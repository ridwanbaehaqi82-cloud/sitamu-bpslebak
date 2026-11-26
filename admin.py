from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import Kunjungan, Stasiun, db
from datetime import date, datetime
import pytz
import csv
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_waktu_sekarang():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)

# ==========================================
# 1. BAGIAN DASHBOARD (DSB)
# ==========================================
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    hari_ini = date.today()
    
    # Ambil semua data kunjungan lalu filter khusus tanggal hari ini
    semua_kunjungan = Kunjungan.query.all()
    kunjungan_hari_ini = [k for k in semua_kunjungan if k.waktu_datang.date() == hari_ini]
    
    # Hitung angka untuk kartu ringkasan
    total_hari_ini = len(kunjungan_hari_ini)
    sedang_berkunjung = len([k for k in kunjungan_hari_ini if k.status == 'AKTIF'])
    selesai = len([k for k in kunjungan_hari_ini if k.status == 'SELESAI'])
    menunggu = len([k for k in kunjungan_hari_ini if k.status == 'MENUNGGU'])
    
    # Urutkan tamu dari yang terbaru masuk ke yang paling lama
    kunjungan_hari_ini.sort(key=lambda x: x.waktu_datang, reverse=True)
    
    return render_template('admin/dashboard.html', 
                           total=total_hari_ini, 
                           aktif=sedang_berkunjung, 
                           selesai=selesai, 
                           menunggu=menunggu,
                           buku_tamu=kunjungan_hari_ini)


# ==========================================
# 2. BAGIAN BUKU TAMU (BKT)
# ==========================================
@admin_bp.route('/buku-tamu')
@login_required
def buku_tamu():
    # Mengambil parameter penyaring dari URL (pencarian, tanggal, status)
    kata_kunci = request.args.get('cari', '').lower()
    tanggal_filter = request.args.get('tanggal', date.today().strftime('%Y-%m-%d'))
    status_filter = request.args.get('status', 'Semua Status')
    
    query = Kunjungan.query
    
    # Penyaring Berdasarkan Status
    if status_filter != 'Semua Status':
        query = query.filter_by(status=status_filter)
        
    semua_tamu = query.order_by(Kunjungan.waktu_datang.desc()).all()
    
    # Penyaring Berdasarkan Tanggal dan Pencarian Teks
    hasil_filter = []
    for tamu in semua_tamu:
        # Cek Tanggal
        if tamu.waktu_datang.strftime('%Y-%m-%d') != tanggal_filter:
            continue
            
        # Cek Pencarian (Nama, Instansi, atau Tujuan)
        if kata_kunci:
            nama_cocok = kata_kunci in tamu.nama_lengkap.lower()
            instansi_cocok = kata_kunci in tamu.instansi.lower()
            tujuan_cocok = kata_kunci in tamu.tujuan.lower()
            if not (nama_cocok or instansi_cocok or tujuan_cocok):
                continue
                
        hasil_filter.append(tamu)
        
    return render_template('admin/buku_tamu.html', 
                           daftar_tamu=hasil_filter, 
                           tanggal_aktif=tanggal_filter,
                           status_aktif=status_filter,
                           kata_kunci=kata_kunci)


# ==========================================
# 3. UBAH STATUS & HITUNG DURASI
# ==========================================
@admin_bp.route('/kunjungan/<int:id>/status', methods=['POST'])
@login_required
def ubah_status(id):
    kunjungan = Kunjungan.query.get_or_404(id)
    status_baru = request.form.get('status_baru')
    
    if status_baru == 'AKTIF':
        kunjungan.status = 'AKTIF'
        kunjungan.waktu_mulai = get_waktu_sekarang()
        kunjungan.diubah_oleh = current_user.id
        
    elif status_baru == 'SELESAI':
        kunjungan.status = 'SELESAI'
        kunjungan.waktu_selesai = get_waktu_sekarang()
        kunjungan.diubah_oleh = current_user.id
        
        # Perhitungan lama kunjungan (durasi dalam menit)
        waktu_awal = kunjungan.waktu_mulai if kunjungan.waktu_mulai else kunjungan.waktu_datang
        selisih = kunjungan.waktu_selesai - waktu_awal
        kunjungan.durasi_menit = int(selisih.total_seconds() / 60)
        
    db.session.commit()
    flash(f'Status kunjungan {kunjungan.nama_lengkap} berhasil diubah menjadi {status_baru}.', 'sukses')
    
    # Kembali ke halaman sebelumnya
    return redirect(request.referrer or url_for('admin.buku_tamu'))


# ==========================================
# 4. UNDUH DATA CSV
# ==========================================
@admin_bp.route('/ekspor')
@login_required
def ekspor_csv():
    # Menghasilkan file CSV dari kunjungan
    tanggal_filter = request.args.get('tanggal', date.today().strftime('%Y-%m-%d'))
    semua_tamu = Kunjungan.query.all()
    tamu_hari_ini = [k for k in semua_tamu if k.waktu_datang.strftime('%Y-%m-%d') == tanggal_filter]
    
    output = io.StringIO()
    writer = csv.writer(output)
    # Header Tabel
    writer.writerow(['Jam Datang', 'Nama Tamu', 'No. HP', 'Asal Instansi', 'Bertemu Siapa & Tujuan', 'Status', 'Durasi (Menit)'])
    
    for tamu in tamu_hari_ini:
        jam = tamu.waktu_datang.strftime('%H:%M WIB')
        durasi = f"{tamu.durasi_menit} Menit" if tamu.durasi_menit else "-"
        writer.writerow([jam, tamu.nama_lengkap, tamu.no_hp, tamu.instansi, tamu.tujuan, tamu.status, durasi])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=Buku_Tamu_{tanggal_filter}.csv"}
    )


# ==========================================
# 5. TAMBAH TAMU MANUAL OLEH ADMIN
# ==========================================
@admin_bp.route('/kunjungan/tambah', methods=['GET', 'POST'])
@login_required
def tambah_kunjungan():
    if request.method == 'POST':
        # Ambil stasiun resepsionis aktif (default id 1 jika belum diatur)
        stasiun_aktif = Stasiun.query.filter_by(aktif=True).first()
        stasiun_id = stasiun_aktif.id if stasiun_aktif else 1
        
        # Ambil isian yang dipisah
        bertemu_siapa = request.form.get('bertemu_siapa')
        tujuan_kunjungan = request.form.get('tujuan_kunjungan')
        tujuan_gabungan = f"{bertemu_siapa} - {tujuan_kunjungan}"
        
        kunjungan_baru = Kunjungan(
            stasiun_id=stasiun_id,
            nama_lengkap=request.form.get('nama_lengkap'),
            no_hp=request.form.get('no_hp'),
            instansi=request.form.get('instansi'),
            jabatan=request.form.get('jabatan'),
            tujuan=tujuan_gabungan,
            alamat=request.form.get('alamat'),
            status='MENUNGGU',
            sumber='PETUGAS', # Ditandai bahwa petugas yang menginput
            dicatat_oleh=current_user.id
        )
        db.session.add(kunjungan_baru)
        db.session.commit()
        
        flash('Data tamu baru berhasil ditambahkan secara manual.', 'sukses')
        return redirect(url_for('admin.buku_tamu'))
        
    return render_template('admin/tambah_tamu.html')
# ==========================================
# 6. EDIT & HAPUS DATA TAMU
# ==========================================
@admin_bp.route('/kunjungan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_kunjungan(id):
    kunjungan = Kunjungan.query.get_or_404(id)
    
    if request.method == 'POST':
        kunjungan.nama_lengkap = request.form.get('nama_lengkap')
        kunjungan.no_hp = request.form.get('no_hp')
        kunjungan.instansi = request.form.get('instansi')
        kunjungan.jabatan = request.form.get('jabatan')
        kunjungan.tujuan = request.form.get('tujuan')
        kunjungan.alamat = request.form.get('alamat')
        kunjungan.diubah_oleh = current_user.id
        
        db.session.commit()
        flash(f'Data tamu {kunjungan.nama_lengkap} berhasil diperbarui.', 'sukses')
        return redirect(url_for('admin.buku_tamu'))
        
    return render_template('admin/edit_tamu.html', tamu=kunjungan)

@admin_bp.route('/kunjungan/hapus/<int:id>', methods=['POST'])
@login_required
def hapus_kunjungan(id):
    kunjungan = Kunjungan.query.get_or_404(id)
    nama = kunjungan.nama_lengkap
    
    db.session.delete(kunjungan)
    db.session.commit()
    
    flash(f'Data tamu {nama} berhasil dihapus.', 'sukses')
    return redirect(request.referrer or url_for('admin.buku_tamu'))