import os
import asyncio
from yt_dlp import YoutubeDL

class PinterestExtractor:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_ffmpeg_path = os.path.join(project_root, "ffmpeg", "bin")

        self.ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, 'pin_%(id)s.%(ext)s'),
            'noplaylist': True,
            'nocheckcertificate': True,
            
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 5,
            
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },

            'ffmpeg_location': local_ffmpeg_path,
            'quiet': True,
        }

    async def download_video(self, url: str, progress_callback=None) -> dict:
        return await asyncio.to_thread(self._execute_download, url, progress_callback)

    def _execute_download(self, url: str, progress_callback=None) -> dict:
        opts = self.ydl_opts.copy()

        if progress_callback:
            def hook(d):
                if d.get('status') == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    if total and total > 0:
                        pct = (downloaded / total) * 100
                        progress_callback(pct)

            opts['progress_hooks'] = [hook]

        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

            if not os.path.exists(filepath):
                base_path = os.path.splitext(filepath)[0]
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base_path + ext):
                        filepath = base_path + ext
                        break

            return {
                "filepath": filepath,
                "title": info.get("title", "Pinterest Video"),
                "duration": info.get("duration", 0),
                "filesize": os.path.getsize(filepath) if os.path.exists(filepath) else 0
            }
