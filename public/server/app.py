import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Muat variabel lingkungan dari .env
load_dotenv()

app = Flask(__name__, static_folder='../public', template_folder='../views')

# Konfigurasi Flask (Ganti dengan kunci rahasia yang kuat di produksi!)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'kunci_rahasia_default_yang_kuat')

# Konfigurasi Upload File
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
MAX_FILE_SIZE = 500 * 1024  # 500 KB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE * 4 # Batas ukuran request total

# Konfigurasi Flask-Mail dari .env
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# Fungsi Pembantu untuk Upload File
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Database Dummy (GANTI DENGAN DATABASE SESUNGGUHNYA SEPERTI PostgreSQL/MySQL) ---
# Data ini akan hilang setiap kali server restart.
# Gunakan database relasional untuk menyimpan data secara persisten.
DUMMY_DB = {
    'users': {
        'ortu1': {'password': 'pass123', 'santri_id': 'S001', 'email_ortu': 'dummy.ortu1@example.com'},
        'admin': {'password': 'adminpass', 'role': 'admin'}
    },
    'santri': {
        'S001': {
            'nama': 'Budi Santoso',
            'nilai_ulangan': [
                {'mata_pelajaran': 'Aqidah Akhlak', 'nilai': 75},
                {'mata_pelajaran': 'Fiqh', 'nilai': 80},
                {'mata_pelajaran': 'Hafalan Quran Juz 1', 'nilai': 60} # Contoh nilai tidak memenuhi
            ],
            'total_nilai_akumulasi': 215,
            'total_nilai_maksimal': 300,
            'nilai_lulus_pondok': 240, # Standar kelulusan pondok
            'info_pindah': 'Pengumuman: Mulai semester depan, Budi akan pindah ke kelas 8A.',
            'info_penerimaan_khusus': ['Diterima program tahfidz intensif.']
        }
    },
    'keuangan': {
        'S001': {
            'total_tagihan': 5000000, # Rp 5.000.000
            'sisa_tagihan': 2500000, # Rp 2.500.000 (sudah lunas setengah)
            'riwayat_pembayaran': [
                {'tanggal': '2025-01-15', 'jumlah': 2500000, 'keterangan': 'Pembayaran Tahap 1'}
            ]
        }
    },
    'seragam': {
        'S001': {
            'status': 'Sedang dalam pengiriman',
            'estimasi_tiba': '2025-07-10',
            'informasi_tambahan': 'Nomor resi: ABC12345'
        }
    },
    'pendaftaran_baru': [] # Untuk menyimpan data pendaftaran yang masuk
}

# --- Fungsi Pembantu Email ---
def send_email(to_email, subject, body):
    try:
        msg = Message(subject, recipients=[to_email])
        msg.body = body
        mail.send(msg)
        print(f"Email terkirim ke {to_email}")
        return True
    except Exception as e:
        print(f"Gagal mengirim email ke {to_email}: {e}")
        return False

# --- Rute Publik ---

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/jurusan.html')
def jurusan():
    return render_template('jurusan.html')

@app.route('/pendaftaran.html')
def pendaftaran_page():
    return render_template('pendaftaran.html')

@app.route('/alumni.html')
def alumni_page():
    # Di sini Anda bisa mengambil data alumni dari database jika ada
    # Untuk contoh ini, data alumni ada di frontend statis
    return render_template('alumni.html')

# API Pendaftaran Santri Baru
@app.route('/api/pendaftaran', methods=['POST'])
def submit_pendaftaran():
    try:
        nama_calon = request.form.get('namaCalon')
        alamat_calon = request.form.get('alamatCalon')
        umur_calon = request.form.get('umurCalon')
        nama_ortu = request.form.get('namaOrtu')
        email_ortu = request.form.get('emailOrtu')
        wa_ortu = request.form.get('waOrtu')

        # Validasi dasar kolom wajib
        if not all([nama_calon, alamat_calon, umur_calon, nama_ortu, email_ortu, wa_ortu]):
            return jsonify({'message': 'Semua kolom wajib diisi!'}), 400

        # Validasi Umur
        try:
            umur_calon = int(umur_calon)
            if not (6 <= umur_calon <= 25): # Contoh rentang umur
                return jsonify({'message': 'Umur calon santri harus antara 6 dan 25 tahun.'}), 400
        except ValueError:
            return jsonify({'message': 'Umur calon santri harus berupa angka.'}), 400

        uploaded_files_paths = {}
        for key in ['ktpOrtu', 'kk', 'dataCalon']:
            if key not in request.files:
                return jsonify({'message': f'File {key} tidak ditemukan dalam unggahan!'}), 400
            file = request.files[key]
            if file.filename == '':
                return jsonify({'message': f'File {key} belum diunggah!'}), 400

            if not allowed_file(file.filename):
                return jsonify({'message': f'Format file {file.filename} tidak diizinkan. Hanya JPG/JPEG.'}), 400

            # Cek ukuran file
            # Karena file.read() akan memindahkan kursor, kita simpan isinya dulu
            file_content = file.read()
            if len(file_content) > MAX_FILE_SIZE:
                return jsonify({'message': f'Ukuran file {file.filename} melebihi 500 KB!'}), 400

            filename = secure_filename(f"{key}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Pastikan direktori upload ada
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Simpan file yang sudah dibaca
            with open(filepath, 'wb') as f:
                f.write(file_content)

            uploaded_files_paths[key] = filepath

        # Simpan data pendaftaran ke "database" dummy
        new_registration = {
            'id': f"REG{len(DUMMY_DB['pendaftaran_baru']) + 1:04d}",
            'nama_calon': nama_calon,
            'alamat_calon': alamat_calon,
            'umur_calon': umur_calon,
            'nama_ortu': nama_ortu,
            'email_ortu': email_ortu,
            'wa_ortu': wa_ortu,
            'dokumen_ktp': uploaded_files_paths.get('ktpOrtu'),
            'dokumen_kk': uploaded_files_paths.get('kk'),
            'dokumen_data_calon': uploaded_files_paths.get('dataCalon'),
            'tanggal_daftar': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Menunggu Verifikasi'
        }
        DUMMY_DB['pendaftaran_baru'].append(new_registration)

        # Kirim email konfirmasi
        subject = "Konfirmasi Pendaftaran Santri Baru Pondok Pesantren Al-Babang"
        body = f"""Assalamu'alaikum wr. wb.,

Yth. Bapak/Ibu {nama_ortu},

Terima kasih atas pendaftaran putra/putri Anda, {nama_calon}, di Pondok Pesantren Al-Babang.
Pendaftaran Anda dengan ID: {new_registration['id']} telah kami terima pada tanggal {new_registration['tanggal_daftar']}.

Kami akan segera memproses pendaftaran ini. Informasi mengenai hasil kelulusan/penerimaan akan kami sampaikan kemudian melalui email ini atau nomor WhatsApp yang terdaftar.

Mohon bersabar menunggu informasi selanjutnya.

Jazakumullah Khairan Katsiran.

Hormat kami,
Panitia Penerimaan Santri Baru
Pondok Pesantren Al-Babang
"""
        send_email(email_ortu, subject, body)

        return jsonify({'message': 'Pendaftaran berhasil diterima.'}), 200

    except Exception as e:
        print(f"Error pada pendaftaran: {e}")
        return jsonify({'message': f'Terjadi kesalahan server: {str(e)}'}), 500

# --- Rute Portal Orang Tua (Membutuhkan Login) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = DUMMY_DB['users'].get(username)

        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            session['santri_id'] = user.get('santri_id')
            session['role'] = user.get('role', 'orang_tua') # Atur role untuk admin
            
            if session['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('portal_orang_tua'))
        else:
            return render_template('login.html', error='Nama pengguna atau kata sandi salah.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('santri_id', None)
    session.pop('role', None)
    return redirect(url_for('homepage'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def santri_data_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('santri_id'):
            return "Anda tidak memiliki data santri yang terkait dengan akun ini.", 403
        return f(*args, **kwargs)
    return decorated_function

# Fungsi helper untuk format rupiah di Jinja2
@app.template_filter('format_rupiah')
def format_rupiah_filter(amount):
    return f"{int(amount):,}".replace(",", ".")

@app.route('/portal')
@login_required
@santri_data_required
def portal_orang_tua():
    santri_id = session.get('santri_id')
    santri_data = DUMMY_DB['santri'].get(santri_id)
    standar_lulus_min = 70 # Contoh standar kelulusan per mata pelajaran

    if not santri_data:
        return "Data santri tidak ditemukan.", 404

    return render_template('portal_orang_tua.html', santri=santri_data, standar_lulus_min=standar_lulus_min)

@app.route('/portal/keuangan')
@login_required
@santri_data_required
def keuangan():
    santri_id = session.get('santri_id')
    santri_data = DUMMY_DB['santri'].get(santri_id)
    keuangan_data = DUMMY_DB['keuangan'].get(santri_id)

    if not santri_data or not keuangan_data:
        return "Data keuangan tidak ditemukan.", 404
    
    # Notifikasi email otomatis jika belum lunas total (contoh, bisa disesuaikan logikanya)
    # Ini idealnya dijalankan sebagai background task/cron job, bukan setiap kali halaman diakses.
    # Namun, untuk demonstrasi, kita letakkan di sini.
    if keuangan_data['sisa_tagihan'] > 0 and keuangan_data['sisa_tagihan'] == keuangan_data['total_tagihan']:
        ortu_email = DUMMY_DB['users'].get(session['username'], {}).get('email_ortu')
        if ortu_email:
            subject = f"Pengingat Pembayaran Pondok Pesantren Al-Babang untuk {santri_data['nama']}"
            body = f"""Assalamu'alaikum wr. wb.,

Yth. Bapak/Ibu,

Kami ingin mengingatkan bahwa pembayaran untuk santri {santri_data['nama']} masih belum lunas.
Total tagihan: Rp {format_rupiah_filter(keuangan_data['total_tagihan'])}
Sisa tagihan yang harus dilunasi: Rp {format_rupiah_filter(keuangan_data['sisa_tagihan'])}.

Mohon segera menyelesaikan pembayaran. Abaikan email ini jika Anda sudah melakukan pembayaran.

Jazakumullah Khairan Katsiran.

Hormat kami,
Administrasi Keuangan
Pondok Pesantren Al-Babang
"""
            send_email(ortu_email, subject, body)


    return render_template('keuangan.html', santri=santri_data, keuangan=keuangan_data)

@app.route('/portal/seragam')
@login_required
@santri_data_required
def pembelian_seragam():
    santri_id = session.get('santri_id')
    santri_data = DUMMY_DB['santri'].get(santri_id)
    seragam_data = DUMMY_DB['seragam'].get(santri_id)

    if not santri_data or not seragam_data:
        return "Data seragam tidak ditemukan.", 404

    return render_template('pembelian_seragam.html', santri=santri_data, seragam=seragam_data)

# --- Admin Panel (Membutuhkan Login Admin) ---
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            return "Akses Ditolak: Anda tidak memiliki hak akses administrator.", 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_panel():
    return render_template('admin_dashboard.html', 
                           pendaftaran_baru=DUMMY_DB['pendaftaran_baru'],
                           santri=DUMMY_DB['santri'])

# Rute contoh untuk admin (misalnya untuk melihat pendaftaran baru)
@app.route('/admin/pendaftaran-list')
@admin_required
def admin_pendaftaran_list():
    return jsonify(DUMMY_DB['pendaftaran_baru']) # Data pendaftaran baru

# Rute untuk mengupdate status pendaftaran (contoh sederhana)
@app.route('/admin/pendaftaran/<id>/status', methods=['POST'])
@admin_required
def update_pendaftaran_status(id):
    new_status = request.json.get('status')
    if not new_status:
        return jsonify({'message': 'Status baru diperlukan.'}), 400
    
    for reg in DUMMY_DB['pendaftaran_baru']:
        if reg['id'] == id:
            reg['status'] = new_status
            # Logika tambahan: Jika diterima, buat akun portal untuk ortu, tambahkan ke data santri, dll.
            return jsonify({'message': f'Status pendaftaran {id} berhasil diupdate menjadi {new_status}.'})
    return jsonify({'message': 'Pendaftaran tidak ditemukan.'}), 404


if __name__ == '__main__':
    # Pastikan folder uploads ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(debug=True, port=5000) # Jalankan di port 5000