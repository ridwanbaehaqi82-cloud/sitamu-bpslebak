from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import Admin, Stasiun
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika petugas sudah login, langsung lempar ke dashboard
    if current_user.is_authenticated:
        return redirect('/admin/dashboard')
        
    # Ambil data meja resepsionis dari database untuk dropdown
    daftar_stasiun = Stasiun.query.filter_by(aktif=True).all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Cari data admin di database
        admin = Admin.query.filter_by(username_email=username).first()
        
        # Cek apakah admin ada dan kata sandinya cocok
        if admin and check_password_hash(admin.password_hash, password):
            if admin.aktif:
                login_user(admin)
                return redirect('/admin/dashboard')
            else:
                flash('Akun Anda dinonaktifkan. Hubungi Pengelola Sistem.', 'error')
        else:
            flash('Username atau kata sandi salah.', 'error')
            
    return render_template('admin/login.html', daftar_stasiun=daftar_stasiun)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))