from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import pytz

db = SQLAlchemy()

def get_waktu_sekarang():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz)

class Admin(db.Model, UserMixin):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username_email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    peran = db.Column(db.String(50), nullable=False)
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    gagal_login = db.Column(db.Integer, default=0, nullable=False)
    terkunci_sampai = db.Column(db.DateTime, nullable=True)
    wajib_ganti_sandi = db.Column(db.Boolean, default=False, nullable=False)

class Stasiun(db.Model):
    __tablename__ = 'stasiun'
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(50), unique=True, nullable=False)
    nama_stasiun = db.Column(db.String(100), nullable=False)
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    kunjungan = db.relationship('Kunjungan', backref='stasiun', lazy=True)

class Kunjungan(db.Model):
    __tablename__ = 'kunjungan'
    id = db.Column(db.Integer, primary_key=True)
    stasiun_id = db.Column(db.Integer, db.ForeignKey('stasiun.id'), nullable=False)
    nama_lengkap = db.Column(db.String(150), nullable=False)
    no_hp = db.Column(db.String(20), nullable=False)
    instansi = db.Column(db.String(150), nullable=False)
    jabatan = db.Column(db.String(100), nullable=True)
    tujuan = db.Column(db.String(255), nullable=False)
    alamat = db.Column(db.Text, nullable=True)
    
    waktu_datang = db.Column(db.DateTime, default=get_waktu_sekarang, nullable=False)
    waktu_mulai = db.Column(db.DateTime, nullable=True)
    waktu_selesai = db.Column(db.DateTime, nullable=True)
    durasi_menit = db.Column(db.Integer, nullable=True)
    
    status = db.Column(db.String(20), default='MENUNGGU', nullable=False)
    sumber = db.Column(db.String(20), nullable=False) 
    
    dicatat_oleh = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    diubah_oleh = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)

class Pengaturan(db.Model):
    __tablename__ = 'pengaturan'
    kunci = db.Column(db.String(50), primary_key=True)
    nilai = db.Column(db.Text, nullable=False)