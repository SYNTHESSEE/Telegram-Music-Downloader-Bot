import sys
import asyncio
import logging
import os
import re
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.utils.token import TokenValidationError
from aiogram.client.session.aiohttp import AiohttpSession

from utils.link_parser import LinkParser
from utils.animator import StatusAnimator
from extractors.youtube import YouTubeExtractor
from extractors.pinterest import PinterestExtractor
from extractors.yandex import YandexMetaExtractor

# 1. Загрузка переменных окружения в первую очередь
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

if not os.path.isabs(DOWNLOAD_DIR):
    DOWNLOAD_DIR = os.path.join(BASE_DIR, DOWNLOAD_DIR)

# 2. Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 3. Инициализация роутеров и экстракторов
router = Router()
yt_extractor = YouTubeExtractor(download_dir=DOWNLOAD_DIR)
pin_extractor = PinterestExtractor(download_dir=DOWNLOAD_DIR)
ya_extractor = YandexMetaExtractor()


@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        f"👋 Привет, **{message.from_user.first_name}**!\n\n"
        "Я бот для скачивания медиаконтента в высоком качестве.\n\n"
        "**Поддерживаемые сервисы:**\n"
        "• 🎵 **YouTube / YouTube Music** — прямое скачивание (MP3)\n"
        "• 🔴 **Яндекс Музыка** — автопоиск оригинала и скачивание (MP3)\n"
        "• 📌 **Pinterest / pin.it** — скачивание видеороликов (MP4)\n\n"
        "**Как использовать:**\n"
        "Просто отправь ссылку на трек или видео."
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(F.text)
async def handle_message(message: Message):
    parsed = LinkParser.parse_text(message.text)
    link_type = parsed["type"]
    url = parsed["url"]

    if not link_type:
        return

    logger.info(f"Запрос от [{message.from_user.id}] | Тип: [{link_type}] | URL: {url}")
    loop = asyncio.get_running_loop()

    async with StatusAnimator(message, "Инициализация загрузки") as status:
        def on_progress(percent: float):
            loop.call_soon_threadsafe(status.set_progress, percent)

        try:
            if link_type == "pinterest":
                status.update(new_text="Загрузка видео с Pinterest")
                data = await pin_extractor.download_video(url, progress_callback=on_progress)
                
                video_file = FSInputFile(data["filepath"])
                await message.answer_video(
                    video=video_file,
                    caption=f"📌 **{data['title']}**",
                    parse_mode="Markdown"
                )

            elif link_type == "youtube":
                status.update(new_text="Извлечение аудио из YouTube")
                data = await yt_extractor.download_track(url, progress_callback=on_progress)
                
                clean_title = re.sub(r'[\\/*?:"<>|]', "", data["title"])
                display_filename = f"{clean_title}.mp3"
                
                audio_file = FSInputFile(data["filepath"], filename=display_filename)
                
                await message.answer_audio(
                    audio=audio_file,
                    title=data["title"],
                    performer=data.get("artist"),
                    caption=f"🎵 **{data['title']}**",
                    parse_mode="Markdown"
                )

            elif link_type == "yandex":
                status.update(new_text="Чтение тегов Яндекс Музыки")
                meta = await ya_extractor.get_track_info(url)
                
                search_query = f"ytsearch1:{meta['artist']} - {meta['title']}"
                status.update(new_text=f"Поиск в YouTube: {meta['artist']} - {meta['title']}")
                
                data = await yt_extractor.download_track(search_query, progress_callback=on_progress)
                
                safe_artist = re.sub(r'[\\/*?:"<>|]', "", meta["artist"])
                safe_title = re.sub(r'[\\/*?:"<>|]', "", meta["title"])
                display_filename = f"{safe_artist} - {safe_title}.mp3"
                
                audio_file = FSInputFile(data["filepath"], filename=display_filename)
                
                await message.answer_audio(
                    audio=audio_file,
                    title=meta["title"],
                    performer=meta["artist"],
                    caption=f"🎵 **{meta['artist']} — {meta['title']}**\n*(найдено через YouTube)*",
                    parse_mode="Markdown"
                )

            if 'data' in locals() and os.path.exists(data["filepath"]):
                os.remove(data["filepath"])

        except Exception as e:
            logger.error(f"Сбой при обработке ссылки: {e}", exc_info=True)
            await message.answer(f"❌ **Ошибка при обработке:**\n`{str(e)}`", parse_mode="Markdown")


async def main():
    logger.info("Инициализация ядра бота...")
    
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
        logger.critical(f"TELEGRAM_BOT_TOKEN не загружен! Проверь наличие файла: {env_path}")
        return

    # Подключение SOCKS5 прокси из Happ
    PROXY_URL = "socks5://127.0.0.1:10808"
    session = AiohttpSession(proxy=PROXY_URL)

    try:
        bot = Bot(token=BOT_TOKEN.strip(), session=session)
    except TokenValidationError:
        logger.critical(f"Некорректный формат TELEGRAM_BOT_TOKEN в файле: {env_path}")
        return

    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Сброс точек подключения (Webhook drop)...")
    try:
        await asyncio.wait_for(bot.delete_webhook(drop_pending_updates=True), timeout=5.0)
    except Exception as e:
        logger.warning(f"Пропуск сброса вебхука: {e}")

    logger.info(">>> Бот активен и готов к приему команд <<<")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Сессия завершена.")
