# bot.py
import logging
import hmac
import hashlib
import urllib.parse
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
CREDIT_SECRET: Final[str] = config.CREDIT_SECRET  # chuỗi bí mật dùng để ký


def build_signed_webapp_url(tg_id: str, username: str | None) -> str:
    """
    Tạo URL kèm query + chữ ký HMAC để webapp tin được đây là user thật.
    """
    if username is None:
        username = ""

    # payload đơn giản: "tg_id:username"
    payload = f"{tg_id}:{username}"

    sig = hmac.new(
        CREDIT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    query = {
        "tg_id": tg_id,
        "username": username,
        "sig": sig,
    }
    return WEBAPP_URL.rstrip("/") + "?" + urllib.parse.urlencode(query)


# ====== HANDLERS ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /start: gửi nút mở webapp có ký user."""
    if not WEBAPP_URL:
        await update.message.reply_text("WEBAPP_URL chưa được cấu hình.")
        return

    user = update.effective_user
    tg_id = str(user.id)
    username = user.username

    full_url = build_signed_webapp_url(tg_id, username)

    keyboard = [
        [
            InlineKeyboardButton(
                text="⛏ Mở game đào dầu",
                web_app=WebAppInfo(url=https://chdum.fly.dev),
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