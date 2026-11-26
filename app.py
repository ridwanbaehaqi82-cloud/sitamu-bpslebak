from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from collections import defaultdict
from werkzeug.security import check_password_hash, generate_password_hash
import pytz
import os
import io
import pandas as pd

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_sitamu'

# Konfigurasi Database SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sitamu.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Zona Waktu Lokal (WIB)
tz = pytz.timezone('Asia/Jakarta')


def norm_dt(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(tz).replace(tzinfo=None)
        return dt
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day)
    if isinstance(dt, str) and dt.strip():
        teks = dt.strip()
        try:
            parsed = datetime.fromisoformat(teks)
            if parsed.tzinfo is not None:
                return parsed.astimezone(tz).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(teks[:26], fmt)
            except ValueError:
                continue
    return None


def parse_tanggal_aman(val):
    dt = norm_dt(val)
    if isinstance(dt, datetime):
        return dt.date()
    return None


def hitung_rentang_periode(periode_raw, tgl_mulai_str, tgl_selesai_str):
    periode = (periode_raw or 'bulan_ini').strip()
    today = datetime.now(tz).date()

    if periode == 'kustom' and tgl_mulai_str and tgl_selesai_str:
        try:
            start_date = datetime.strptime(tgl_mulai_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(tgl_selesai_str, '%Y-%m-%d').date()
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            jumlah_hari = max((end_date - start_date).days + 1, 1)
            return 'kustom', start_date, end_date, jumlah_hari, 'Rentang Tanggal Terpilih'
        except ValueError:
            pass

    if periode == '7_hari':
        end_date = today
        start_date = today - timedelta(days=6)
        return '7_hari', start_date, end_date, 7, '7 Hari Terakhir'

    if periode == 'tahun_ini':
        end_date = today
        start_date = date(today.year, 1, 1)
        jumlah_hari = max((end_date - start_date).days + 1, 1)
        return 'tahun_ini', start_date, end_date, jumlah_hari, 'Tahun Ini'

    if periode == 'semua':
        end_date = today
        semua_data = Kunjungan.query.all()
        tanggal_valid = [parse_tanggal_aman(k.waktu_datang) for k in semua_data]
        tanggal_valid = [t for t in tanggal_valid if t is not None]
        start_date = min(tanggal_valid) if tanggal_valid else today
        jumlah_hari = max((end_date - start_date).days + 1, 1)
        return 'semua', start_date, end_date, jumlah_hari, 'Semua Waktu'

    end_date = today
    start_date = today.replace(day=1)
    jumlah_hari = max((end_date - start_date).days + 1, 1)
    return 'bulan_ini', start_date, end_date, jumlah_hari, 'Bulan Ini'


# ==========================================
# 1. MODEL DATABASE
# ==========================================
class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username_email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Kunjungan(db.Model):
    __tablename__ = 'kunjungan'
    id = db.Column(db.Integer, primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    no_hp = db.Column(db.String(20), nullable=False)
    instansi = db.Column(db.String(100), nullable=False)
    jabatan = db.Column(db.String(100), nullable=True)
    bertemu_siapa = db.Column(db.String(100), nullable=False)
    tujuan_kunjungan = db.Column(db.Text, nullable=False)
    alamat = db.Column(db.Text, nullable=True)
    waktu_datang = db.Column(db.DateTime, default=lambda: datetime.now(tz))
    status = db.Column(db.String(30), default='MENUNGGU')
    durasi_menit = db.Column(db.Integer, nullable=True)


with app.app_context():
    db.create_all()


# ==========================================
# 2. RUTE HALAMAN TAMU (FRONTEND)
# ==========================================
@app.route('/')
def sambutan():
    return render_template('tamu/sambutan.html')


@app.route('/isi-form', methods=['GET', 'POST'])
def isi_form():
    if request.method == 'POST':
        tamu_baru = Kunjungan(
            nama_lengkap=request.form.get('nama_lengkap', 'Tanpa Nama'),
            no_hp=request.form.get('no_hp', '-'),
            instansi=request.form.get('instansi', '-'),
            jabatan=request.form.get('jabatan', '-'),
            bertemu_siapa=request.form.get('bertemu_siapa', '-'),
            tujuan_kunjungan=request.form.get('tujuan_kunjungan', '-'),
            alamat=request.form.get('alamat', '-')
        )
        db.session.add(tamu_baru)
        db.session.commit()
        return redirect(url_for('terima_kasih'))

    return render_template('tamu/form.html')


@app.route('/terima-kasih')
def terima_kasih():
    return render_template('tamu/selesai.html')


# ==========================================
# 3. RUTE PANEL ADMIN (BACKEND)
# ==========================================
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = Admin.query.filter_by(username_email=username).first()

        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau password salah. Silakan coba lagi.', 'login_error')

    return render_template('admin/login.html')


@app.route('/admin/lupa-sandi', methods=['POST'])
def lupa_sandi():
    username_email = request.form.get('reset_username', '').strip()
    password_baru = request.form.get('password_baru', '')
    konfirmasi_password = request.form.get('konfirmasi_password', '')

    if not username_email or not password_baru or not konfirmasi_password:
        flash('Lengkapi semua kolom reset kata sandi.', 'reset_error')
        return redirect(url_for('login'))

    if len(password_baru) < 6:
        flash('Kata sandi baru minimal 6 karakter.', 'reset_error')
        return redirect(url_for('login'))

    if password_baru != konfirmasi_password:
        flash('Konfirmasi kata sandi baru tidak cocok.', 'reset_error')
        return redirect(url_for('login'))

    admin = Admin.query.filter_by(username_email=username_email).first()
    if not admin:
        flash('Akun admin tidak ditemukan.', 'reset_error')
        return redirect(url_for('login'))

    admin.password_hash = generate_password_hash(password_baru)
    db.session.commit()
    flash('Kata sandi berhasil diperbarui. Silakan masuk dengan kata sandi baru.', 'reset_success')
    return redirect(url_for('login'))


@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    return render_template('admin/dashboard.html')


@app.route('/admin/buku-tamu')
def buku_tamu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    sekarang = datetime.now(tz)
    awal_hari = sekarang.replace(hour=0, minute=0, second=0, microsecond=0)
    akhir_hari = sekarang.replace(hour=23, minute=59, second=59, microsecond=999999)

    data_hari_ini = Kunjungan.query.filter(
        Kunjungan.waktu_datang >= awal_hari,
        Kunjungan.waktu_datang <= akhir_hari
    ).all()

    total_hari_ini = len(data_hari_ini)
    total_aktif = sum(1 for t in data_hari_ini if t.status in ['AKTIF', 'SEDANG BERKUNJUNG', 'Sedang Berkunjung'])
    total_selesai = sum(1 for t in data_hari_ini if t.status in ['SELESAI', 'Selesai'])

    page = request.args.get('page', 1, type=int)
    pagination = Kunjungan.query.order_by(Kunjungan.waktu_datang.desc()).paginate(page=page, per_page=10, error_out=False)

    daftar_tamu = pagination.items

    return render_template(
        'admin/buku_tamu.html',
        daftar_tamu=daftar_tamu,
        pagination=pagination,
        total_hari_ini=total_hari_ini,
        total_aktif=total_aktif,
        total_selesai=total_selesai
    )


@app.route('/admin/edit-tamu/<int:id>', methods=['GET', 'POST'])
@app.route('/admin/kunjungan/edit/<int:id>', methods=['GET', 'POST'])
def edit_tamu(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    tamu = Kunjungan.query.get_or_404(id)

    if request.method == 'POST':
        tamu.nama_lengkap = request.form.get('nama_lengkap', tamu.nama_lengkap)
        tamu.no_hp = request.form.get('no_hp', tamu.no_hp)
        tamu.instansi = request.form.get('instansi', tamu.instansi)
        tamu.jabatan = request.form.get('jabatan', tamu.jabatan)
        tamu.bertemu_siapa = request.form.get('bertemu_siapa', tamu.bertemu_siapa)
        tamu.tujuan_kunjungan = request.form.get('tujuan_kunjungan', tamu.tujuan_kunjungan)
        tamu.alamat = request.form.get('alamat', tamu.alamat)

        db.session.commit()
        flash('Data tamu berhasil diperbarui.', 'success')
        return redirect(url_for('buku_tamu'))

    return render_template('admin/edit_tamu.html', tamu=tamu)


@app.route('/admin/kunjungan/<int:id>/status', methods=['POST'])
def update_status(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    tamu = Kunjungan.query.get_or_404(id)
    status_baru = request.form.get('status_baru')

    if status_baru:
        tamu.status = status_baru
        db.session.commit()
        flash('Status tamu berhasil diperbarui.', 'success')

    return redirect(request.referrer or url_for('buku_tamu'))


@app.route('/admin/kunjungan/hapus/<int:id>', methods=['POST'])
def hapus_kunjungan(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    tamu = Kunjungan.query.get_or_404(id)
    db.session.delete(tamu)
    db.session.commit()
    flash('Data tamu berhasil dihapus.', 'success')
    return redirect(url_for('buku_tamu'))


@app.route('/admin/ekspor-excel')
def ekspor_excel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    periode_param = request.args.get('periode', '').strip()
    tgl_mulai_str = request.args.get('tgl_mulai', '').strip()
    tgl_selesai_str = request.args.get('tgl_selesai', '').strip()

    semua_kunjungan = Kunjungan.query.order_by(Kunjungan.waktu_datang.desc()).all()

    if periode_param:
        _, start_date, end_date, _, _ = hitung_rentang_periode(
            periode_param, tgl_mulai_str, tgl_selesai_str
        )
        kunjungan_list = []
        for k in semua_kunjungan:
            tgl_k = parse_tanggal_aman(k.waktu_datang)
            if tgl_k and start_date <= tgl_k <= end_date:
                kunjungan_list.append(k)
        label_file = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    elif tgl_mulai_str and tgl_selesai_str:
        _, start_date, end_date, _, _ = hitung_rentang_periode(
            'kustom', tgl_mulai_str, tgl_selesai_str
        )
        kunjungan_list = []
        for k in semua_kunjungan:
            tgl_k = parse_tanggal_aman(k.waktu_datang)
            if tgl_k and start_date <= tgl_k <= end_date:
                kunjungan_list.append(k)
        label_file = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    else:
        kunjungan_list = semua_kunjungan
        label_file = datetime.now(tz).strftime('%Y-%m-%d')

    kolom = [
        'Waktu Datang', 'Nama Tamu', 'No. Kontak', 'Instansi / Asal',
        'Jabatan', 'Bertemu Siapa', 'Tujuan Kunjungan', 'Alamat', 'Status'
    ]
    data = []
    for k in kunjungan_list:
        dt_lokal = norm_dt(k.waktu_datang)
        data.append({
            'Waktu Datang': dt_lokal.strftime('%Y-%m-%d %H:%M:%S') if isinstance(dt_lokal, datetime) else str(k.waktu_datang or ''),
            'Nama Tamu': k.nama_lengkap,
            'No. Kontak': k.no_hp,
            'Instansi / Asal': k.instansi,
            'Jabatan': k.jabatan if k.jabatan else '-',
            'Bertemu Siapa': k.bertemu_siapa,
            'Tujuan Kunjungan': k.tujuan_kunjungan,
            'Alamat': k.alamat if k.alamat else '-',
            'Status': k.status
        })

    df = pd.DataFrame(data, columns=kolom)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data Buku Tamu')
    output.seek(0)

    filename = f"Laporan_Buku_Tamu_{label_file}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@app.route('/admin/laporan')
def laporan():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    periode_raw = request.args.get('periode', 'bulan_ini')
    tgl_mulai_str = request.args.get('tgl_mulai', '')
    tgl_selesai_str = request.args.get('tgl_selesai', '')

    periode, start_date, end_date, jumlah_hari, label_periode = hitung_rentang_periode(
        periode_raw, tgl_mulai_str, tgl_selesai_str
    )

    kunjungan_periode = []
    counts_per_day = defaultdict(int)
    bulan_counts = [0] * 12

    semua_kunjungan = Kunjungan.query.order_by(Kunjungan.waktu_datang.desc()).all()
    for k in semua_kunjungan:
        tgl_k = parse_tanggal_aman(k.waktu_datang)
        if tgl_k and start_date <= tgl_k <= end_date:
            kunjungan_periode.append(k)
            counts_per_day[tgl_k.strftime('%Y-%m-%d')] += 1
            if tgl_k.year == end_date.year:
                bulan_counts[tgl_k.month - 1] += 1

    total_kunjungan = len(kunjungan_periode)
    rata_rata_hari = round(total_kunjungan / jumlah_hari, 1) if total_kunjungan > 0 else 0
    total_selesai = sum(1 for k in kunjungan_periode if k.status in ['SELESAI', 'Selesai'])

    chart_labels = []
    chart_values = []

    if periode == 'tahun_ini':
        bulan_nama = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        chart_labels = bulan_nama[:end_date.month]
        chart_values = bulan_counts[:end_date.month]
    else:
        cursor = start_date
        while cursor <= end_date:
            chart_labels.append(cursor.strftime('%d/%m'))
            chart_values.append(counts_per_day.get(cursor.strftime('%Y-%m-%d'), 0))
            cursor += timedelta(days=1)

    return render_template(
        'admin/laporan.html',
        periode=periode,
        label_periode=label_periode,
        start_date_str=start_date.strftime('%d %b %Y'),
        end_date_str=end_date.strftime('%d %b %Y'),
        tgl_mulai_val=start_date.strftime('%Y-%m-%d'),
        tgl_selesai_val=end_date.strftime('%Y-%m-%d'),
        total_kunjungan=total_kunjungan,
        rata_rata_hari=rata_rata_hari,
        total_selesai=total_selesai,
        chart_labels=chart_labels,
        chart_values=chart_values,
        daftar_laporan=kunjungan_periode
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)