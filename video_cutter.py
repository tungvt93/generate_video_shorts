import os
import subprocess
import time
import re
from pathlib import Path
from typing import List, Dict, Any
from config import OUTPUT_DIR

def sanitize_filename(filename: str) -> str:
    """Removes invalid characters for filesystem filenames."""
    s = re.sub(r'[^\w\s-]', '', filename).strip()
    return re.sub(r'[-\s]+', '_', s)

def cut_video_clips(video_path: str, clips: List[Dict[str, Any]], speed: float = 1.2) -> List[Dict[str, Any]]:
    """
    Cuts video clips from input video based on start_seconds and end_seconds using ffmpeg.
    Speeds up output video and audio by speed factor (e.g. 1.2x).
    Returns the list of clips with updated 'output_path' keys.
    """
    timestamp = int(time.time())
    session_output_dir = OUTPUT_DIR / f"session_{timestamp}"
    session_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[Video Cutter] Starting cutting process for {len(clips)} clips with speed {speed}x...")
    processed_clips = []

    for clip in clips:
        idx = clip.get("clip_index", 1)
        title = clip.get("title", f"clip_{idx}")
        start_s = clip.get("start_seconds", 0.0)
        end_s = clip.get("end_seconds", 10.0)
        duration = end_s - start_s

        safe_title = sanitize_filename(title)[:30]
        out_filename = f"short_{idx}_{safe_title}.mp4"
        out_filepath = str(session_output_dir / out_filename)

        print(f"[Video Cutter] Cutting clip #{idx} ({start_s}s to {end_s}s -> orig {duration:.1f}s, speed {speed}x) -> {out_filename}")

        # FFmpeg command for precise cutting, speedup & fast encoding
        cmd = [
            'ffmpeg',
            '-y',                      # Overwrite output files
            '-ss', str(start_s),       # Fast seek to start time
            '-to', str(end_s),         # Cut until end time
            '-i', video_path,          # Input video
        ]

        if speed != 1.0:
            cmd.extend([
                '-vf', f'setpts=PTS/{speed}',
                '-af', f'atempo={speed}'
            ])

        cmd.extend([
            '-c:v', 'libx264',         # Standard H.264 video codec
            '-c:a', 'aac',              # Standard AAC audio codec
            '-preset', 'fast',         # Fast encoding
            out_filepath
        ])

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', check=True)
            clip["output_path"] = out_filepath
            clip["final_duration"] = round(duration / speed, 2)
            processed_clips.append(clip)
            print(f"[Video Cutter] Successfully generated ({speed}x): {out_filepath}")
        except subprocess.CalledProcessError as e:
            print(f"[Video Cutter] Error cutting clip #{idx}: {e.stderr}")
            # Fallback without speed filters if error
            fallback_cmd = [
                'ffmpeg', '-y', '-ss', str(start_s), '-to', str(end_s),
                '-i', video_path, '-c', 'copy', out_filepath
            ]
            try:
                subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', check=True)
                clip["output_path"] = out_filepath
                clip["final_duration"] = round(duration, 2)
                processed_clips.append(clip)
                print(f"[Video Cutter] Fallback cut succeeded: {out_filepath}")
            except Exception as ex:
                print(f"[Video Cutter] Fallback failed for clip #{idx}: {ex}")

    return processed_clips
