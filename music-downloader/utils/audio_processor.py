import asyncio
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2

class AudioProcessor:
    @staticmethod
    async def compress_to_192(input_path: str) -> str:
        """Понижение битрейта файла до 192 kbps с сохранением метаданных."""
        output_path = input_path.replace(".mp3", "_192kbps.mp3")
        
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-y', '-i', input_path, 
            '-b:a', '192k', '-map_metadata', '0', 
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError("FFmpeg: Сбой ре-энкодинга.")
        return output_path

    @staticmethod
    async def split_audio(input_path: str, max_size_bytes: int = 49 * 1024 * 1024) -> list[str]:
        """Фрагментация аудио на валидные чанки без потери качества."""
        try:
            original_tags = ID3(input_path)
            title = str(original_tags.get('TIT2', 'Track'))
        except Exception:
            title = "Track"

        audio = MP3(input_path)
        total_duration = audio.info.length
        total_size = os.path.getsize(input_path)
        
        num_chunks = int(total_size // max_size_bytes) + 1
        chunk_duration = total_duration / num_chunks
        
        output_chunks = []
        base_name = os.path.splitext(input_path)[0]

        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = f"{base_name}_part_{i+1}.mp3"
            
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y', '-ss', str(start_time), '-t', str(chunk_duration),
                '-i', input_path, '-acodec', 'copy', '-map_metadata', '0',
                chunk_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(chunk_path):
                try:
                    tags = ID3(chunk_path)
                    tags.add(TIT2(encoding=3, text=f"{title} [Part {i+1}/{num_chunks}]"))
                    tags.save()
                except Exception:
                    pass
                output_chunks.append(chunk_path)
                
        return output_chunks
