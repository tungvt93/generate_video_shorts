import os
import sys
import io

# Fix Unicode stdout/stderr issue on Windows
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import gradio as gr
from config import get_gemini_api_key
from downloader import download_video_from_url
from gemini_analyzer import analyze_video_for_highlights
from video_cutter import cut_video_clips

def process_video_pipeline(
    input_file,
    video_url,
    num_clips,
    api_key_input,
    dynamic_length,
    speed_factor,
    min_dur,
    max_dur,
    progress=gr.Progress(track_tqdm=True)
):
    """
    Main processing pipeline for Gradio interface.
    """
    api_key = api_key_input.strip() if api_key_input else get_gemini_api_key()
    if not api_key:
        raise gr.Error("⚠️ Vui lòng nhập GEMINI_API_KEY hoặc cấu hình trong tệp .env!")

    video_path = None
    
    # Step 1: Determine video source
    progress(0.1, desc="Đang kiểm tra đầu vào video...")
    if input_file is not None:
        video_path = input_file
        print(f"[App Pipeline] Using local file input: {video_path}")
    elif video_url and video_url.strip():
        url = video_url.strip()
        progress(0.2, desc="Đang tải video từ đường link (Douyin/YouTube/TikTok)...")
        try:
            video_path = download_video_from_url(url)
        except Exception as e:
            raise gr.Error(f"❌ Lỗi khi tải video từ link: {str(e)}")
    else:
        raise gr.Error("⚠️ Vui lòng tải lên tệp video từ máy HOẶC dán đường dẫn video!")

    if not video_path or not os.path.exists(video_path):
        raise gr.Error("❌ Không tìm thấy tệp video để xử lý.")

    # Validate min/max duration
    use_custom_duration = True
    if dynamic_length or min_dur is None or max_dur is None:
        use_custom_duration = False
        min_d, max_d = 8.0, 10.0
    else:
        try:
            min_d = float(min_dur)
            max_d = float(max_dur)
            if min_d <= 0 or max_d <= 0:
                use_custom_duration = False
                min_d, max_d = 8.0, 10.0
            elif min_d > max_d:
                min_d, max_d = max_d, min_d  # Auto swap if inverted
        except ValueError:
            use_custom_duration = False
            min_d, max_d = 8.0, 10.0

    # Step 2: Analyze with Gemini AI
    desc_str = f"({min_d}s-{max_d}s)" if use_custom_duration else "(Tự do/AI tự tính)"
    progress(0.4, desc=f"Đang gửi video lên Gemini AI để phân tích {desc_str}...")
    try:
        highlights = analyze_video_for_highlights(
            video_path=video_path,
            num_clips=int(num_clips),
            api_key=api_key,
            strict_8_10=use_custom_duration,
            min_clip_duration=min_d,
            max_clip_duration=max_d
        )
    except Exception as e:
        raise gr.Error(f"❌ Lỗi phân tích Gemini AI: {str(e)}")

    if not highlights:
        raise gr.Error("❌ Gemini AI không tìm thấy đoạn highlight phù hợp.")

    # Step 3: Cut Video Clips with Speedup
    progress(0.8, desc=f"Đang tiến hành cắt video ngắn bằng FFmpeg (tốc độ {speed_factor}x)...")
    try:
        processed_clips = cut_video_clips(video_path=video_path, clips=highlights, speed=float(speed_factor))
    except Exception as e:
        raise gr.Error(f"❌ Lỗi khi cắt video: {str(e)}")

    progress(1.0, desc="Hoàn thành!")

    # Format output for display
    output_files = [c["output_path"] for c in processed_clips if "output_path" in c]
    
    summary_text = f"🎉 **Đã tạo thành công {len(output_files)} video ngắn (Tốc độ {speed_factor}x)!**\n\n"
    for c in processed_clips:
        summary_text += f"- **Clip #{c['clip_index']}**: `{c['title']}` (Thời lượng xuất: {c.get('final_duration', c['duration'])}s)\n  *Thời gian gốc: {c['start_seconds']}s -> {c['end_seconds']}s*\n  *Lý do chọn: {c['reason']}*\n\n"

    # Preview the first video clip
    first_clip_preview = output_files[0] if output_files else None

    return summary_text, output_files, first_clip_preview


# Build Gradio UI
theme = gr.themes.Soft(
    primary_hue="red",
    secondary_hue="slate",
)

with gr.Blocks(theme=theme, title="Gemini Auto Shorts Generator") as demo:
    gr.Markdown(
        """
        # 🎬 Gemini Auto Video Shorts Generator
        ### Công cụ tự động tạo video ngắn (TikTok / Reels / Shorts) từ video dài bằng Gemini AI
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📥 1. Chọn Đầu Vào Video")
            file_input = gr.File(
                label="📁 Tải tệp video từ máy tính của bạn (Khuyên dùng)",
                file_types=["video"],
                type="filepath"
            )
            url_input = gr.Textbox(
                label="🔗 Hoặc dán đường dẫn Video (Douyin / YouTube / TikTok)",
                placeholder="https://v.douyin.com/... hoặc https://youtube.com/..."
            )
            
            gr.Markdown("### ⚙️ 2. Cấu Hình Tùy Chọn")
            num_clips_slider = gr.Slider(
                minimum=1,
                maximum=100,
                value=5,
                step=1,
                label="🎯 Số lượng video ngắn muốn tạo"
            )
            
            with gr.Row():
                min_dur_input = gr.Number(label="⏱️ Độ dài Tối thiểu (Giây) - Để trống nếu muốn AI tự tính", value=None, precision=0)
                max_dur_input = gr.Number(label="⏱️ Độ dài Tối đa (Giây) - Để trống nếu muốn AI tự tính", value=None, precision=0)

            speed_slider = gr.Slider(
                minimum=0.8,
                maximum=2.0,
                value=1.2,
                step=0.1,
                label="⚡ Tốc độ video đầu ra (Mặc định 1.2x)"
            )
            dynamic_length_check = gr.Checkbox(
                label="🔓 Ép AI tự quyết định độ dài clip phù hợp theo nội dung",
                value=False
            )
            api_key_box = gr.Textbox(
                label="🔑 Gemini API Key",
                placeholder="Nhập GEMINI_API_KEY (để trống nếu đã cài trong file .env)",
                type="password",
                value=get_gemini_api_key()
            )
            
            submit_btn = gr.Button("⚡ Bắt Đầu Tạo Video Ngắn", variant="primary", size="lg")

        with gr.Column(scale=1):
            gr.Markdown("### 📊 3. Kết Quả")
            status_output = gr.Markdown(value="Sẵn sàng xử lý...")
            preview_video = gr.Video(label="📺 Xem thử Clip đầu tiên")
            file_gallery = gr.Files(label="📦 Tải về các Video ngắn đã tạo")

    submit_btn.click(
        fn=process_video_pipeline,
        inputs=[
            file_input, url_input, num_clips_slider, api_key_box,
            dynamic_length_check, speed_slider, min_dur_input, max_dur_input
        ],
        outputs=[status_output, file_gallery, preview_video]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
