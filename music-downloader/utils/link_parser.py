import re

class LinkParser:
    YOUTUBE_REGEX = re.compile(
        r'https?://(?:www\.|music\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|v/|embed/)|youtu\.be/)[a-zA-Z0-9_-]+[^\s]*',
        re.IGNORECASE
    )
    
    PINTEREST_REGEX = re.compile(
        r'https?://(?:[a-zA-Z0-9-]+\.)?(?:pinterest\.[a-z.]+|pin\.it)/[^\s]*',
        re.IGNORECASE
    )

    YANDEX_REGEX = re.compile(
        r'https?://music\.yandex\.[a-zA-Z.]+/(?:album/\d+/track/|track/)\d+[^\s]*',
        re.IGNORECASE
    )

    @classmethod
    def parse_text(cls, text: str) -> dict:
        if not text:
            return {"type": None, "url": None}

        yt_match = cls.YOUTUBE_REGEX.search(text)
        if yt_match:
            return {"type": "youtube", "url": yt_match.group(0)}

        pin_match = cls.PINTEREST_REGEX.search(text)
        if pin_match:
            return {"type": "pinterest", "url": pin_match.group(0)}

        ya_match = cls.YANDEX_REGEX.search(text)
        if ya_match:
            return {"type": "yandex", "url": ya_match.group(0)}

        return {"type": None, "url": None}
