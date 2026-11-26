from app import app, db, Admin
from werkzeug.security import generate_password_hash

with app.app_context():
    # 1. Hapus data admin yang lama (agar tidak dobel)
    Admin.query.delete()
    
    # 2. Tentukan Email dan Password baru Anda di sini
    email_baru = 'bpskabupatenlebak@gmail.com'
    password_baru = 'BpsLebak2026!'  
    
    # 3. Enkripsi password agar aman di database
    password_enkripsi = generate_password_hash(password_baru)
    
    # 4. Simpan ke database
    admin_baru = Admin(username_email=email_baru, password_hash=password_enkripsi)
    db.session.add(admin_baru)
    db.session.commit()
    
    print("========================================")
    print("✅ AKUN ADMIN BERHASIL DIPERBARUI!")
    print(f"Username / Email : {email_baru}")
    print(f"Password         : {password_baru}")
    print("========================================")