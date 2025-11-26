import logging
from config import TELEGRAM_BOT_TOKEN
from telegram.ext import ApplicationBuilder
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

    # Đăng ký handler các lệnh
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_web_app_data, pattern="^webapp_data$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Chạy bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()