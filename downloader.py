import os
import time
from pathlib import Path
import yt_dlp
from config import DOWNLOAD_DIR

def download_video_from_url(url: str) -> str:
    """
    Downloads a video from a given URL (Douyin, YouTube, TikTok, etc.) using yt-dlp.
    Returns the absolute path to the downloaded MP4 file.
    """
    timestamp = int(time.time())
    output_template = str(DOWNLOAD_DIR / f"downloaded_{timestamp}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }
    
    print(f"[Downloader] Starting download for URL: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # In case the extension changed during merge (e.g., .mp4)
        base, _ = os.path.splitext(filename)
        expected_mp4 = base + ".mp4"
        if os.path.exists(expected_mp4):
            filename = expected_mp4
            
    print(f"[Downloader] Download completed: {filename}")
    return filename

if __name__ == "__main__":
    # Test function if run directly
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    try:
        path = download_video_from_url(test_url)
        print("Test download success:", path)
    except Exception as e:
        print("Test download failed:", e)
