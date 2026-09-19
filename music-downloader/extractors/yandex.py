import re
import json
import html
import asyncio
import urllib.request
import urllib.error

class YandexMetaExtractor:
    """
    Легковесный экстрактор метаданных Яндекс Музыки без использования yt-dlp.
    Использует двухуровневое извлечение:
    1. Открытый REST API (api.music.yandex.net) по ID трека.
    2. Прямой парсинг HTML-метрик (JSON-LD, OpenGraph, <title>) в случае отсутствия API.
    """
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

    async def get_track_info(self, url: str) -> dict:
        """Извлекает Artist и Title из ссылки Яндекс Музыки"""
        return await asyncio.to_thread(self._extract, url)

    def _extract(self, url: str) -> dict:
        track_id_match = re.search(r'track/(\d+)', url)
        track_id = track_id_match.group(1) if track_id_match else None

        # --- Метод 1: Запрос к публичному API Яндекс Музыки ---
        if track_id:
            try:
                api_url = f"https://api.music.yandex.net/tracks/{track_id}"
                req = urllib.request.Request(api_url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('result') and len(data['result']) > 0:
                        track = data['result'][0]
                        title = track.get('title', '').strip()
                        if track.get('version'):
                            title += f" ({track['version'].strip()})"
                        
                        artists = [a.get('name').strip() for a in track.get('artists', []) if a.get('name')]
                        artist = ", ".join(artists) if artists else "Unknown Artist"
                        
                        if title:
                            return {
                                "title": title,
                                "artist": artist
                            }
            except Exception:
                pass  # При ограничении доступа к API переходим к парсингу HTML

        # --- Метод 2: Парсинг HTML-страницы ---
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')

            # 2.1 JSON-LD Schema
            json_ld_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html_content, re.DOTALL)
            for j_str in json_ld_matches:
                try:
                    ld_data = json.loads(j_str)
                    if isinstance(ld_data, dict) and ld_data.get('@type') == 'MusicRecording':
                        title = ld_data.get('name')
                        by_artist = ld_data.get('byArtist')
                        artist = None
                        if isinstance(by_artist, dict):
                            artist = by_artist.get('name')
                        elif isinstance(by_artist, list):
                            artists = [a.get('name') for a in by_artist if isinstance(a, dict) and a.get('name')]
                            artist = ", ".join(artists)
                        if title:
                            return {
                                "title": html.unescape(title).strip(),
                                "artist": html.unescape(artist or "Unknown Artist").strip()
                            }
                except Exception:
                    pass

            # 2.2 Open Graph Tags
            og_title_m = re.search(r'<meta\s+(?:property|name)=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE) or \
                         re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+(?:property|name)=["\']og:title["\']', html_content, re.IGNORECASE)
            
            og_desc_m = re.search(r'<meta\s+(?:property|name)=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE) or \
                        re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+(?:property|name)=["\']og:description["\']', html_content, re.IGNORECASE)

            # 2.3 Тег <title>
            title_tag_m = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)

            raw_title = og_title_m.group(1) if og_title_m else (title_tag_m.group(1) if title_tag_m else "")
            raw_title = html.unescape(raw_title).strip()

            # Очистка суффиксов страницы
            clean_title = re.sub(r'[\s\.\-–—]*Слушать\s+онлайн.*$', '', raw_title, flags=re.IGNORECASE).strip()
            clean_title = re.sub(r'[\s\.\-–—]*слушать\s+трек.*$', '', clean_title, flags=re.IGNORECASE).strip()

            artist_from_desc = ""
            if og_desc_m:
                desc = html.unescape(og_desc_m.group(1))
                art_match = re.search(r'(?:Исполнитель|Artist):\s*([^.]+)', desc, re.IGNORECASE)
                if art_match:
                    artist_from_desc = art_match.group(1).strip()

            m1 = re.match(r'^«(.*?)»\s*[—\-–]\s*(.*)$', clean_title)
            if m1:
                return {"title": m1.group(1).strip(), "artist": m1.group(2).strip()}

            m2 = re.match(r'^(.*?)\s*[—\-–]\s*«(.*?)»$', clean_title)
            if m2:
                return {"title": m2.group(2).strip(), "artist": m2.group(1).strip()}

            if artist_from_desc and clean_title:
                return {"title": clean_title, "artist": artist_from_desc}

            if " — " in clean_title or " – " in clean_title or " - " in clean_title:
                parts = re.split(r'\s+[—\-–]\s+', clean_title, maxsplit=1)
                if len(parts) == 2:
                    return {"title": parts[1].strip(), "artist": parts[0].strip()}

            if clean_title:
                return {"title": clean_title, "artist": artist_from_desc or "Unknown Artist"}

        except Exception as e:
            raise RuntimeError(f"Сбой считывания метаданных страницы: {e}")

        raise ValueError("Не удалось распарсить метаданные с Яндекс Музыки")
