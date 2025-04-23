import sqlite3
import logging
import os
from sqlite3 import Error

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Path ke database
DATABASE_PATH = "data/user_data.db"

# Pastikan direktori ada
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

def create_connection():
    """Membuat koneksi ke database SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        return conn
    except Error as e:
        logger.error(f"Error saat membuat koneksi database: {e}")
    
    return conn

def create_tables():
    """Membuat tabel jika belum ada."""
    
    # SQL untuk membuat tabel users
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        nama TEXT,
        exp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # SQL untuk membuat trigger untuk updated_at
    create_trigger = """
    CREATE TRIGGER IF NOT EXISTS update_user_timestamp 
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
    END;
    """
    
    # Buat koneksi dan tabel
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(create_users_table)
            cursor.execute(create_trigger)
            conn.commit()
            logger.info("Tabel users berhasil dibuat atau sudah ada.")
        except Error as e:
            logger.error(f"Error saat membuat tabel: {e}")
        finally:
            conn.close()
    else:
        logger.error("Error! Tidak dapat membuat koneksi database.")
        
def add_user(telegram_id, nama=None, username=None):
    """Menambahkan pengguna baru ke database."""
    sql = """
    INSERT INTO users (telegram_id, nama, username)
    VALUES (?, ?, ?)
    ON CONFLICT(telegram_id) 
    DO UPDATE SET 
        nama = EXCLUDED.nama,
        username = EXCLUDED.username;
    """
    
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (telegram_id, nama, username))
            conn.commit()
            logger.info(f"User dengan telegram_id {telegram_id} berhasil ditambahkan atau diperbarui.")
            return True
        except Error as e:
            logger.error(f"Error saat menambahkan/memperbarui user: {e}")
            return False
        finally:
            conn.close()
    return False

def get_user(telegram_id):
    """Mendapatkan data pengguna berdasarkan telegram_id."""
    sql = "SELECT * FROM users WHERE telegram_id = ?;"
    
    conn = create_connection()
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row  # Untuk mengakses kolom dengan nama
            cursor = conn.cursor()
            cursor.execute(sql, (telegram_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
        except Error as e:
            logger.error(f"Error saat mendapatkan user: {e}")
            return None
        finally:
            conn.close()
    return None

def update_exp(telegram_id, exp_gain):
    """Menambahkan exp dan level up jika diperlukan."""
    
    # Dapatkan user terlebih dahulu
    user = get_user(telegram_id)
    if not user:
        logger.error(f"User dengan telegram_id {telegram_id} tidak ditemukan.")
        return False
    
    current_exp = user['exp']
    current_level = user['level']
    
    # Rumus untuk level up (sederhana): level * 100 exp untuk naik level berikutnya
    exp_required_for_next_level = current_level * 100
    
    # Tambahkan exp
    new_exp = current_exp + exp_gain
    new_level = current_level
    
    # Cek level up
    while new_exp >= exp_required_for_next_level:
        new_exp -= exp_required_for_next_level
        new_level += 1
        exp_required_for_next_level = new_level * 100
    
    # Update data user
    sql = """
    UPDATE users
    SET exp = ?, level = ?
    WHERE telegram_id = ?;
    """
    
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (new_exp, new_level, telegram_id))
            conn.commit()
            logger.info(f"Exp user {telegram_id} diperbarui: +{exp_gain} exp")
            
            # Return data hasil update dan status level up
            return {
                'leveled_up': new_level > current_level,
                'old_level': current_level,
                'new_level': new_level,
                'exp_gain': exp_gain,
                'current_exp': new_exp,
                'exp_needed': new_level * 100
            }
        except Error as e:
            logger.error(f"Error saat update exp: {e}")
            return False
        finally:
            conn.close()
    return False

def get_top_users(limit=10):
    """Mendapatkan daftar pengguna dengan level tertinggi."""
    sql = """
    SELECT telegram_id, username, nama, exp, level
    FROM users
    ORDER BY level DESC, exp DESC
    LIMIT ?;
    """
    
    conn = create_connection()
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            users = cursor.fetchall()
            return [dict(user) for user in users]
        except Error as e:
            logger.error(f"Error saat mendapatkan top users: {e}")
            return []
        finally:
            conn.close()
    return []

# Inisialisasi database saat modul diimpor
create_tables()