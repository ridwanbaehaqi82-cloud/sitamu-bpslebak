import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Kunci rahasia untuk sesi dan keamanan form
    SECRET_KEY = 'rahasia-bps-lebak-2026'
    
    # Konfigurasi database SQLite (satu file)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'sitamu.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Zona waktu aplikasi
    TIMEZONE = 'Asia/Jakarta'