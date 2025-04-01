from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = Flask(__name__)

# PostgreSQL bağlantısı
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432)
    )
    return conn

# Masaları listeleme
@app.route('/masalar', methods=['GET'])
def masalar():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM masalar')
    masalar = cursor.fetchall()
    conn.close()
    return jsonify(masalar)

# Yeni masa ekleme
@app.route('/masa_ekle', methods=['POST'])
def masa_ekle():
    data = request.get_json()
    masa_adi = data.get('masa_adi')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO masalar (masa_adi, durum) VALUES (%s, %s)', (masa_adi, 'bos'))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Masa silme
@app.route('/masa_sil/<int:masa_id>', methods=['POST'])
def masa_sil(masa_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM masalar WHERE masa_id = %s', (masa_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Ürünleri listeleme
@app.route('/urunler', methods=['GET'])
def urunler():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM urunler')
    urunler = cursor.fetchall()
    conn.close()
    return jsonify(urunler)

# Yeni ürün ekleme
@app.route('/urun_ekle', methods=['POST'])
def urun_ekle():
    data = request.get_json()
    urun_adi = data.get('urun_adi')
    fiyat = data.get('fiyat')
    kategori_id = data.get('kategori_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO urunler (urun_adi, fiyat, kategori_id) VALUES (%s, %s, %s)', 
                   (urun_adi, fiyat, kategori_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Ürün düzenleme
@app.route('/urun_duzenle/<int:urun_id>', methods=['POST'])
def urun_duzenle(urun_id):
    data = request.get_json()
    urun_adi = data.get('urun_adi')
    fiyat = data.get('fiyat')
    kategori_id = data.get('kategori_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE urunler SET urun_adi = %s, fiyat = %s, kategori_id = %s WHERE urun_id = %s', 
                   (urun_adi, fiyat, kategori_id, urun_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Ürün güncellendi"})

# Ürün silme
@app.route('/urun_sil/<int:urun_id>', methods=['POST'])
def urun_sil(urun_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM urunler WHERE urun_id = %s', (urun_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Kategorileri listeleme
@app.route('/kategoriler', methods=['GET'])
def kategoriler():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM kategoriler')
    kategoriler = cursor.fetchall()
    conn.close()
    return jsonify(kategoriler)

# Yeni kategori ekleme
@app.route('/kategori_ekle', methods=['POST'])
def kategori_ekle():
    data = request.get_json()
    kategori_adi = data.get('kategori_adi')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO kategoriler (kategori_adi) VALUES (%s)', (kategori_adi,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Kategori silme
@app.route('/kategori_sil/<int:kategori_id>', methods=['POST'])
def kategori_sil(kategori_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE urunler SET kategori_id = NULL WHERE kategori_id = %s', (kategori_id,))
    cursor.execute('DELETE FROM kategoriler WHERE kategori_id = %s', (kategori_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Sipariş ekleme
@app.route('/siparis_ekle', methods=['POST'])
def siparis_ekle():
    data = request.get_json()
    masa_id = data.get('masa_id')
    urunler = data.get('urunler')
    conn = get_db_connection()
    cursor = conn.cursor()
    for urun in urunler:
        cursor.execute('INSERT INTO siparisler (masa_id, urun_id, adet) VALUES (%s, %s, %s)', 
                       (masa_id, urun['urun_id'], urun['adet']))
    cursor.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ('dolu', masa_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# Sipariş silme
@app.route('/siparis_sil/<int:siparis_id>', methods=['POST'])
def siparis_sil(siparis_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT masa_id FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    masa_id = cursor.fetchone()['masa_id']
    cursor.execute('DELETE FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    cursor.execute('SELECT COUNT(*) FROM siparisler WHERE masa_id = %s', (masa_id,))
    siparis_sayisi = cursor.fetchone()[0]
    if siparis_sayisi == 0:
        cursor.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ('bos', masa_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "masa_id": masa_id})

# Sipariş düzenleme
@app.route('/siparis_duzenle/<int:siparis_id>', methods=['POST'])
def siparis_duzenle(siparis_id):
    data = request.get_json()
    adet = data.get('adet')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE siparisler SET adet = %s WHERE siparis_id = %s', (adet, siparis_id))
    cursor.execute('SELECT masa_id FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    masa_id = cursor.fetchone()['masa_id']
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "masa_id": masa_id})

# Adisyon gösterme
@app.route('/adisyon/<int:masa_id>', methods=['GET'])
def adisyon(masa_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT m.masa_adi, u.urun_adi, s.adet, (s.adet * u.fiyat) as toplam, s.siparis_id
        FROM siparisler s
        JOIN masalar m ON s.masa_id = m.masa_id
        JOIN urunler u ON s.urun_id = u.urun_id
        WHERE s.masa_id = %s
    ''', (masa_id,))
    detay = cursor.fetchall()
    cursor.execute('SELECT SUM(s.adet * u.fiyat) FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id WHERE s.masa_id = %s', (masa_id,))
    toplam = cursor.fetchone()['sum'] or 0
    conn.close()
    return jsonify({"detay": detay, "toplam": toplam})

# Ödeme kapatma
@app.route('/odeme_kapat/<int:masa_id>', methods=['POST'])
def odeme_kapat(masa_id):
    data = request.get_json()
    odemeler = data.get('odemeler')
    odeme_turu = data.get('odeme_turu')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    toplam = 0
    for odeme in odemeler:
        siparis_id = odeme['siparis_id']
        adet = odeme['adet']
        cursor.execute('SELECT urun_id, adet FROM siparisler WHERE siparis_id = %s', (siparis_id,))
        siparis = cursor.fetchone()
        urun_id, mevcut_adet = siparis['urun_id'], siparis['adet']
        cursor.execute('SELECT fiyat FROM urunler WHERE urun_id = %s', (urun_id,))
        fiyat = cursor.fetchone()['fiyat']
        toplam += adet * fiyat
        if mevcut_adet <= adet:
            cursor.execute('DELETE FROM siparisler WHERE siparis_id = %s', (siparis_id,))
        else:
            cursor.execute('UPDATE siparisler SET adet = adet - %s WHERE siparis_id = %s', (adet, siparis_id))
    cursor.execute('SELECT COUNT(*) FROM siparisler WHERE masa_id = %s', (masa_id,))
    siparis_sayisi = cursor.fetchone()['count']
    if siparis_sayisi == 0:
        cursor.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ('bos', masa_id))
    cursor.execute('INSERT INTO odemeler (masa_id, tutar, odeme_tarihi, odeme_turu) VALUES (%s, %s, %s, %s)', 
                   (masa_id, toplam, datetime.now().isoformat(), odeme_turu))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "toplam": toplam})

# Ödeme geçmişini gösterme
@app.route('/odemeler', methods=['GET'])
def odemeler():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT m.masa_adi, o.tutar, o.odeme_tarihi, o.odeme_turu FROM odemeler o JOIN masalar m ON o.masa_id = m.masa_id')
    odemeler = cursor.fetchall()
    conn.close()
    return jsonify(odemeler)

# Gelir raporu
@app.route('/gelir_raporu', methods=['GET'])
def gelir_raporu():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT SUM(tutar) FROM odemeler')
    toplam_gelir = cursor.fetchone()['sum'] or 0
    cursor.execute('SELECT DATE(odeme_tarihi), SUM(tutar) FROM odemeler GROUP BY DATE(odeme_tarihi)')
    gunluk_ozet = cursor.fetchall()
    conn.close()
    return jsonify({"toplam_gelir": toplam_gelir, "gunluk_ozet": [[g['date'], g['sum']] for g in gunluk_ozet]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)