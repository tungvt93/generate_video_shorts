import time
import json
import random
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config import get_gemini_api_key, MIN_CLIP_DURATION, MAX_CLIP_DURATION

class VideoClipHighlight(BaseModel):
    title: str = Field(description="Tiêu đề hấp dẫn ngắn gọn cho đoạn clip")
    start_seconds: float = Field(description="Thời điểm bắt đầu tính bằng giây (ví dụ 75.5)")
    end_seconds: float = Field(description="Thời điểm kết thúc tính bằng giây (phải lớn hơn start_seconds)")
    reason: str = Field(description="Lý do đoạn này hay hoặc có khả năng thu hút người xem")

class HighlightAnalysisResult(BaseModel):
    clips: List[VideoClipHighlight]

def parse_time_to_seconds(time_val: Any) -> float:
    """Helper to parse timestamps into float seconds."""
    if isinstance(time_val, (int, float)):
        return float(time_val)
    if isinstance(time_val, str):
        time_str = time_val.strip()
        parts = time_str.split(':')
        try:
            if len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            else:
                return float(time_str)
        except ValueError:
            return 0.0
    return 0.0

def analyze_video_for_highlights(
    video_path: str,
    num_clips: int = 5,
    api_key: str = None,
    strict_8_10: bool = True,
    min_clip_duration: float = 8.0,
    max_clip_duration: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Uploads video to Gemini Files API and requests interesting highlights.
    If strict_8_10 is True, forces duration between min_clip_duration and max_clip_duration.
    If strict_8_10 is False, lets Gemini determine optimal length based on content.
    Returns list of dicts with title, start_seconds, end_seconds, reason.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Chưa cấu hình GEMINI_API_KEY. Vui lòng kiểm tra lại!")

    client = genai.Client(api_key=key)
    
    print(f"[Gemini Analyzer] Uploading video file: {video_path}...")
    uploaded_file = client.files.upload(file=video_path)
    print(f"[Gemini Analyzer] Upload completed. File URI: {uploaded_file.uri}. Waiting for processing...")

    # Wait for processing
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(4)
        uploaded_file = client.files.get(name=uploaded_file.name)
        print(f"[Gemini Analyzer] Processing status: {uploaded_file.state.name}...")

    if uploaded_file.state.name != "ACTIVE":
        raise RuntimeError(f"Video processing failed with status: {uploaded_file.state.name}")

    print(f"[Gemini Analyzer] Video is ACTIVE. Sending prompt to Gemini (Strict custom duration: {strict_8_10}, Min: {min_clip_duration}s, Max: {max_clip_duration}s)...")

    if strict_8_10:
        duration_instruction = f"2. Độ dài của mỗi clip (tính bằng end_seconds - start_seconds) PHẢI nằm trong khoảng từ {min_clip_duration} giây đến {max_clip_duration} giây (ví dụ: ngẫu nhiên trong khoảng {min_clip_duration}s - {max_clip_duration}s)."
    else:
        duration_instruction = f"2. Tự do quyết định độ dài tối ưu cho từng clip dựa trên nội dung thực tế của video để trích xuất đủ {num_clips} đoạn hay nhất."

    prompt = f"""
Hãy phân tích kỹ lưỡng video này và chọn ra đúng {num_clips} đoạn highlight (khoảnh khắc hay, hấp dẫn, tạo kịch tính hoặc có khả năng lên xu hướng viral nhất).

Yêu cầu BẮT BUỘC:
1. KHÔNG ĐƯỢC TRÙNG LẶP NỘI DUNG VÀ THỜI GIAN: Các mốc thời gian [start_seconds, end_seconds] giữa tất cả các clip phải hoàn toàn tách biệt, tuyệt đối không được chồng lấn/giao nhau.
{duration_instruction}
3. Trả về kết quả dưới dạng định dạng JSON chuẩn.
"""

    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash']
    response = None
    last_error = None

    for model_name in models_to_try:
        for attempt in range(1, 4):  # Try up to 3 times per model
            try:
                print(f"[Gemini Analyzer] Sending request to {model_name} (Attempt {attempt})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=HighlightAnalysisResult,
                        temperature=0.4,
                    ),
                )
                if response:
                    break
            except Exception as e:
                last_error = e
                err_msg = str(e)
                print(f"[Gemini Analyzer] Warning on {model_name} attempt {attempt}: {err_msg}")
                if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg:
                    print("[Gemini Analyzer] Server experiencing high demand. Waiting 5 seconds before retrying...")
                    time.sleep(5)
                else:
                    break # non-transient error, break attempt loop
        if response:
            break

    if not response:
        # Final cleanup before raising error
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass
        raise RuntimeError(f"Không thể kết nối Gemini AI do máy chủ đang quá tải (Lỗi 503). Vui lòng thử lại sau 1-2 phút! Lỗi chi tiết: {last_error}")

    print("[Gemini Analyzer] Received response successfully from Gemini.")
    
    # Cleanup file from Gemini servers after analysis
    try:
        client.files.delete(name=uploaded_file.name)
        print("[Gemini Analyzer] Cleaned up temporary file from Gemini storage.")
    except Exception as e:
        print(f"[Gemini Analyzer] Warning: Could not delete temp file: {e}")

    try:
        result_data = json.loads(response.text)
        clips_raw = result_data.get("clips", [])
    except Exception as e:
        print(f"[Gemini Analyzer] Error parsing JSON response: {e}. Raw text: {response.text}")
        clips_raw = []

    final_clips = []
    occupied_ranges = []  # List of tuples (start, end) to guarantee zero overlap

    for clip in clips_raw:
        title = clip.get("title", f"Highlight #{len(final_clips)+1}")
        start_s = parse_time_to_seconds(clip.get("start_seconds", 0))
        end_s = parse_time_to_seconds(clip.get("end_seconds", 0))
        reason = clip.get("reason", "")

        duration = end_s - start_s
        
        # Adjust if strict mode enabled
        if strict_8_10:
            if duration < min_clip_duration or duration > max_clip_duration:
                target_duration = random.uniform(min_clip_duration, max_clip_duration)
                end_s = start_s + target_duration
                print(f"[Gemini Analyzer] Adjusted duration from {duration:.2f}s to {target_duration:.2f}s (range {min_clip_duration}s-{max_clip_duration}s).")
        else:
            if duration <= 1.0:
                end_s = start_s + 10.0  # fallback safety
                print(f"[Gemini Analyzer] Fallback clip duration to 10s.")

        # Check overlap with existing chosen clips
        is_overlapping = False
        for occ_start, occ_end in occupied_ranges:
            # Overlap check condition
            if not (end_s <= occ_start or start_s >= occ_end):
                is_overlapping = True
                print(f"[Gemini Analyzer] Filtered out overlapping clip '{title}' [{start_s:.1f}s-{end_s:.1f}s] with existing range [{occ_start:.1f}s-{occ_end:.1f}s].")
                break

        if not is_overlapping:
            occupied_ranges.append((start_s, end_s))
            final_clips.append({
                "clip_index": len(final_clips) + 1,
                "title": title,
                "start_seconds": round(start_s, 2),
                "end_seconds": round(end_s, 2),
                "duration": round(end_s - start_s, 2),
                "reason": reason
            })

    return final_clips
