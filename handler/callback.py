import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from models.game_bot import start_quiz  # Import fungsi start_quiz dari game_bot.py
from models.game_group import start_quiz_group # Import fungsi start_quiz dari game_group.py
from models.quiz_kanji import start_kanji_quiz, handle_kanji_button_answer  # Import fungsi untuk quiz kanji
from models.quiz_kotoba import start_kotoba_quiz, handle_kotoba_button_answer  # Import fungsi untuk quiz kotoba

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konstanta untuk jumlah part per halaman
PARTS_PER_PAGE = 10

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Ambil username pengguna
    user_name = query.from_user.username if query.from_user.username else "Unknown"
    chat_id = query.message.chat.id

    # Periksa apakah ini callback dari tombol jawaban kanji
    if query.data.startswith("kanji_option_"):
        return await handle_kanji_button_answer(update, context)
        
    # Periksa apakah ini callback dari tombol jawaban kotoba
    if query.data.startswith("kotoba_option_"):
        return await handle_kotoba_button_answer(update, context)

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
                [InlineKeyboardButton("Kanji N5", callback_data='kanji_n5_level')],
                [InlineKeyboardButton("Kanji N4", callback_data='kanji_n4_level')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tingkatan JLPT Kanji:", reply_markup=reply_markup)
        
        # Handler untuk quiz kotoba
        elif query.data == 'kotoba':
            keyboard = [
                [InlineKeyboardButton("Kotoba JLPT N5", callback_data='kotoba_n5_level')],
                [InlineKeyboardButton("Kotoba JLPT N4", callback_data='kotoba_n4_level')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tingkatan JLPT Kotoba:", reply_markup=reply_markup)

        # Handler untuk kotoba N5 - pilih tipe quiz
        elif query.data == 'kotoba_n5_level':
            keyboard = [
                [InlineKeyboardButton("Kotoba → Arti", callback_data='kotoba_n5_to_meaning')],
                [InlineKeyboardButton("Arti → Kotoba", callback_data='meaning_to_kotoba_n5')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tipe quiz Kotoba N5:", reply_markup=reply_markup)
            
        # Handler untuk kotoba N4 - pilih tipe quiz
        elif query.data == 'kotoba_n4_level':
            keyboard = [
                [InlineKeyboardButton("Kotoba → Arti", callback_data='kotoba_n4_to_meaning')],
                [InlineKeyboardButton("Arti → Kotoba", callback_data='meaning_to_kotoba_n4')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tipe quiz Kotoba N4:", reply_markup=reply_markup)
            
        # Handler untuk kotoba N5 to meaning - pilih part (halaman 1)
        elif query.data == 'kotoba_n5_to_meaning' or query.data == 'kotoba_n5_to_meaning_page_1':
            await show_part_selection(update, 'kotoba_n5_to_meaning', 1, 50)
            
        # Handler untuk meaning to kotoba N5 - pilih part (halaman 1)
        elif query.data == 'meaning_to_kotoba_n5' or query.data == 'meaning_to_kotoba_n5_page_1':
            await show_part_selection(update, 'meaning_to_kotoba_n5', 1, 50)
            
        # Handler untuk kotoba N4 to meaning - pilih part (halaman 1)
        elif query.data == 'kotoba_n4_to_meaning' or query.data == 'kotoba_n4_to_meaning_page_1':
            await show_part_selection(update, 'kotoba_n4_to_meaning', 1, 50)
            
        # Handler untuk meaning to kotoba N4 - pilih part (halaman 1)
        elif query.data == 'meaning_to_kotoba_n4' or query.data == 'meaning_to_kotoba_n4_page_1':
            await show_part_selection(update, 'meaning_to_kotoba_n4', 1, 50)
        
        # Handler untuk pagination kotoba N5 to meaning
        elif query.data.startswith('kotoba_n5_to_meaning_page_'):
            page_num = int(query.data.split('_page_')[1])
            await show_part_selection(update, 'kotoba_n5_to_meaning', page_num, 50)
            
        # Handler untuk pagination meaning to kotoba N5
        elif query.data.startswith('meaning_to_kotoba_n5_page_'):
            page_num = int(query.data.split('_page_')[1])
            await show_part_selection(update, 'meaning_to_kotoba_n5', page_num, 50)
            
        # Handler untuk pagination kotoba N4 to meaning
        elif query.data.startswith('kotoba_n4_to_meaning_page_'):
            page_num = int(query.data.split('_page_')[1])
            await show_part_selection(update, 'kotoba_n4_to_meaning', page_num, 50)
            
        # Handler untuk pagination meaning to kotoba N4
        elif query.data.startswith('meaning_to_kotoba_n4_page_'):
            page_num = int(query.data.split('_page_')[1])
            await show_part_selection(update, 'meaning_to_kotoba_n4', page_num, 50)
        
        # Handler untuk memilih tipe quiz Kanji N5
        elif query.data == 'kanji_n5_level':
            keyboard = [
                [InlineKeyboardButton("Kanji → Arti", callback_data='kanji_n5_to_meaning')],
                [InlineKeyboardButton("Arti → Kanji", callback_data='meaning_to_kanji_n5')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tipe quiz Kanji N5:", reply_markup=reply_markup)
            
        # Handler untuk memilih tipe quiz Kanji N4
        elif query.data == 'kanji_n4_level':
            keyboard = [
                [InlineKeyboardButton("Kanji → Arti", callback_data='kanji_n4_to_meaning')],
                [InlineKeyboardButton("Arti → Kanji", callback_data='meaning_to_kanji_n4')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih tipe quiz Kanji N4:", reply_markup=reply_markup)
            
        # Handler untuk memilih part dari Kanji N5 to meaning
        elif query.data == 'kanji_n5_to_meaning':
            keyboard = [
                # Part 01-02 (2 tombol per baris)
                [
                    InlineKeyboardButton("Part 01 (Kanji 1-10)", callback_data='kanji_n5_to_meaning_part_01'),
                    InlineKeyboardButton("Part 02 (Kanji 11-20)", callback_data='kanji_n5_to_meaning_part_02')
                ],
                # Part 03-04
                [
                    InlineKeyboardButton("Part 03 (Kanji 21-30)", callback_data='kanji_n5_to_meaning_part_03'),
                    InlineKeyboardButton("Part 04 (Kanji 31-40)", callback_data='kanji_n5_to_meaning_part_04')
                ],
                # Part 05-06
                [
                    InlineKeyboardButton("Part 05 (Kanji 41-50)", callback_data='kanji_n5_to_meaning_part_05'),
                    InlineKeyboardButton("Part 06 (Kanji 51-60)", callback_data='kanji_n5_to_meaning_part_06')
                ],
                # Part 07-08
                [
                    InlineKeyboardButton("Part 07 (Kanji 61-70)", callback_data='kanji_n5_to_meaning_part_07'),
                    InlineKeyboardButton("Part 08 (Kanji 71-80)", callback_data='kanji_n5_to_meaning_part_08')
                ],
                # Part 09
                [
                    InlineKeyboardButton("Part 09 (Kanji 81+)", callback_data='kanji_n5_to_meaning_part_09')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih bagian Kanji N5:", reply_markup=reply_markup)

        # Handler untuk memilih part dari Meaning to Kanji N5
        elif query.data == 'meaning_to_kanji_n5':
            keyboard = [
                # Part 01-02 (2 tombol per baris)
                [
                    InlineKeyboardButton("Part 01 (Kanji 1-10)", callback_data='meaning_to_kanji_n5_part_01'),
                    InlineKeyboardButton("Part 02 (Kanji 11-20)", callback_data='meaning_to_kanji_n5_part_02')
                ],
                # Part 03-04
                [
                    InlineKeyboardButton("Part 03 (Kanji 21-30)", callback_data='meaning_to_kanji_n5_part_03'),
                    InlineKeyboardButton("Part 04 (Kanji 31-40)", callback_data='meaning_to_kanji_n5_part_04')
                ],
                # Part 05-06
                [
                    InlineKeyboardButton("Part 05 (Kanji 41-50)", callback_data='meaning_to_kanji_n5_part_05'),
                    InlineKeyboardButton("Part 06 (Kanji 51-60)", callback_data='meaning_to_kanji_n5_part_06')
                ],
                # Part 07-08
                [
                    InlineKeyboardButton("Part 07 (Kanji 61-70)", callback_data='meaning_to_kanji_n5_part_07'),
                    InlineKeyboardButton("Part 08 (Kanji 71-80)", callback_data='meaning_to_kanji_n5_part_08')
                ],
                # Part 09
                [
                    InlineKeyboardButton("Part 09 (Kanji 81+)", callback_data='meaning_to_kanji_n5_part_09')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih bagian Arti ke Kanji N5:", reply_markup=reply_markup)
        
        # Handler untuk memilih part dari Kanji N4 to meaning
        elif query.data == 'kanji_n4_to_meaning':
            keyboard = [
                # Part 01-02 (2 tombol per baris)
                [
                    InlineKeyboardButton("Part 01 (Kanji 1-10)", callback_data='kanji_n4_to_meaning_part_01'),
                    InlineKeyboardButton("Part 02 (Kanji 11-20)", callback_data='kanji_n4_to_meaning_part_02')
                ],
                # Part 03-04
                [
                    InlineKeyboardButton("Part 03 (Kanji 21-30)", callback_data='kanji_n4_to_meaning_part_03'),
                    InlineKeyboardButton("Part 04 (Kanji 31-40)", callback_data='kanji_n4_to_meaning_part_04')
                ],
                # Part 05
                [
                    InlineKeyboardButton("Part 05 (Kanji 41+)", callback_data='kanji_n4_to_meaning_part_05')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih bagian Kanji N4:", reply_markup=reply_markup)

        # Handler untuk memilih part dari Meaning to Kanji N4
        elif query.data == 'meaning_to_kanji_n4':
            keyboard = [
                # Part 01-02 (2 tombol per baris)
                [
                    InlineKeyboardButton("Part 01 (Kanji 1-10)", callback_data='meaning_to_kanji_n4_part_01'),
                    InlineKeyboardButton("Part 02 (Kanji 11-20)", callback_data='meaning_to_kanji_n4_part_02')
                ],
                # Part 03-04
                [
                    InlineKeyboardButton("Part 03 (Kanji 21-30)", callback_data='meaning_to_kanji_n4_part_03'),
                    InlineKeyboardButton("Part 04 (Kanji 31-40)", callback_data='meaning_to_kanji_n4_part_04')
                ],
                # Part 05
                [
                    InlineKeyboardButton("Part 05 (Kanji 41+)", callback_data='meaning_to_kanji_n4_part_05')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Pilih bagian Arti ke Kanji N4:", reply_markup=reply_markup)

        # Tangani quiz kanji dengan fungsi khusus
        elif any(query.data.startswith(prefix) for prefix in [
            'kanji_n5_to_meaning_part_', 
            'kanji_n4_to_meaning_part_',
            'meaning_to_kanji_n5_part_', 
            'meaning_to_kanji_n4_part_'
        ]):
            await start_kanji_quiz(update, context, query.data)
        
        # Tangani quiz kotoba dengan fungsi khusus
        elif any(query.data.startswith(prefix) for prefix in [
            'kotoba_n5_to_meaning_part_', 
            'kotoba_n4_to_meaning_part_',
            'meaning_to_kotoba_n5_part_', 
            'meaning_to_kotoba_n4_part_'
        ]):
            await start_kotoba_quiz(update, context, query.data)
        
        # Tangani quiz lain dengan fungsi yang sudah ada
        elif any(query.data.startswith(prefix) for prefix in [
            'hiragana_basic', 'hiragana_all', 
            'katakana_basic', 'katakana_all'
        ]):
            await start_quiz(update, context, query.data)

    # Pastikan pesan berasal dari grup
    elif update.effective_chat.type == 'supergroup':
        # Kode for grup...
        pass


async def show_part_selection(update, quiz_type, page, total_parts):
    """
    Menampilkan halaman pemilihan part dengan navigasi next/back
    """
    query = update.callback_query
    
    # Hitung range part untuk halaman ini
    start_part = (page - 1) * PARTS_PER_PAGE + 1
    end_part = min(start_part + PARTS_PER_PAGE - 1, total_parts)
    
    # Buat keyboard dengan 2 tombol per baris
    keyboard = []
    current_row = []
    
    for part_num in range(start_part, end_part + 1):
        # Format part number dengan leading zeros (01, 02, etc)
        part_str = f"{part_num:02d}"
        
        # Tentukan range kata untuk part ini
        start_word = (part_num - 1) * 20 + 1
        end_word = part_num * 20
        button_text = f"Part {part_str} ({start_word}-{end_word})"
        
        # Buat callback data
        callback_data = f"{quiz_type}_part_{part_str}"
        
        # Tambahkan tombol ke baris saat ini
        current_row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        # Jika baris sudah berisi 2 tombol atau ini adalah part terakhir, tambahkan baris ke keyboard
        if len(current_row) == 2 or part_num == end_part:
            keyboard.append(current_row)
            current_row = []
    
    # Tambahkan tombol navigasi (back dan next)
    nav_row = []
    
    # Tombol Back (jika bukan halaman pertama)
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Back", callback_data=f"{quiz_type}_page_{page-1}"))
    
    # Tombol Next (jika masih ada part di halaman berikutnya)
    if end_part < total_parts:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"{quiz_type}_page_{page+1}"))
    
    # Tambahkan tombol navigasi jika ada
    if nav_row:
        keyboard.append(nav_row)
    
    # Tambahkan tombol kembali ke menu utama
    keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="kotoba")])
    
    # Tentukan judul halaman berdasarkan jenis quiz
    if quiz_type == 'kotoba_n5_to_meaning':
        title = "Pilih bagian Kotoba N5 → Arti:"
    elif quiz_type == 'meaning_to_kotoba_n5':
        title = "Pilih bagian Arti → Kotoba N5:"
    elif quiz_type == 'kotoba_n4_to_meaning':
        title = "Pilih bagian Kotoba N4 → Arti:"
    elif quiz_type == 'meaning_to_kotoba_n4':
        title = "Pilih bagian Arti → Kotoba N4:"
    else:
        title = "Pilih bagian:"
    
    # Info halaman
    page_info = f"Halaman {page}/{(total_parts + PARTS_PER_PAGE - 1) // PARTS_PER_PAGE}"
    
    # Tampilkan keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"{title}\n{page_info}", reply_markup=reply_markup)