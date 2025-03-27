import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes
from config.constants import user_quiz_data
from datetime import timedelta

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Cek apakah chat berada di grup atau tidak
    if update.effective_chat.type != 'private':
        await update.message.reply_text("❌ Kuis ini hanya bisa didalam bot\ngunakan /start_group untuk didalam grup.")
        return

    # Cek apakah user sedang mengerjakan kuis
    if chat_id in user_quiz_data:
        await update.message.reply_text("❗ Kamu sedang mengerjakan kuis.\nKetik /cancel untuk menutup kuis.")
        return
    
    # Hapus pesan sebelumnya jika ada
    if context.chat_data.get("last_message_id"):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data["last_message_id"])
            logger.info(f"Pesan sebelumnya dihapus: chat_id={chat_id}, message_id={context.chat_data['last_message_id']}")
        except Exception as e:
            logger.warning(f"Gagal menghapus pesan sebelumnya: chat_id={chat_id}, message_id={context.chat_data['last_message_id']}, error={e}")

    # Menyiapkan tombol pilihan untuk Hiragana dan Katakana
    keyboard = [
        [InlineKeyboardButton("Quiz Hiragana", callback_data='hiragana')],
        [InlineKeyboardButton("Quiz Katakana", callback_data='katakana')],
        [InlineKeyboardButton("Quiz Kanji", callback_data='kanji')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Kirim pesan baru
    sent_message = await update.message.reply_text(
        "Pilih quiz yang ingin kamu mainkan:", reply_markup=reply_markup
    )
    context.chat_data["last_message_id"] = sent_message.message_id

    # Menjadwalkan penghapusan pesan setelah 1 menit
    context.job_queue.run_once(
        delete_message,
        when=timedelta(minutes=1),
        data={'chat_id': chat_id, 'message_id': sent_message.message_id}
    )

async def start_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Cek apakah chat berada di grup atau tidak
    if update.effective_chat.type != 'group' and update.effective_chat.type != 'supergroup':
        await update.message.reply_text("❌ Kuis ini hanya bisa dijalankan di dalam grup. Gunakan /start untuk kuis pribadi.")
        return

    # Cek apakah grup sedang mengerjakan kuis
    if chat_id in user_quiz_data:
        await update.message.reply_text("❗ Kuis sedang berjalan di grup ini.\nKetik /cancel untuk menutup kuis.")
        return

    # Hapus pesan sebelumnya jika ada
    if context.chat_data.get("last_message_id"):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data["last_message_id"])
            logger.info(f"Pesan sebelumnya dihapus: chat_id={chat_id}, message_id={context.chat_data['last_message_id']}")
        except Exception as e:
            logger.warning(f"Gagal menghapus pesan sebelumnya: chat_id={chat_id}, message_id={context.chat_data['last_message_id']}, error={e}")

    # Menyiapkan tombol pilihan untuk Hiragana dan Katakana
    keyboard = [
        [InlineKeyboardButton("Quiz Hiragana", callback_data='hiragana_group')],
        [InlineKeyboardButton("Quiz Katakana", callback_data='katakana_group')],
        [InlineKeyboardButton("Quiz Kanji", callback_data='kanji_group')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

       # Kirim pesan baru
    sent_message = await update.message.reply_text(
        "Pilih quiz yang ingin kamu mainkan:", reply_markup=reply_markup
    )
    context.chat_data["last_message_id"] = sent_message.message_id

    # Menjadwalkan penghapusan pesan setelah 1 menit
    context.job_queue.run_once(
        delete_message,
        when=timedelta(minutes=1),
        data={'chat_id': chat_id, 'message_id': sent_message.message_id}
    )


async def delete_message(context):
    """Fungsi untuk menghapus pesan setelah 1 menit."""
    job_data = context.job.data  # Mengambil data dari job
    try:
        await context.bot.delete_message(chat_id=job_data['chat_id'], message_id=job_data['message_id'])
    except Exception as e:
        # Log jika pesan gagal dihapus (misalnya sudah dihapus sebelumnya)
        print(f"Failed to delete message: {e}")

# Handler untuk membatalkan kuis
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_quiz_data:
        del user_quiz_data[chat_id]
        await update.message.reply_text("🚫 Kuis dibatalkan.\nKetik /start untuk memulai lagi.")
    else:
        await update.message.reply_text("ketik /start untuk memulai kuis.")

# Membuat handler untuk /start
def get_start_handler():
    return CommandHandler('start', start)

# Membuat handler untuk /start
def get_start_group_handler():
    return CommandHandler('start_group', start_group)

def get_cancel_handler():
    return CommandHandler('cancel', cancel)