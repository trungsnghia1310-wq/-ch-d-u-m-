import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Gắn tg_id & username vào URL để WebApp đọc được
    url = f"{config.WEBAPP_URL}?tg_id={user.id}&username={user.username or ''}"

    kb = [
        [
            KeyboardButton(
                text="🚀 Mở game Đế Chế Dầu Đen",
                web_app=WebAppInfo(url=url),
            )
        ]
    ]

    # ✂️ Chỉ còn 1 dòng này theo yêu cầu
    text = "👋 Chào mừng bạn đến với Đế Chế Dầu Đen!"

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        )
    else:
        await update.effective_chat.send_message(
            text,
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        )


def main():
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()