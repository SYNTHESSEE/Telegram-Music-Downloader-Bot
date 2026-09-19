import asyncio
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

class StatusAnimator:
    """
    Контекстный менеджер с анимацией спиннера и прогресс-баром.
    """
    def __init__(self, message: Message, initial_text: str = "Обработка", bar_length: int = 12):
        self.message = message
        self.text = initial_text
        self.percent = None  # None — полоса скрыта до начала реальной выкачки
        self.bar_length = bar_length
        self.status_msg = None
        self._task = None
        self._running = False
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    async def __aenter__(self):
        content = self._render_content(self.frames[0])
        self.status_msg = await self.message.answer(content, parse_mode="Markdown")
        self._running = True
        self._task = asyncio.create_task(self._animate())
        return self

    def update(self, new_text: str = None, percent: float = None):
        """Обновление текста статуса или процентов"""
        if new_text is not None:
            self.text = new_text
        if percent is not None:
            self.percent = percent

    def set_progress(self, percent: float):
        """Потокобезопасный вызов для yt-dlp"""
        self.percent = percent

    def _render_content(self, frame: str) -> str:
        text_line = f"{frame} **{self.text}**"
        
        if self.percent is None:
            return text_line

        # Вычисление количества закрашенных и полых кубиков
        pct = min(max(self.percent, 0.0), 100.0)
        filled = int(round((pct / 100.0) * self.bar_length))
        filled = min(filled, self.bar_length)
        hollow = self.bar_length - filled

        # Сплошная линия из кубиков в моноширинном блоке + проценты справа
        bar = "■" * filled + "□" * hollow
        progress_line = f"`{bar}` **{pct:.0f}%**"

        return f"{text_line}\n{progress_line}"

    async def _animate(self):
        idx = 1
        while self._running:
            await asyncio.sleep(1.2)  # Безопасный интервал обновления
            if not self._running:
                break
            
            frame = self.frames[idx % len(self.frames)]
            idx += 1
            content = self._render_content(frame)
            
            try:
                await self.status_msg.edit_text(content, parse_mode="Markdown")
            except TelegramBadRequest:
                pass  # Игнорируем, если контент не изменился
            except Exception:
                break

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.status_msg:
            try:
                await self.status_msg.delete()
            except Exception:
                pass
