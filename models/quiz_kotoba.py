import logging
import re
import random
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes, CallbackQueryHandler
from config.constants import user_quiz_data
from database.database import add_user, update_exp

# Data quiz kotoba diimpor dari file terpisah
from quiz.quiz_kotoba_n5 import kotoba_n5_quiz
from quiz.quiz_kotoba_n4 import kotoba_n4_quiz

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

QUIZ, ANSWER = range(2)

# Fungsi untuk memulai quiz kotoba
async def start_kotoba_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_type=None):
    user_choice = update.callback_query.data
    logger.info(f"User memilih quiz: {user_choice}")
    chat_id = update.callback_query.message.chat.id
    user_name = update.callback_query.from_user.username  # Ambil username pengguna

    # Log saat pengguna memulai kuis
    log_message = f"Pengguna @{user_name} ({chat_id}) telah memulai quiz kotoba: {user_choice}"
    logger.info(log_message)
    # Kirim log ke grup Telegram
    await send_log_to_group(log_message, context)

    # Periksa apakah data kuis sudah ada atau belum
    if chat_id not in user_quiz_data:
        # Inisialisasi data kuis per pengguna dalam user_quiz_data
        user_quiz_data[chat_id] = {
            "quiz_questions": [],  # Soal yang akan diberikan
            "wrong_answers": [],   # Jawaban yang salah
            "attempts": 0,         # Jumlah percobaan per soal
            "total_quiz": 0,       # Total soal
            "start_time": time.time(),  # Waktu mulai kuis
            "quiz_type": quiz_type,  # Jenis quiz yang dipilih
            "current_question_index": 0,  # Indeks pertanyaan saat ini
            "score": 0  # Skor pengguna
        }

    # Tentukan soal berdasarkan pilihan jenis kuis
    questions = []
    
    # Mendapatkan part dari quiz_type
    part_number = 1
    if "_part_" in quiz_type:
        part_match = re.search(r'_part_(\d+)', quiz_type)
        if part_match:
            part_number = int(part_match.group(1))
    
    # Tentukan dataset yang digunakan berdasarkan jenis quiz
    if "kotoba_n5" in quiz_type:
        source_data = kotoba_n5_quiz
    elif "kotoba_n4" in quiz_type:
        source_data = kotoba_n4_quiz
    else:
        # Default ke N5 jika tidak dikenali
        source_data = kotoba_n5_quiz
    
    # Menghitung range untuk pemilihan kotoba (20 kata per bagian)
    start_idx = (part_number - 1) * 20
    end_idx = min(start_idx + 20, len(source_data))
    
    # Ambil subset pertanyaan kotoba (sesuai dengan jenis quiz)
    subset_data = source_data[start_idx:end_idx].copy()
    
    # Untuk quiz arti -> kotoba, kita perlu memformat pertanyaan dan jawaban
    if "meaning_to_kotoba" in quiz_type:
        # Untuk setiap item di subset_data, buat pertanyaan dengan format "Kata mana yang berarti: {arti}?"
        for item in subset_data:
            question_item = {
                "question": f"Kata mana yang berarti: {item['kana']}?",
                "answer": item['kanji'],
                "kana": item['kana'],
                "deskripsi": item.get('deskripsi', ''),
                "arti": item['arti']
            }
            questions.append(question_item)
    else:
        # Untuk quiz kotoba -> arti, pertanyaan adalah kanji/kata Jepangnya
        for item in subset_data:
            question_item = {
                "question": f"Apa arti dari kata | {item['kanji']} |",
                "answer": item['arti'],
                "kana": item['kana'],
                "deskripsi": item.get('deskripsi', ''),
                "kanji": item['kanji']
            }
            questions.append(question_item)

    user_quiz_data[chat_id]["quiz_questions"] = questions
    random.shuffle(user_quiz_data[chat_id]["quiz_questions"])  # Mengacak soal
    user_quiz_data[chat_id]["total_quiz"] = len(user_quiz_data[chat_id]["quiz_questions"])
    
    # Pastikan soal tersedia
    if len(user_quiz_data[chat_id]["quiz_questions"]) == 0:
        await update.callback_query.edit_message_text("Tidak ada soal yang tersedia untuk kuis ini.")
        return ConversationHandler.END

    await update.callback_query.edit_message_text(f"Quiz Kotoba akan segera dimulai!")
    logger.info("Quiz kotoba dimulai.")
    
    # Menampilkan soal pertama
    await show_quiz_question(update, context, chat_id)
    
    return QUIZ

# Fungsi untuk escape karakter khusus dalam MarkdownV2
def escape_markdown(text):
    # Escape karakter khusus dalam MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

# Fungsi untuk membuat teks tersensor/blur
def create_spoiler_text(text):
    # Escape karakter khusus sebelum menambahkan format spoiler
    escaped_text = escape_markdown(text)
    return f"||{escaped_text}||"

# Fungsi untuk mengirim pesan kotoba→arti yang konsisten
async def send_kotoba_to_meaning_question(context, chat_id, current_question, quiz_info):
    kanji = current_question.get("kanji", "")
    kana = current_question.get("kana", "")
    
    # Log untuk debugging
    logger.info(f"Mengirim pertanyaan: Kanji: {kanji}, Kana: {kana}")
    
    # Format pesan dengan HTML
    message_text = f"{quiz_info}\n\nApa arti dari kata | {kanji} |\nCara baca: <tg-spoiler>{kana}</tg-spoiler>\n\nKetikkan arti dari kata ini:"
    
    try:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode="HTML"
        )
        
        # Tambahkan instruksi
        await context.bot.send_message(
            chat_id=chat_id,
            text="Pastikan jawaban kamu diakhiri dengan tanda baca titik (.)\nContoh: 'buku.'"
        )
        
        return message
    except Exception as e:
        logger.error(f"Error saat mengirim pesan: {e}")
        # Fallback tanpa format
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"{quiz_info}\n\nApa arti dari kata | {kanji} |\n\nKetikkan arti dari kata ini:"
        )
        
        # Tambahkan instruksi
        await context.bot.send_message(
            chat_id=chat_id,
            text="Pastikan jawaban kamu diakhiri dengan tanda baca titik (.)\nContoh: 'buku.'"
        )
        
        return message

# Fungsi untuk menampilkan pertanyaan quiz
async def show_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    current_question = user_quiz_data[chat_id]["quiz_questions"][0]
    quiz_type = user_quiz_data[chat_id]["quiz_type"]
    
    # Tampilkan informasi tentang jenis quiz
    quiz_info = get_quiz_info_text(quiz_type)
    
    # Format pertanyaan berdasarkan tipe quiz
    if "meaning_to_kotoba" in quiz_type:
        # Quiz arti -> kotoba
        question = current_question["question"]
        kana_spoiler = create_spoiler_text(current_question["kana"])
        arti = current_question["arti"]
        
        # Escape karakter khusus dalam pertanyaan
        escaped_question = escape_markdown(question)
        escaped_quiz_info = escape_markdown(quiz_info)
        
        # Pilih dataset yang sesuai untuk pilihan jawaban
        if "meaning_to_kotoba_n5" in quiz_type:
            source_data = kotoba_n5_quiz
        elif "meaning_to_kotoba_n4" in quiz_type:
            source_data = kotoba_n4_quiz
        else:
            source_data = kotoba_n5_quiz
        
        # Ambil beberapa jawaban salah dari seluruh kotoba
        all_kanji = [item['kanji'] for item in source_data]
        correct_kanji = current_question["answer"]
        wrong_options = [k for k in all_kanji if k != correct_kanji]
        random.shuffle(wrong_options)
        
        # Ambil 3 jawaban salah
        options = wrong_options[:3]
        options.append(correct_kanji)
        random.shuffle(options)  # Acak posisi jawaban benar
        
        # Simpan jawaban yang benar dan opsi untuk pemeriksaan nanti
        user_quiz_data[chat_id]["current_options"] = options
        user_quiz_data[chat_id]["correct_answer"] = correct_kanji
        
        # Buat tombol dalam 2 baris, 2 kanji per baris
        keyboard = [
            # Baris 1: 2 kanji pertama
            [
                InlineKeyboardButton(options[0], callback_data=f"kotoba_option_0_{options[0]}"),
                InlineKeyboardButton(options[1], callback_data=f"kotoba_option_1_{options[1]}")
            ],
            # Baris 2: 2 kanji terakhir
            [
                InlineKeyboardButton(options[2], callback_data=f"kotoba_option_2_{options[2]}"),
                InlineKeyboardButton(options[3], callback_data=f"kotoba_option_3_{options[3]}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Format pesan dengan HTML yang lebih aman
        message_text = f"{quiz_info}\n\n{question}\nCara baca: <tg-spoiler>{current_question['arti']}</tg-spoiler>\n\nPilih kanji yang sesuai:"
        
        # Kirim message dengan HTML
        try:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error saat mengirim pesan: {e}")
            # Fallback tanpa format
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"{quiz_info}\n\n{question}\n\nPilih kanji yang sesuai:",
                reply_markup=reply_markup
            )
    else:
        # Quiz kotoba -> arti (kanji/kata -> arti)
        # Gunakan fungsi khusus untuk pengiriman yang konsisten
        message = await send_kotoba_to_meaning_question(context, chat_id, current_question, quiz_info)
    
    # Simpan message_id untuk referensi
    user_quiz_data[chat_id]["last_message_id"] = message.message_id

# Fungsi untuk menampilkan pertanyaan quiz tanpa job_queue
async def show_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    # Pastikan masih ada soal tersisa
    if chat_id not in user_quiz_data or not user_quiz_data[chat_id]["quiz_questions"]:
        logger.warning(f"Tidak ada soal tersisa untuk chat_id {chat_id}")
        return
    
    current_question = user_quiz_data[chat_id]["quiz_questions"][0]
    quiz_type = user_quiz_data[chat_id]["quiz_type"]
    
    # Tampilkan informasi tentang jenis quiz
    quiz_info = get_quiz_info_text(quiz_type)
    
    # Format pertanyaan
    kanji = current_question.get("kanji", "")
    kana = current_question.get("kana", "")
    
    # Untuk quiz kotoba -> arti
    question_text = f"{quiz_info}\n\nApa arti dari kata | {kanji} |\nCara baca: <tg-spoiler>{kana}</tg-spoiler>\n\nKetikkan arti dari kata ini:"
    
    try:
        # Kirim soal dengan format HTML untuk spoiler
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=question_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error saat mengirim soal berikutnya: {e}")
        # Fallback tanpa format spoiler
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{quiz_info}\n\nApa arti dari kata | {kanji} |\nCara baca: {kana}\n\nKetikkan arti dari kata ini:"
        )
        

# Fungsi untuk menangani jawaban dari tombol (khusus quiz arti->kotoba)
async def handle_kotoba_button_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Tanggapi callback query untuk menghilangkan loading state
    
    chat_id = update.effective_chat.id
    user_name = update.callback_query.from_user.username
    
    # Periksa apakah pengguna sedang mengerjakan quiz
    if chat_id not in user_quiz_data:
        await query.edit_message_text("Tidak ada quiz yang sedang berjalan. Ketik /start untuk memulai.")
        return ConversationHandler.END
    
    # Pastikan callback data diawali dengan "kotoba_option_"
    if not query.data.startswith("kotoba_option_"):
        return QUIZ
    
    # Ekstrak pilihan user dan kata yang dipilih
    _, _, index, chosen_kotoba = query.data.split("_", 3)
    correct_answer = user_quiz_data[chat_id]["correct_answer"]
    
    # Hitung progress
    progress = user_quiz_data[chat_id]["total_quiz"] - len(user_quiz_data[chat_id]["quiz_questions"]) + 1
    total = user_quiz_data[chat_id]["total_quiz"]
    
    # Buat progress bar visual
    bar_length = 10
    filled_length = int(bar_length * progress / total)
    progress_bar = '▓' * filled_length + '░' * (bar_length - filled_length)
    
    # Persiapkan deskripsi dan informasi tambahan
    current_question = user_quiz_data[chat_id]["quiz_questions"][0]
    description_text = ""
    if "deskripsi" in current_question and current_question["deskripsi"]:
        description_text = f"\n{current_question['deskripsi']}\n"
    
    # Periksa jawaban
    if chosen_kotoba == correct_answer:
        # Jawaban benar
        user_quiz_data[chat_id]["score"] += 1
        
        # Ubah teks pesan dengan jawaban yang benar
        message_text = f"✅ Jawaban benar!\nKanji: {correct_answer}\nArtinya: {current_question['arti']}\nCara baca: {current_question['kana']}{description_text}\n📊 Progres: {progress_bar} ({progress:02}/{total})"
        
        await query.edit_message_text(text=message_text)
        logger.info(f"Jawaban benar untuk pertanyaan: {current_question['question']}")
    else:
        # Jawaban salah
        # Simpan jawaban yang salah untuk rekap
        user_quiz_data[chat_id]["wrong_answers"].append({
            "question": current_question["question"],
            "user_answer": chosen_kotoba,
            "correct_answer": correct_answer
        })
        
        # Ubah teks pesan dengan jawaban yang benar
        message_text = f"❌ Jawaban salah!\nJawaban yang benar adalah: {correct_answer}\nCara baca: {current_question['kana']}{description_text}\nArtinya: {current_question['arti']}\n\n📊 Progres: {progress_bar} ({progress:02}/{total})"
        
        await query.edit_message_text(text=message_text)
        logger.info(f"Jawaban salah untuk pertanyaan: {current_question['question']}")
    
    # Hapus soal yang sudah dijawab
    user_quiz_data[chat_id]["quiz_questions"].pop(0)
    
    # Periksa apakah masih ada soal
    if user_quiz_data[chat_id]["quiz_questions"]:
        # Tunggu 0.5 detik sebelum menampilkan soal berikutnya
        await context.bot.send_message(
            chat_id=chat_id,
            text="Soal berikutnya akan ditampilkan..."
        )
        
        # PERUBAHAN: Langsung memanggil show_quiz_question daripada menggunakan job_queue
        await show_quiz_question(update, context, chat_id)
        
        return QUIZ
    else:
        # Quiz selesai, tampilkan rekap
        await show_quiz_summary(update, context, chat_id)
        
        # Reset data quiz
        del user_quiz_data[chat_id]
        logger.info("Quiz kotoba selesai.")
        return ConversationHandler.END

# Fungsi untuk memeriksa jawaban kotoba (khusus kotoba->arti)
async def check_kotoba_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pastikan pesan datang dari pribadi
    if update.effective_chat.type != 'private':
        return  # Jika bukan pesan pribadi, tidak diproses lebih lanjut
    
    user_answer = update.message.text.strip().lower()
    chat_id = update.message.chat.id

    # Ambil username pengguna dari pesan
    user_name = update.message.from_user.username
    
    # Pastikan chat_id ada dalam data kuis
    if chat_id not in user_quiz_data or len(user_quiz_data[chat_id]["quiz_questions"]) == 0:
        return  # Tidak ada quiz aktif, jadi tidak perlu diproses

    # Pastikan ini adalah quiz kotoba->arti
    if "meaning_to_kotoba" in user_quiz_data[chat_id]["quiz_type"]:
        # Ini seharusnya menggunakan tombol, bukan text input
        await update.message.reply_text("Silakan gunakan tombol untuk menjawab quiz ini.")
        return QUIZ

    # Pastikan ini adalah quiz kotoba
    if not any(prefix in user_quiz_data[chat_id]["quiz_type"] for prefix in ["kotoba_n5_to_meaning", "kotoba_n4_to_meaning"]):
        return  # Bukan quiz kotoba

    # Validasi format jawaban
    if not user_answer.endswith('.'):
        await update.message.reply_text("Jawaban harus diakhiri dengan tanda baca titik (.)!")
        logger.warning("Jawaban pengguna tidak diakhiri dengan titik.")
        return QUIZ

    # Menghapus titik dari jawaban untuk pemeriksaan
    user_answer = user_answer[:-1].strip()

    current_question = user_quiz_data[chat_id]["quiz_questions"][0]
    correct_answers = current_question["answer"].lower().split(",")
    correct_answers = [ans.strip() for ans in correct_answers]  # Bersihkan spasi di setiap jawaban
    
    logger.info(f"Jawaban pengguna: {user_answer}, Jawaban benar: {correct_answers}")

    # Hitung progress
    progress = user_quiz_data[chat_id]["total_quiz"] - len(user_quiz_data[chat_id]["quiz_questions"]) + 1
    total = user_quiz_data[chat_id]["total_quiz"]
    
    # Buat progress bar visual
    bar_length = 10
    filled_length = int(bar_length * progress / total)
    progress_bar = '▓' * filled_length + '░' * (bar_length - filled_length)
    
    # Persiapkan deskripsi
    description_text = ""
    if "deskripsi" in current_question and current_question["deskripsi"]:
        description_text = f"\n{current_question['deskripsi']}\n"

    # Memeriksa apakah jawaban pengguna benar atau salah
    if any(correct_answer == user_answer for correct_answer in correct_answers):
        # Jawaban benar
        user_quiz_data[chat_id]["score"] += 1
        
        # Teks respons
        message_text = f"✅ Jawaban benar!\nKanji: {current_question['kanji']}\nCara baca: {current_question['kana']}{description_text}\nArtinya: {current_question['answer']}\n\n📊 Progres: {progress_bar} ({progress:02}/{total})"
        
        await update.message.reply_text(message_text)

        logger.info(f"Jawaban benar untuk pertanyaan: {current_question['question']}")
        user_quiz_data[chat_id]["attempts"] = 0  # Reset percobaan
        
    else:
        # Jawaban salah, periksa apakah ini percobaan pertama
        if user_quiz_data[chat_id]["attempts"] == 0:
            await update.message.reply_text("Jawaban salah! Silakan coba lagi.")
            user_quiz_data[chat_id]["attempts"] += 1
            return ANSWER  # Memberikan kesempatan kedua
        else:
            # Simpan jawaban yang salah untuk rekap di akhir
            user_quiz_data[chat_id]["wrong_answers"].append({
                "question": current_question["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answers
            })

            # Format tampilan jawaban yang benar
            formatted_answers = ", ".join(correct_answers)
            await update.message.reply_text(f"Jawaban salah!\nJawaban yang benar adalah: {formatted_answers}\nKanji: {current_question['kanji']}\nCara baca: {current_question['kana']}{description_text}\n\n📊 Progres: {progress_bar} ({progress:02}/{total})")
            logger.info(f"Jawaban salah untuk pertanyaan: {current_question['question']}")
            user_quiz_data[chat_id]["attempts"] = 0  # Reset percobaan

    # Hapus soal yang sudah ditanyakan
    user_quiz_data[chat_id]["quiz_questions"].pop(0)

    # Lanjutkan soal berikutnya atau selesai
    if user_quiz_data[chat_id]["quiz_questions"]:
        # Masih ada soal berikutnya
        await update.message.reply_text("Soal berikutnya akan ditampilkan...")
        
        # PENTING: Gunakan show_quiz_question yang SAMA seperti yang digunakan oleh handle_kotoba_button_answer
        # Ini akan memastikan konsistensi format antara kedua mode
        await show_next_question(update, context, chat_id)
        
        return QUIZ
    else:
        # Quiz selesai, tampilkan rekap
        await show_quiz_summary(update, context, chat_id)
        
        # Reset data quiz
        del user_quiz_data[chat_id]
        logger.info("Quiz kotoba selesai.")
        return ConversationHandler.END

# Fungsi untuk menampilkan ringkasan quiz
async def show_quiz_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    # Ambil username pengguna dan user_id
    if update.callback_query:
        user_name = update.callback_query.from_user.full_name
        user_id = update.callback_query.from_user.id
    else:
        user_name = update.message.from_user.full_name
        user_id = update.message.from_user.id
    
    # Tambahkan/update user di database
    add_user(telegram_id=user_id, nama=user_name)
    
    # Hitung waktu yang dihabiskan
    start_time = user_quiz_data[chat_id]["start_time"]
    time_taken = time.time() - start_time
    minutes = int(time_taken // 60)
    seconds = int(time_taken % 60)

    # Hitung jumlah jawaban benar dan salah
    total_questions = user_quiz_data[chat_id]["total_quiz"]
    wrong_answers_count = len(user_quiz_data[chat_id]["wrong_answers"])
    correct_answers_count = total_questions - wrong_answers_count

    # Persentase keberhasilan
    success_percentage = (correct_answers_count / total_questions) * 100
    
    # TAMBAHAN: Hitung total exp yang didapat
    exp_per_correct_answer = 2
    base_exp_earned = correct_answers_count * exp_per_correct_answer
    
    # Bonus exp jika menyelesaikan quiz (bonus tergantung jumlah soal)
    # Untuk setiap soal yang diselesaikan, berikan bonus 1 exp (jadi total 10 untuk 10 soal)
    bonus_exp = min(10, total_questions)  # Max 10 exp
    total_exp_earned = base_exp_earned + bonus_exp
    
    # Update exp pengguna di database
    exp_result = update_exp(telegram_id=user_id, exp_gain=total_exp_earned)

    # Pesan ringkasan
    recap_message = (
        f"🎉 Kuis selesai! Kerja bagus {user_name}.\n"
        f"🕒 Waktu yang dihabiskan: {minutes} menit {seconds} detik.\n\n"
        f"📊 Hasil Quiz:\n"
        f"Total soal: {total_questions}\n"
        f"Jawaban benar: {correct_answers_count} ({success_percentage:.1f}%)\n"
        f"Jawaban salah: {wrong_answers_count}\n\n"
        f"💫 EXP diperoleh:\n"
        f"• {base_exp_earned} EXP ({correct_answers_count} jawaban benar × 2 EXP)\n"
        f"• {bonus_exp} EXP bonus (menyelesaikan quiz)\n"
        f"Total: +{total_exp_earned} EXP\n"
    )
    
    # Tambahkan informasi level up jika terjadi
    if exp_result and exp_result['leveled_up']:
        recap_message += f"\n🎖️ LEVEL UP! Anda naik ke level {exp_result['new_level']}! 🎖️\n"
        recap_message += f"EXP menuju level berikutnya: {exp_result['current_exp']}/{exp_result['exp_needed']}\n"
    elif exp_result:
        recap_message += f"\nLevel saat ini: {exp_result['new_level']}\n"
        recap_message += f"EXP: {exp_result['current_exp']}/{exp_result['exp_needed']}\n"

    # Tambahkan detail jawaban salah jika ada
    if user_quiz_data[chat_id]["wrong_answers"]:
        recap = "\nBerikut adalah rekap jawaban yang salah:\n\n"
        for item in user_quiz_data[chat_id]["wrong_answers"]:
            if isinstance(item['correct_answers'], list):
                correct = ', '.join(item['correct_answers'])
            else:
                correct = item['correct_answers']
                
            recap += (
                f"Pertanyaan: {item['question']}\n"
                f"Jawaban kamu: {item['user_answer']}\n"
                f"Jawaban yang benar: {correct}\n\n"
            )
        recap_message += recap

    # Kirim rekap ke grup log dan pengguna
    await send_log_to_group(recap_message, context)
    
    if update.callback_query:
        await context.bot.send_message(chat_id=chat_id, text=recap_message)
    else:
        await update.message.reply_text(recap_message)

# Helper function untuk mendapatkan teks informasi quiz
def get_quiz_info_text(quiz_type):
    if "kotoba_n5_to_meaning" in quiz_type:
        return "📝 Quiz Kotoba N5 → Arti\nTulis arti dari kata yang ditampilkan."
    elif "meaning_to_kotoba_n5" in quiz_type:
        return "📝 Quiz Arti → Kotoba N5\nPilih kata yang sesuai dengan arti yang diberikan."
    elif "kotoba_n4_to_meaning" in quiz_type:
        return "📝 Quiz Kotoba N4 → Arti\nTulis arti dari kata yang ditampilkan."
    elif "meaning_to_kotoba_n4" in quiz_type:
        return "📝 Quiz Arti → Kotoba N4\nPilih kata yang sesuai dengan arti yang diberikan."
    else:
        return "📝 Quiz Kotoba\nJawab pertanyaan dengan benar."

# Fungsi untuk mengirim log ke grup Telegram
async def send_log_to_group(log_message: str, context: ContextTypes.DEFAULT_TYPE):
    group_chat_id = '-1002593183248'  # Ganti dengan chat_id grup Anda
    await context.bot.send_message(chat_id=group_chat_id, text=log_message)