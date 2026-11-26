from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Kunjungan, Stasiun

tamu_bp = Blueprint('tamu', __name__)

@tamu_bp.route('/')
def sambutan():
    return render_template('tamu/sambutan.html')

@tamu_bp.route('/isi-form', methods=['GET', 'POST'])
def isi_form():
    stasiun_kode = request.args.get('stasiun', 'lobby-1') 
    
    if request.method == 'POST':
        stasiun = Stasiun.query.filter_by(kode=stasiun_kode).first()
        stasiun_id = stasiun.id if stasiun else 1
        
        # Ambil dua isian yang sudah dipisah
        bertemu_siapa = request.form.get('bertemu_siapa')
        tujuan_kunjungan = request.form.get('tujuan_kunjungan')
        
        # Gabungkan menjadi satu kalimat agar pas dengan database kita
        tujuan_gabungan = f"{bertemu_siapa} - {tujuan_kunjungan}"
        
        kunjungan_baru = Kunjungan(
            stasiun_id=stasiun_id,
            nama_lengkap=request.form.get('nama_lengkap'),
            no_hp=request.form.get('no_hp'),
            instansi=request.form.get('instansi'),
            jabatan=request.form.get('jabatan'),
            tujuan=tujuan_gabungan, # Simpan hasil gabungan ke database
            alamat=request.form.get('alamat'),
            sumber='MANDIRI'
        )
        db.session.add(kunjungan_baru)
        db.session.commit()
        
        return redirect(url_for('tamu.terima_kasih'))
        
    return render_template('tamu/form.html', stasiun_kode=stasiun_kode)

@tamu_bp.route('/terima-kasih')
def terima_kasih():
    return render_template('tamu/selesai.html')