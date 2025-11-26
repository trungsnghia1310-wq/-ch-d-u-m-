# bot.py
import logging

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)

import config


# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start – gửi nút mở WebApp game đào dầu.
    """
    user = update.effective_user

    # Nếu chưa cấu hình WEBAPP_URL thì báo lỗi nhẹ cho bạn dễ debug
    webapp_url = config.WEBAPP_URL
    if not webapp_url:
        await update.message.reply_text(
            "❌ WEBAPP_URL chưa được cấu hình.\n"
            "Admin hãy kiểm tra lại biến môi trường WEBAPP_URL trên Render."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                text="⛏ Mở game Oil Mining",
                web_app=WebAppInfo(url=webapp_url),
            )
        ]
    ]

    text = (
        f"Chào {user.first_name or 'bạn'} 👋\n"
        "Đây là bot game *Oil Mining Bot*.\n\n"
        "Bấm nút bên dưới để mở game WebApp nhé!"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /help – hướng dẫn nhanh.
    """
    await update.message.reply_text(
        "📖 Hướng dẫn:\n"
        "- Dùng /start để nhận nút mở game WebApp.\n"
        "- Mọi thao tác chơi game, nhiệm vụ, quy đổi... đều nằm trong WebApp."
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /ping – test xem bot có đang sống không.
    """
    await update.message.reply_text("🏓 Pong! Bot đang chạy bình thường.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Bắt và log mọi exception để dễ debug.
    """
    logger.error("❌ Exception while handling an update:", exc_info=context.error)

    # Thông báo nhẹ cho admin / user (không bắt buộc)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Có lỗi xảy ra khi xử lý yêu cầu, admin sẽ kiểm tra lại.",
            )
        except Exception:
            # Tránh lỗi chồng lỗi
            pass


# ====== MAIN ======
def main() -> None:
    """
    Hàm khởi động bot – dùng ApplicationBuilder của PTB v21.
    Không dùng Updater nữa.
    """
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN không tồn tại. "
            "Hãy kiểm tra lại biến môi trường TELEGRAM_BOT_TOKEN trên Render."
        )

    logger.info("Starting bot with token (ẩn)...")

    application = ApplicationBuilder().token(token).build()

    # Đăng ký các command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping))

    # Error handler
    application.add_error_handler(error_handler)

    # Chạy polling (Render sẽ giữ tiến trình này)
    logger.info("Bot is running with long polling...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()