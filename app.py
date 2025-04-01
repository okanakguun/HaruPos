from flask import Flask, render_template, request, jsonify, abort, session, redirect, url_for
import psycopg2
import os
import bcrypt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cok-gizli-bir-anahtar')  # Render'da SECRET_KEY tanımla

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL çevresel değişkeni tanımlı değil!")
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Veritabanı bağlantı hatası: {str(e)}")

LICENSE_KEY = "KAFE123"

def check_license():
    return True

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        kullanici_adi = data.get('kullanici_adi')
        sifre = data.get('sifre')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT kullanici_id, sifre FROM kullanicilar WHERE kullanici_adi = %s', (kullanici_adi,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.checkpw(sifre.encode('utf-8'), user[1].encode('utf-8')):
            session['user_id'] = user[0]
            return jsonify({"status": "success", "message": "Giriş başarılı!"})
        else:
            return jsonify({"status": "error", "message": "Kullanıcı adı veya şifre yanlış!"}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if not check_license():
        abort(403, "Geçersiz lisans anahtarı!")
    return render_template('index.html')

@app.route('/masalar')
@login_required
def masalar():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id, masa_adi, durum FROM masalar ORDER BY masa_id')
    masalar = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(m) for m in masalar])

@app.route('/urunler')
@login_required
def urunler():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT urun_id, urun_adi, fiyat, kategori_id FROM urunler ORDER BY urun_id')
    urunler = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(u) for u in urunler])

@app.route('/kategoriler')
@login_required
def kategoriler():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT kategori_id, kategori_adi FROM kategoriler ORDER BY kategori_id')
    kategoriler = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(k) for k in kategoriler])

@app.route('/siparis_ekle', methods=['POST'])
@login_required
def siparis_ekle():
    data = request.get_json()
    masa_id = data['masa_id']
    urunler = data['urunler']
    conn = get_db_connection()
    cur = conn.cursor()
    for urun in urunler:
        cur.execute('INSERT INTO siparisler (masa_id, urun_id, adet) VALUES (%s, %s, %s)',
                    (masa_id, urun['urun_id'], urun['adet']))
    cur.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ("dolu", masa_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/adisyon/<int:masa_id>')
@login_required
def adisyon(masa_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT m.masa_adi, u.urun_adi, s.adet, (s.adet * u.fiyat) as toplam, s.siparis_id
        FROM siparisler s
        JOIN masalar m ON s.masa_id = m.masa_id
        JOIN urunler u ON s.urun_id = u.urun_id
        WHERE s.masa_id = %s
    ''', (masa_id,))
    detay = cur.fetchall()
    toplam = sum(row[3] for row in detay)
    cur.close()
    conn.close()
    return jsonify({"detay": [list(d) for d in detay], "toplam": toplam})

@app.route('/odeme_kapat/<int:masa_id>', methods=['POST'])
@login_required
def odeme_kapat(masa_id):
    data = request.get_json()
    odemeler = data.get('odemeler', [])
    odeme_turu = data.get('odeme_turu', 'nakit')
    conn = get_db_connection()
    cur = conn.cursor()
    
    toplam = 0
    for odeme in odemeler:
        siparis_id = odeme['siparis_id']
        odenen_adet = int(odeme['adet'])
        
        cur.execute('''
            SELECT s.adet, u.fiyat 
            FROM siparisler s 
            JOIN urunler u ON s.urun_id = u.urun_id 
            WHERE s.siparis_id = %s
        ''', (siparis_id,))
        siparis = cur.fetchone()
        if not siparis or odenen_adet > siparis[0]:
            conn.close()
            return jsonify({"status": "error", "message": f"Sipariş {siparis_id} için geçersiz adet"}), 400
        
        tutar = odenen_adet * siparis[1]
        toplam += tutar
        
        cur.execute('INSERT INTO odemeler (masa_id, tutar, odeme_turu) VALUES (%s, %s, %s)',
                    (masa_id, tutar, odeme_turu))
        
        kalan_adet = siparis[0] - odenen_adet
        if kalan_adet > 0:
            cur.execute('UPDATE siparisler SET adet = %s WHERE siparis_id = %s',
                        (kalan_adet, siparis_id))
        else:
            cur.execute('DELETE FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    
    cur.execute('SELECT COUNT(*) FROM siparisler WHERE masa_id = %s', (masa_id,))
    kalan_siparis = cur.fetchone()[0]
    if kalan_siparis == 0:
        cur.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ("bos", masa_id))
    else:
        cur.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ("dolu", masa_id))
    
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "toplam": toplam})

@app.route('/odemeler')
@login_required
def odemeler():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id, tutar, tarih, odeme_turu FROM odemeler')
    odemeler = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(o) for o in odemeler])

@app.route('/masa_ekle', methods=['POST'])
@login_required
def masa_ekle():
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO masalar (masa_adi, durum) VALUES (%s, %s)', (data['masa_adi'], "bos"))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/urun_ekle', methods=['POST'])
@login_required
def urun_ekle():
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO urunler (urun_adi, fiyat, kategori_id) VALUES (%s, %s, %s)',
                (data['urun_adi'], data['fiyat'], data['kategori_id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/kategori_ekle', methods=['POST'])
@login_required
def kategori_ekle():
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO kategoriler (kategori_adi) VALUES (%s)', (data['kategori_adi'],))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/masa_sil/<int:masa_id>', methods=['POST'])
@login_required
def masa_sil(masa_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM siparisler WHERE masa_id = %s', (masa_id,))
    cur.execute('DELETE FROM odemeler WHERE masa_id = %s', (masa_id,))
    cur.execute('DELETE FROM masalar WHERE masa_id = %s', (masa_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/urun_sil/<int:urun_id>', methods=['POST'])
@login_required
def urun_sil(urun_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM siparisler WHERE urun_id = %s', (urun_id,))
    cur.execute('DELETE FROM urunler WHERE urun_id = %s', (urun_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/kategori_sil/<int:kategori_id>', methods=['POST'])
@login_required
def kategori_sil(kategori_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE urunler SET kategori_id = NULL WHERE kategori_id = %s', (kategori_id,))
    cur.execute('DELETE FROM kategoriler WHERE kategori_id = %s', (kategori_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/siparis_sil/<int:siparis_id>', methods=['POST'])
@login_required
def siparis_sil(siparis_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    masa_id = cur.fetchone()[0]
    cur.execute('DELETE FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    cur.execute('SELECT COUNT(*) FROM siparisler WHERE masa_id = %s', (masa_id,))
    kalan_siparis = cur.fetchone()[0]
    if kalan_siparis == 0:
        cur.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ("bos", masa_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "masa_id": masa_id})

@app.route('/siparis_duzenle/<int:siparis_id>', methods=['POST'])
@login_required
def siparis_duzenle(siparis_id):
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    masa_id = cur.fetchone()[0]
    cur.execute('UPDATE siparisler SET adet = %s WHERE siparis_id = %s', (data['adet'], siparis_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"masa_id": masa_id})

@app.route('/gelir_raporu')
@login_required
def gelir_raporu():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DATE(tarih), SUM(tutar) FROM odemeler GROUP BY DATE(tarih)')
    gunluk_ozet = cur.fetchall()
    cur.execute('SELECT SUM(tutar) FROM odemeler')
    toplam_gelir = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return jsonify({"gunluk_ozet": [list(g) for g in gunluk_ozet], "toplam_gelir": toplam_gelir})

@app.route('/urun_duzenle/<int:urun_id>', methods=['POST'])
@login_required
def urun_duzenle(urun_id):
    data = request.get_json()
    urun_adi = data.get('urun_adi')
    fiyat = data.get('fiyat')
    kategori_id = data.get('kategori_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE urunler SET urun_adi = %s, fiyat = %s, kategori_id = %s WHERE urun_id = %s',
                (urun_adi, fiyat, kategori_id, urun_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "message": "Ürün güncellendi"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)