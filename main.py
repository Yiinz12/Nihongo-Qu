import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from handler.command import get_start_handler, get_cancel_handler, get_start_group_handler  # Import fungsi untuk menangani command
from handler.callback import button  # Import fungsi untuk menangani callback
from models.game_bot import check_answer  # Mengimpor fungsi start_quiz dari game.py
from models.game_group import check_answer_group  # Mengimpor fungsi start_quiz dari game.py
from config.constants import BOT_TOKEN

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fungsi utama untuk menjalankan bot
def main():
    # Token API dari BotFather
    application = Application.builder().token(BOT_TOKEN).build()

    # Menambahkan handler untuk /start
    application.add_handler(get_start_handler())
    application.add_handler(get_start_group_handler())
    application.add_handler(get_cancel_handler())


    # Menambahkan handler untuk menangani callback tombol
    application.add_handler(CallbackQueryHandler(button))  # Menambahkan handler callback

    # Handler untuk grup
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.SUPERGROUP, check_answer_group))
    # Handler untuk pesan pribadi
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, check_answer))
    

    # Mulai bot dan logging
    logger.info("Bot is starting...")
    application.run_polling()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    import asyncio
    # Langsung jalankan polling tanpa mengelola event loop secara manual
    asyncio.run(main())
