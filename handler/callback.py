import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from models.game_bot import start_quiz  # Mengimpor fungsi start_quiz dari game_bot.py
from models.game_group import start_quiz_group # Mengimpor fungsi start_quiz dari game_group.py
# Fungsi untuk menangani pilihan quiz (Hiragana atau Katakana)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Ambil username pengguna
    user_name = query.from_user.username if query.from_user.username else "Unknown"
    chat_id = query.message.chat.id

    # Pastikan pesan berasal dari pesan pribadi
    if update.effective_chat.type == 'private':
        
        if query.data == 'hiragana':
            keyboard = [
                [InlineKeyboardButton("Basic", callback_data='hiragana_basic')],
                [InlineKeyboardButton("All", callback_data='hiragana_all')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Hiragana:", reply_markup=reply_markup)

        elif query.data == 'katakana':
            keyboard = [
                [InlineKeyboardButton("Basic", callback_data='katakana_basic')],
                [InlineKeyboardButton("All", callback_data='katakana_all')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Katakana:", reply_markup=reply_markup)
        
        elif query.data == 'kanji':
            keyboard = [
                [InlineKeyboardButton("Kanji N5", callback_data='kanji_n5')],
                [InlineKeyboardButton("Kanji N4", callback_data='kanji_n4')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Kanji:", reply_markup=reply_markup)

        elif query.data == 'hiragana_basic' or query.data == 'hiragana_all':
            await start_quiz(update, context, query.data)

        elif query.data == 'katakana_basic' or query.data == 'katakana_all':
            await start_quiz(update, context, query.data)
        
        elif query.data == 'kanji_n5' or query.data == 'kanji_n4':
            await start_quiz(update, context, query.data)

    # Pastikan pesan berasal dari grup
    elif update.effective_chat.type == 'supergroup':
        
        if query.data == 'hiragana_group':
            keyboard = [
                [InlineKeyboardButton("Basic", callback_data='hiragana_basic')],
                [InlineKeyboardButton("All", callback_data='hiragana_all')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Hiragana untuk grup:", reply_markup=reply_markup)

        elif query.data == 'katakana_group':
            keyboard = [
                [InlineKeyboardButton("Basic", callback_data='katakana_basic')],
                [InlineKeyboardButton("All", callback_data='katakana_all')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Katakana untuk grup:", reply_markup=reply_markup)
        
        elif query.data == 'kanji_group':
            keyboard = [
                [InlineKeyboardButton("Kanji N5", callback_data='kanji_n5')],
                [InlineKeyboardButton("Kanji N4", callback_data='kanji_n4')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih jenis quiz Kanji:", reply_markup=reply_markup)

        elif query.data == 'hiragana_basic' or query.data == 'hiragana_all':
            await start_quiz_group(update, context, query.data)

        elif query.data == 'katakana_basic' or query.data == 'katakana_all':
            await start_quiz_group(update, context, query.data)
        
        elif query.data == 'kanji_n5' or query.data == 'kanji_n4':
            await start_quiz_group(update, context, query.data)