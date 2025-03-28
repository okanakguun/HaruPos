from flask import Flask, render_template, request, jsonify, abort
import sqlite3
import os

app = Flask(__name__)

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect('adisyon.db')
    conn.row_factory = sqlite3.Row
    return conn

# Sabit lisans anahtarı
LICENSE_KEY = "KAFE123"  # Bunu kafeye özel yapabilirsin

# Lisans kontrol fonksiyonu
def check_license():
    # Şu an sabit, başka bir kontrol gerekirse burayı genişletebiliriz
    return True  # Her zaman geçerli, çünkü lisans kod içinde

# Ana sayfa
@app.route('/')
def index():
    if not check_license():
        abort(403, "Geçersiz lisans anahtarı! Lütfen satıcıyla iletişime geçin.")
    return render_template('index.html')

# Masaları listele
@app.route('/masalar')
def masalar():
    conn = get_db_connection()
    masalar = conn.execute('SELECT masa_id, masa_adi, durum FROM masalar').fetchall()
    conn.close()
    return jsonify([list(m) for m in masalar])

# Ürünleri listele
@app.route('/urunler')
def urunler():
    conn = get_db_connection()
    urunler = conn.execute('SELECT urun_id, urun_adi, fiyat FROM urunler').fetchall()
    conn.close()
    return jsonify([list(u) for u in urunler])

# Sipariş ekle
@app.route('/siparis_ekle', methods=['POST'])
def siparis_ekle():
    data = request.get_json()
    masa_id = data['masa_id']
    urunler = data['urunler']
    conn = get_db_connection()
    for urun in urunler:
        conn.execute('INSERT INTO siparisler (masa_id, urun_id, adet) VALUES (?, ?, ?)',
                     (masa_id, urun['urun_id'], urun['adet']))
    conn.execute('UPDATE masalar SET durum = "dolu" WHERE masa_id = ?', (masa_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Adisyon göster
@app.route('/adisyon/<int:masa_id>')
def adisyon(masa_id):
    conn = get_db_connection()
    detay = conn.execute('''
        SELECT m.masa_adi, u.urun_adi, s.adet, (s.adet * u.fiyat) as toplam, s.siparis_id
        FROM siparisler s
        JOIN masalar m ON s.masa_id = m.masa_id
        JOIN urunler u ON s.urun_id = u.urun_id
        WHERE s.masa_id = ?
    ''', (masa_id,)).fetchall()
    toplam = sum(row[3] for row in detay)
    conn.close()
    return jsonify({"detay": [list(d) for d in detay], "toplam": toplam})

# Ödeme kapat
@app.route('/odeme_kapat/<int:masa_id>', methods=['POST'])
def odeme_kapat(masa_id):
    conn = get_db_connection()
    toplam = conn.execute('SELECT SUM(s.adet * u.fiyat) FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id WHERE s.masa_id = ?', (masa_id,)).fetchone()[0]
    conn.execute('INSERT INTO odemeler (masa_id, tutar) VALUES (?, ?)', (masa_id, toplam))
    conn.execute('DELETE FROM siparisler WHERE masa_id = ?', (masa_id,))
    conn.execute('UPDATE masalar SET durum = "bos" WHERE masa_id = ?', (masa_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Ödeme geçmişi
@app.route('/odemeler')
def odemeler():
    conn = get_db_connection()
    odemeler = conn.execute('SELECT masa_id, tutar, tarih FROM odemeler').fetchall()
    conn.close()
    return jsonify([list(o) for o in odemeler])

# Yeni masa ekle
@app.route('/masa_ekle', methods=['POST'])
def masa_ekle():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO masalar (masa_adi, durum) VALUES (?, "bos")', (data['masa_adi'],))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Yeni ürün ekle
@app.route('/urun_ekle', methods=['POST'])
def urun_ekle():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO urunler (urun_adi, fiyat) VALUES (?, ?)', (data['urun_adi'], data['fiyat']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Sipariş sil
@app.route('/siparis_sil/<int:siparis_id>', methods=['POST'])
def siparis_sil(siparis_id):
    conn = get_db_connection()
    masa_id = conn.execute('SELECT masa_id FROM siparisler WHERE siparis_id = ?', (siparis_id,)).fetchone()[0]
    conn.execute('DELETE FROM siparisler WHERE siparis_id = ?', (siparis_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "masa_id": masa_id})

# Sipariş düzenle
@app.route('/siparis_duzenle/<int:siparis_id>', methods=['POST'])
def siparis_duzenle(siparis_id):
    data = request.get_json()
    conn = get_db_connection()
    masa_id = conn.execute('SELECT masa_id FROM siparisler WHERE siparis_id = ?', (siparis_id,)).fetchone()[0]
    conn.execute('UPDATE siparisler SET adet = ? WHERE siparis_id = ?', (data['adet'], siparis_id))
    conn.commit()
    conn.close()
    return jsonify({"masa_id": masa_id})

# Gelir raporu
@app.route('/gelir_raporu')
def gelir_raporu():
    conn = get_db_connection()
    gunluk_ozet = conn.execute('SELECT DATE(tarih), SUM(tutar) FROM odemeler GROUP BY DATE(tarih)').fetchall()
    toplam_gelir = conn.execute('SELECT SUM(tutar) FROM odemeler').fetchone()[0] or 0
    conn.close()
    return jsonify({"gunluk_ozet": [list(g) for g in gunluk_ozet], "toplam_gelir": toplam_gelir})

if __name__ == '__main__':
    # Veritabanı yoksa oluştur
    if not os.path.exists('adisyon.db'):
        conn = get_db_connection()
        conn.execute('CREATE TABLE masalar (masa_id INTEGER PRIMARY KEY, masa_adi TEXT, durum TEXT)')
        conn.execute('CREATE TABLE urunler (urun_id INTEGER PRIMARY KEY, urun_adi TEXT, fiyat REAL)')
        conn.execute('CREATE TABLE siparisler (siparis_id INTEGER PRIMARY KEY, masa_id INTEGER, urun_id INTEGER, adet INTEGER)')
        conn.execute('CREATE TABLE odemeler (odeme_id INTEGER PRIMARY KEY, masa_id INTEGER, tutar REAL, tarih DATETIME DEFAULT CURRENT_TIMESTAMP)')
        conn.commit()
        conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)  # Yerel ağda çalışsın