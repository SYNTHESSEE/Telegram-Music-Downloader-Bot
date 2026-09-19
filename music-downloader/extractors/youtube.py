import os
import asyncio
import yt_dlp

try:
    import static_ffmpeg
    ffmpeg_path, _ = static_ffmpeg.add_paths()
except ImportError:
    ffmpeg_path = None


class YouTubeExtractor:
    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
        self.ydl_opts = {
            'format': 'ba/ba*',
            'outtmpl': os.path.join(self.download_dir, 'yt_%(id)s.%(ext)s'),
            'noplaylist': True,
            'nocheckcertificate': True,
            
            # Сетевой прокси-канал
            'proxy': 'socks5://127.0.0.1:10808',
            'socket_timeout': 30,
            'retries': 10,
            
            # Заголовки имитации
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            
            # Удаленная расшифровка JS-челленджей
            'remote_components': ['ejs:github'],
            
            # Стабильный стек клиентов без вызова варнингов о PO-Token/Cookies
            'extractor_args': {
                'youtube': {
                    'player_client': ['web_creator', 'android_vr', 'web_embedded'],
                    'player_skip': ['webpage'],
                }
            },
            
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,  # Подавление некритичных системных предупреждений
        }

        if ffmpeg_path:
            self.ydl_opts['ffmpeg_location'] = ffmpeg_path

    async def download_track(self, target: str, progress_callback=None):
        return await asyncio.to_thread(self._execute_download, target, progress_callback)

    def _execute_download(self, target: str, progress_callback=None):
        opts = self.ydl_opts.copy()
        if progress_callback:
            def hook(d):
                if d.get('status') == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        progress_callback(percent)
            opts['progress_hooks'] = [hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            final_filepath = f"{base}.mp3"
            
            return {
                "filepath": final_filepath,
                "title": info.get("title", "Unknown Title"),
                "artist": info.get("uploader", "Unknown Artist")
            }
