import logging
import re  # Tambahkan di bagian atas file untuk regex
import random  # Import random untuk mengacak soal
import time  # Import time untuk menghitung durasi kuis
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from quiz.quiz import hiragana_quiz, katakana_quiz, hiragana_quiz_full, katakana_quiz_full  # Mengimpor quiz Hiragana
from quiz.quiz_kanji import kanji_n5_quiz, kanji_n4_quiz
from quiz.quiz_kotoba_n5 import kotoba_n5_tubuh_kesehatan, kotoba_n5_waktu  # Mengimpor quiz Kotoba N5
from telegram.ext import ConversationHandler, ContextTypes
from config.constants import user_quiz_data

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

QUIZ, ANSWER = range(2)

# Fungsi untuk memulai kuis Hiragana atau Katakana
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_type=None):
    user_choice = update.callback_query.data
    logger.info(f"User chose quiz: {user_choice}")
    chat_id = update.callback_query.message.chat.id
    user_name = update.callback_query.from_user.username  # Ambil username pengguna

    # Log saat pengguna memulai kuis
    log_message = f"User @{user_name} ({chat_id}) has started the quiz."
    logger.info(log_message)
    # Kirim log ke grup Telegram
    await send_log_to_group(log_message, context)  # Panggil fungsi dengan context

    # Periksa apakah data kuis sudah ada atau belum
    if chat_id not in user_quiz_data:
        # Inisialisasi data kuis per pengguna dalam user_quiz_data
        user_quiz_data[chat_id] = {
            "quiz_questions": [],  # Soal yang akan diberikan
            "wrong_answers": [],  # Jawaban yang salah
            "attempts": 0,  # Jumlah percakapan
            "total_quiz": 0,  # Total soal
            "start_time": time.time()  # Waktu mulai kuis
        }

    # Tentukan soal berdasarkan pilihan jenis kuis
    questions = []
    if quiz_type == 'hiragana_basic':
        questions = hiragana_quiz.copy()
    elif quiz_type == 'hiragana_all':
        questions = hiragana_quiz_full.copy()
    elif quiz_type == 'katakana_basic':
        questions = katakana_quiz.copy()
    elif quiz_type == 'katakana_all':
        questions = katakana_quiz_full.copy()
    elif quiz_type == 'kanji_n5':
        questions = kanji_n5_quiz.copy()
    elif quiz_type == 'kanji_n4':
        questions = kanji_n4_quiz.copy()
    elif quiz_type == 'kotoba_n5_part_01':
        questions = kotoba_n5_tubuh_kesehatan.copy()
    elif quiz_type == 'kotoba_n5_part_02':
        questions = kotoba_n5_waktu.copy()
    
    # Preprocessing untuk ekstraksi hiragana dari description
    for q in questions:
        if "description" in q and "Hiragana:" in q["description"]:
            hiragana_match = re.search(r"Hiragana:\s+(\S+)", q["description"])
            if hiragana_match:
                q["hiragana"] = hiragana_match.group(1)
    
    user_quiz_data[chat_id]["quiz_questions"] = questions
    random.shuffle(user_quiz_data[chat_id]["quiz_questions"])  # Mengacak soal
    user_quiz_data[chat_id]["total_quiz"] = len(user_quiz_data[chat_id]["quiz_questions"])  # Simpan total soal

    # Pastikan soal tersedia
    if len(user_quiz_data[chat_id]["quiz_questions"]) == 0:
        await update.callback_query.edit_message_text("Tidak ada soal yang tersedia untuk kuis ini.")
        return ConversationHandler.END

    current_question = user_quiz_data[chat_id]["quiz_questions"][0]
    question = current_question["question"]
    logger.info(f"Question to ask: {question}")
    
    await update.callback_query.edit_message_text(f"Permainan akan segera dimulai!")
    logger.info("Question start.")
    
    # Tambahkan hiragana dengan spoiler jika tersedia
    hiragana_text = ""
    if "hiragana" in current_question:
        hiragana_text = f"\n<tg-spoiler>Hiragana: {current_question['hiragana']}</tg-spoiler>"
    
    # Kirim pertanyaan dengan hiragana spoiler jika ada
    await update.callback_query.message.reply_text(
        f"{question}{hiragana_text}\nSilakan jawab:", 
        parse_mode="HTML"
    )
    logger.info("Question sent to user.")

    # Mengirimkan pesan pemberitahuan sebelum kuis dimulai
    await update.callback_query.message.reply_text("Pastikan setiap jawaban kamu diakhiri dengan tanda baca titik (.)\n\nContoh: 'ma.'")
    logger.info("Quiz notification sent to user.")
    
    return QUIZ

# Fungsi untuk memeriksa jawaban
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pastikan pesan datang dari pribadi
    if update.effective_chat.type != 'private':
        return  # Jika bukan pesan pribadi, tidak diproses lebih lanjut
    
    user_answer = update.message.text.strip().lower()
    chat_id = update.message.chat.id  # Ambil chat_id dari message untuk perhitungan percakapan

    # Ambil username pengguna, pastikan callback_query ada
    if update.callback_query:
        user_name = update.callback_query.from_user.username  # Ambil username pengguna dari callback
    else:
        user_name = update.message.from_user.username  # Ambil username dari message
    
    # Pastikan chat_id ada dalam data kuis
    if chat_id not in user_quiz_data or len(user_quiz_data[chat_id]["quiz_questions"]) == 0:
        await update.message.reply_text("Soal tidak ditemukan. Mungkin kuis telah selesai.")
        return ConversationHandler.END

    correct_answers = user_quiz_data[chat_id]["quiz_questions"][0]["answer"].lower().split(",")  # Memisahkan jawaban yang benar
    logger.info(f"User answer: {user_answer}, Correct answer: {correct_answers}")

    if not user_answer.endswith('.'):
        await update.message.reply_text("Jawaban harus diakhiri dengan tanda baca titik (.)!")
        logger.warning("User answer did not end with a dot.")
        return QUIZ

    # Menghapus titik dari jawaban untuk pemeriksaan
    user_answer = user_answer[:-1]

    # Memeriksa apakah jawaban pengguna benar atau salah
    if any(correct_answer.strip() == user_answer for correct_answer in correct_answers):
        # Hitung progress
        progress = user_quiz_data[chat_id]["total_quiz"] - len(user_quiz_data[chat_id]["quiz_questions"]) + 1
        total = user_quiz_data[chat_id]["total_quiz"]

        # Periksa apakah pertanyaan memiliki deskripsi
        current_question = user_quiz_data[chat_id]["quiz_questions"][0]
        description_text = ""
        if "description" in current_question:
            description_text = f"\n{current_question['description']}\n"

        # Ambil link dari soal saat ini
        question_link = current_question.get("link", None)  # Tidak ada link akan menjadi None

        # Buat tombol hanya jika ada link
        reply_markup = None
        if question_link:
            keyboard = [
                [InlineKeyboardButton("Info Detail", url=question_link)]  # Menggunakan link dari soal
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

        # Buat progress bar (maks 10 blok visual)
        bar_length = 10
        filled_length = int(bar_length * progress / total)
        progress_bar = '▓' * filled_length + '░' * (bar_length - filled_length)

        # Kirim respons dengan tombol jika ada link, atau tanpa tombol
        message_text = f"✅ Jawaban benar!\n{description_text}\n📊 Progres: {progress_bar} ({progress:02}/{total})"
        
        if reply_markup:
            await update.message.reply_text(message_text, reply_markup=reply_markup)  # Kirim dengan tombol jika ada
        else:
            await update.message.reply_text(message_text)  # Kirim tanpa tombol jika tidak ada

        logger.info(f"Answer was correct for question: {user_quiz_data[chat_id]['quiz_questions'][0]['question']}")
        user_quiz_data[chat_id]["attempts"] = 0  # Reset attempts setelah benar
    else:
        if user_quiz_data[chat_id]["attempts"] == 0:
            await update.message.reply_text("Jawaban salah! Silakan coba lagi.")
            user_quiz_data[chat_id]["attempts"] += 1
            return ANSWER  # Memberikan kesempatan kedua
        else:
            # Simpan jawaban yang salah
            user_quiz_data[chat_id]["wrong_answers"].append({
                "question": user_quiz_data[chat_id]["quiz_questions"][0]["question"],
                "user_answer": user_answer,
                "correct_answers": correct_answers
            })

            await update.message.reply_text(f"Jawaban salah!\nJawaban yang benar adalah: {correct_answers}")
            logger.error(f"Answer was incorrect for question: {user_quiz_data[chat_id]['quiz_questions'][0]['question']}")
            user_quiz_data[chat_id]["attempts"] = 0  # Reset attempts setelah 2 kali salah

    # Hapus soal yang sudah ditanyakan
    user_quiz_data[chat_id]["quiz_questions"].pop(0)

    # Lanjutkan soal berikutnya atau selesai
    if user_quiz_data[chat_id]["quiz_questions"]:
        next_question = user_quiz_data[chat_id]["quiz_questions"][0]["question"]
        
        # Tambahkan hiragana dengan spoiler jika tersedia
        hiragana_text = ""
        if "hiragana" in user_quiz_data[chat_id]["quiz_questions"][0]:
            hiragana = user_quiz_data[chat_id]["quiz_questions"][0]["hiragana"]
            hiragana_text = f"\n<tg-spoiler>Hiragana: {hiragana}</tg-spoiler>"
        
        await update.message.reply_text(
            f"Soal berikutnya:\n{next_question}{hiragana_text}", 
            parse_mode="HTML"
        )
        logger.info(f"Next question: {next_question}")
        return QUIZ
    else:
        # Kirim waktu yang dihabiskan
        start_time = user_quiz_data[chat_id]["start_time"]
        time_taken = time.time() - start_time

        minutes = int(time_taken // 60)
        seconds = int(time_taken % 60)

        # Kuis selesai, kirim rekap jawaban yang salah dan benar
        correct_answers_count = user_quiz_data[chat_id]["total_quiz"] - len(user_quiz_data[chat_id]["quiz_questions"]) - len(user_quiz_data[chat_id]["wrong_answers"])
        wrong_answers_count = len(user_quiz_data[chat_id]["wrong_answers"])

        recap_message = f"🎉 Kuis selesai! Kerja bagus {user_name}.\n" \
                        f"🕒 Waktu yang dihabiskan: {minutes} menit {seconds} detik.\n\n" \
                        f"Jawaban benar: {correct_answers_count}\n" \
                        f"Jawaban salah: {wrong_answers_count}\n"

        if user_quiz_data[chat_id]["wrong_answers"]:
            recap = "Berikut adalah rekap jawaban yang salah:\n\n"
            for item in user_quiz_data[chat_id]["wrong_answers"]:
                recap += f"Pertanyaan: {item['question']}\n" \
                         f"Jawaban kamu: {item['user_answer']}\n" \
                         f"Jawaban yang benar: {item['correct_answers']}\n\n"

            recap_message += recap

        # Kirim rekap ke grup log
        await send_log_to_group(recap_message, context)
        await update.message.reply_text(recap_message)

        # Reset data kuis
        del user_quiz_data[chat_id]
        logger.info("Quiz completed.")
        return ConversationHandler.END

    
# Fungsi untuk mengirim log ke grup Telegram
async def send_log_to_group(log_message: str, context: ContextTypes.DEFAULT_TYPE):
    group_chat_id = '-1002593183248'  # Ganti dengan chat_id grup Anda
    await context.bot.send_message(chat_id=group_chat_id, text=log_message)
