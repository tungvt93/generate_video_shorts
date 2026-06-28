# 🎬 Gemini Auto Video Shorts Generator

Công cụ tự động cắt video dài (từ tệp trong máy hoặc link Douyin/YouTube/TikTok) thành các video ngắn chất lượng cao có độ dài **8 - 10 giây** dựa trên sự phân tích nội dung thông minh từ **Gemini AI**.

## 🌟 Tính Năng Nổi Bật
- **Hỗ trợ đa dạng đầu vào**: Tải tệp video từ máy tính (MP4, MKV...) hoặc dán đường dẫn Douyin/YouTube/TikTok.
- **Phân tích thông minh với Gemini AI**: Tự động phát hiện các phân cảnh kịch tính, cuốn hút hoặc có tiềm năng viral cao.
- **Đảm bảo chuẩn độ dài**: Mọi video cắt ra đều tuân thủ nghiêm ngặt độ dài từ **8 đến 10 giây** (ngẫu nhiên 8.2s, 9.0s, 9.5s...).
- **Giao diện Web trực quan (Gradio UI)**: Xem trực tiếp tiến trình, phát thử video ngắn và tải về máy dễ dàng.

## 🚀 Hướng Dẫn Sử Dụng

### 1. Cài Đặt Thư viện
```bash
pip install -r requirements.txt
```
*Lưu ý: Đảm bảo máy tính của bạn đã cài đặt `ffmpeg`.*

### 2. Cấu Hình Gemini API Key
Tạo tệp `.env` tại thư mục gốc (hoặc nhập trực tiếp trên giao diện Web):
```env
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 3. Khởi Chạy Ứng Dụng Web UI
```bash
python app.py
```
Sau đó truy cập đường dẫn `http://127.0.0.1:7860` trên trình duyệt web của bạn.

## 📁 Cấu Trúc Dự Án
- `app.py`: Giao diện Web Gradio chính.
- `gemini_analyzer.py`: Module giao tiếp với Gemini Files API và phân tích mốc thời gian.
- `video_cutter.py`: Module cắt video tự động bằng FFmpeg.
- `downloader.py`: Module tự động tải video từ link Douyin/YouTube qua `yt-dlp`.
- `config.py`: Tệp cấu hình thư mục và thông số hệ thống.
