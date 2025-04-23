import logging
import random  # Import random untuk mengacak soal
import time  # Import time untuk menghitung durasi kuis
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from quiz.quiz import hiragana_quiz, katakana_quiz, hiragana_quiz_full, katakana_quiz_full  # Mengimpor quiz Hiragana
from quiz.quiz_kanji_n5 import kanji_n5_quiz
from quiz.quiz_kanji_n4 import kanji_n4_quiz  # Mengimpor quiz Kanji N5
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
async def start_quiz_group(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_type=None):
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
            "start_time": time.time(),  # Waktu mulai kuis
            "user_scores": {}  # Poin pengguna
        }

    # Tentukan soal berdasarkan pilihan jenis kuis
    if quiz_type == 'hiragana_basic':
        user_quiz_data[chat_id]["quiz_questions"] = hiragana_quiz.copy()  # Gunakan hiragana_quiz untuk Basic
    elif quiz_type == 'hiragana_all':
        user_quiz_data[chat_id]["quiz_questions"] = hiragana_quiz_full.copy()  # Gunakan hiragana_quiz_full untuk All
    elif quiz_type == 'katakana_basic':
        user_quiz_data[chat_id]["quiz_questions"] = katakana_quiz.copy()  # Gunakan katakana_quiz untuk Basic
    elif quiz_type == 'katakana_all':
        user_quiz_data[chat_id]["quiz_questions"] = katakana_quiz_full.copy()  # Gunakan katakana_quiz_full untuk All
    elif quiz_type == 'kanji_n5':
        user_quiz_data[chat_id]["quiz_questions"] = kanji_n5_quiz.copy()  # Gunakan kanji_n5_quiz untuk Kanji N5
    elif quiz_type == 'kanji_n4':
        user_quiz_data[chat_id]["quiz_questions"] = kanji_n4_quiz.copy()  # Gunakan kanji_n4_quiz untuk Kanji N4

    random.shuffle(user_quiz_data[chat_id]["quiz_questions"])  # Mengacak soal
    user_quiz_data[chat_id]["total_quiz"] = len(user_quiz_data[chat_id]["quiz_questions"])  # Simpan total soal

    # Pastikan soal tersedia
    if len(user_quiz_data[chat_id]["quiz_questions"]) == 0:
        await update.callback_query.edit_message_text("Tidak ada soal yang tersedia untuk kuis ini.")
        return ConversationHandler.END

    question = user_quiz_data[chat_id]["quiz_questions"][0]["question"]  # Soal pertama
    logger.info(f"Question to ask: {question}")
    
    await update.callback_query.edit_message_text(f"Permainan akan segera dimulai!")
    logger.info("Question start.")

    await context.bot.send_message(chat_id=chat_id, text=f"{question}\nSilakan jawab:")
    logger.info("Question sent to user.")

    # Mengirimkan pesan pemberitahuan sebelum kuis dimulai
    await context.bot.send_message(chat_id=chat_id, text="Pastikan setiap jawaban kamu diakhiri dengan tanda baca titik (.)\n\nContoh: 'ma.'")
    logger.info("Quiz notification sent to user.")
    
    return QUIZ

async def check_answer_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Pastikan update berisi pesan dan bukan callback
    if update.message is None:
        return  # Tidak ada pesan, jadi hentikan eksekusi
    
    user_answer = update.message.text.strip().lower()
    chat_id = update.message.chat.id  # Ambil chat_id dari message untuk perhitungan percakapan

    # Pastikan pesan datang dari grup
    if update.effective_chat.type != 'supergroup':
        logger.warning(f"Received message from non-supergroup chat: {update.effective_chat.id}")
        return  # Jika bukan grup, tidak diproses lebih lanjut
    
    if chat_id not in user_quiz_data:
        return  # Jika data kuis tidak ditemukan, tidak diproses lebih lanjut

    # Ambil username pengguna, pastikan callback_query ada
    if update.callback_query:
        user_name = update.callback_query.from_user.username  # Ambil username pengguna dari callback
    else:
        user_name = update.message.from_user.username  # Ambil username dari message

    # Mendapatkan jawaban yang benar, membagi berdasarkan koma
    correct_answers = user_quiz_data[chat_id]["quiz_questions"][0]["answer"].lower().split(",")  # Memisahkan jawaban yang benar

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
        
        # Menambahkan 2 poin untuk jawaban benar
        if user_name not in user_quiz_data[chat_id]["user_scores"]:
            user_quiz_data[chat_id]["user_scores"][user_name] = 0
        user_quiz_data[chat_id]["user_scores"][user_name] += 2

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

        # Hapus soal yang sudah ditanyakan
        user_quiz_data[chat_id]["quiz_questions"].pop(0)

        # Lanjutkan soal berikutnya atau selesai
        if user_quiz_data[chat_id]["quiz_questions"]:
            next_question = user_quiz_data[chat_id]["quiz_questions"][0]["question"]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Soal berikutnya:\n{next_question}"
            )
            logger.info(f"Next question: {next_question}")
            return QUIZ
        else:
            # Kuis selesai, kirim rekap berdasarkan poin
            start_time = user_quiz_data[chat_id]["start_time"]
            time_taken = time.time() - start_time

            minutes = int(time_taken // 60)
            seconds = int(time_taken % 60)

            # Buat peringkat berdasarkan poin
            sorted_scores = sorted(user_quiz_data[chat_id]["user_scores"].items(), key=lambda x: x[1], reverse=True)
            ranking = "\n".join([f"{i+1}. {user} - {score} Poin" for i, (user, score) in enumerate(sorted_scores)])

            recap_message = f"🎉 Kuis selesai! Kerja bagus {user_name}.\n" \
                            f"🕒 Waktu yang dihabiskan: {minutes} menit {seconds} detik.\n\n" \
                            f"Peringkat Poin:\n{ranking}"

            # Kirim rekap ke grup log
            await send_log_to_group(recap_message, context)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{recap_message}"
            )

            # Reset data kuis
            del user_quiz_data[chat_id]
            logger.info("Quiz completed.")
            return ConversationHandler.END
    else:
        return  # Tidak ada respons atau tindakan lebih lanjut




    
# Fungsi untuk mengirim log ke grup Telegram
async def send_log_to_group(log_message: str, context: ContextTypes.DEFAULT_TYPE):
    group_chat_id = '-1002593183248'  # Ganti dengan chat_id grup Anda
    await context.bot.send_message(chat_id=group_chat_id, text=log_message)
