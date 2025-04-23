import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, ContextTypes
from handler.command import get_start_handler, get_cancel_handler, get_start_group_handler  # Import fungsi untuk menangani command
from handler.callback import button  # Import fungsi untuk menangani callback
from handler.command import get_profile_handler, get_leaderboard_handler
from models.game_bot import check_answer  # Mengimpor fungsi start_quiz dari game.py
from models.game_group import check_answer_group  # Mengimpor fungsi start_quiz dari game.py
from models.quiz_kanji import check_kanji_answer  # Import fungsi untuk memeriksa jawaban kanji
from models.quiz_kotoba import check_kotoba_answer  # Import fungsi untuk memeriksa jawaban kotoba
from config.constants import BOT_TOKEN, user_quiz_data  # Import user_quiz_data untuk track state

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler tunggal untuk semua jawaban
async def handle_any_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Log untuk debugging
    logger.info(f"Menerima teks dari chat_id: {chat_id}")
    
    # Tentukan jenis quiz yang sedang berjalan
    if chat_id in user_quiz_data:
        quiz_type = user_quiz_data[chat_id].get("quiz_type", "")
        logger.info(f"Quiz type yang terdeteksi: {quiz_type}")
        
        if "kotoba" in quiz_type and "meaning" in quiz_type:
            # Jawaban untuk quiz kotoba
            logger.info(f"Mendelegasikan ke check_kotoba_answer untuk chat_id: {chat_id}")
            return await check_kotoba_answer(update, context)
        elif "kanji" in quiz_type:
            # Jawaban untuk quiz kanji
            logger.info(f"Mendelegasikan ke check_kanji_answer untuk chat_id: {chat_id}")
            return await check_kanji_answer(update, context)
    
    # Default ke check_answer umum
    logger.info(f"Mendelegasikan ke check_answer umum untuk chat_id: {chat_id}")
    return await check_answer(update, context)

# Fungsi utama untuk menjalankan bot
def main():
    # Token API dari BotFather
    application = Application.builder().token(BOT_TOKEN).build()

    # Menambahkan handler untuk /start
    application.add_handler(get_start_handler())
    application.add_handler(get_start_group_handler())
    application.add_handler(get_cancel_handler())
    application.add_handler(get_profile_handler())
    application.add_handler(get_leaderboard_handler())
    
    # Menambahkan handler untuk menangani callback tombol
    application.add_handler(CallbackQueryHandler(button))  # Menambahkan handler callback

    # Handler untuk grup
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.SUPERGROUP, check_answer_group))
    
    
    # Tambahkan handler utama tunggal
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_any_answer))
    
    # Mulai bot dan logging
    logger.info("Bot is starting...")
    application.run_polling()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()