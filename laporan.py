from flask import Blueprint, render_template, request
from flask_login import login_required
from models import Kunjungan, db
from datetime import datetime, date, timedelta
from collections import Counter

laporan_bp = Blueprint('laporan', __name__, url_prefix='/admin')

@laporan_bp.route('/laporan')
@login_required
def halaman_laporan():
    # LAP-01: Filter rentang tanggal (Bawaan: awal bulan sampai hari ini)
    hari_ini = date.today()
    awal_bulan = hari_ini.replace(day=1)
    
    tgl_mulai_str = request.args.get('mulai', awal_bulan.strftime('%Y-%m-%d'))
    tgl_akhir_str = request.args.get('akhir', hari_ini.strftime('%Y-%m-%d'))
    
    tgl_mulai = datetime.strptime(tgl_mulai_str, '%Y-%m-%d').date()
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d').date()
    
    # Ambil data dalam rentang tanggal
    semua_kunjungan = Kunjungan.query.all()
    data_rentang = [k for k in semua_kunjungan if tgl_mulai <= k.waktu_datang.date() <= tgl_akhir]
    
    # LAP-02: Total Kunjungan
    total_kunjungan = len(data_rentang)
    
    # LAP-03: Rata-rata Tamu per Hari
    selisih_hari = (tgl_akhir - tgl_mulai).days + 1
    rata_per_hari = round(total_kunjungan / selisih_hari, 1) if selisih_hari > 0 else 0
    
    # LAP-04 & LAP-05: Kunjungan Selesai & Rata-rata Durasi
    data_selesai = [k for k in data_rentang if k.status == 'SELESAI']
    total_selesai = len(data_selesai)
    persen_selesai = round((total_selesai / total_kunjungan * 100), 1) if total_kunjungan > 0 else 0
    
    total_durasi = sum(k.durasi_menit for k in data_selesai if k.durasi_menit is not None)
    rata_durasi = round(total_durasi / total_selesai) if total_selesai > 0 else 0
    
    # LAP-08: Instansi Asal Terbanyak (Top 5)
    list_instansi = [k.instansi.upper().strip() for k in data_rentang]
    top_instansi = Counter(list_instansi).most_common(5)
    
    # Format data top instansi untuk HTML
    instansi_terbanyak = []
    for inst, jumlah in top_instansi:
        persen = round((jumlah / total_kunjungan * 100), 1) if total_kunjungan > 0 else 0
        instansi_terbanyak.append({'nama': inst, 'jumlah': jumlah, 'persen': persen})
    
    # LAP-09: Tabel Rincian
    data_rentang.sort(key=lambda x: x.waktu_datang, reverse=True)
    
    return render_template('admin/laporan.html',
                           tgl_mulai=tgl_mulai_str,
                           tgl_akhir=tgl_akhir_str,
                           total_kunjungan=total_kunjungan,
                           rata_per_hari=rata_per_hari,
                           rata_durasi=rata_durasi,
                           total_selesai=total_selesai,
                           persen_selesai=persen_selesai,
                           instansi_terbanyak=instansi_terbanyak,
                           tabel_rincian=data_rentang)