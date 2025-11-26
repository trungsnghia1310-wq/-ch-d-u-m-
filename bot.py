# bot.py
import logging
from typing import Final

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import config

# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN: Final[str] = config.TELEGRAM_BOT_TOKEN
WEBAPP_URL: Final[str] = config.WEBAPP_URL


# ====== HANDLERS ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /start: gửi nút mở webapp."""
    if not WEBAPP_URL:
        await update.message.reply_text("WEBAPP_URL chưa được cấu hình.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                text="⛏ Mở game đào dầu",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Xin chào! Ấn nút bên dưới để mở game đào dầu 👇",
        reply_markup=reply_markup,
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /ping: test bot còn sống không."""
    await update.message.reply_text("✅ Bot vẫn đang chạy!")


# ====== MAIN ======

def main() -> None:
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN chưa được set trong Environment.")
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN")

    logger.info("Starting bot with token (ẩn)...")

    application = ApplicationBuilder().token(TOKEN).build()

    # Đăng ký các command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))

    # Chạy polling (API mới, KHÔNG dùng Updater nữa)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()