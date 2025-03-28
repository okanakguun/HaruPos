from flask import Flask, render_template, request, jsonify, abort
import psycopg2
import os

app = Flask(__name__)

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL çevresel değişkeni tanımlı değil!")
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except psycopg2.Error as e:
        raise Exception(f"Veritabanı bağlantı hatası: {str(e)}")

# Sabit lisans anahtarı
LICENSE_KEY = "KAFE123"

def check_license():
    return True

@app.route('/')
def index():
    if not check_license():
        abort(403, "Geçersiz lisans anahtarı!")
    return render_template('index.html')

@app.route('/masalar')
def masalar():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id, masa_adi, durum FROM masalar')
    masalar = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(m) for m in masalar])

@app.route('/urunler')
def urunler():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT urun_id, urun_adi, fiyat FROM urunler')
    urunler = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(u) for u in urunler])

@app.route('/siparis_ekle', methods=['POST'])
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
def odeme_kapat(masa_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT SUM(s.adet * u.fiyat) FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id WHERE s.masa_id = %s', (masa_id,))
    toplam = cur.fetchone()[0] or 0
    cur.execute('INSERT INTO odemeler (masa_id, tutar) VALUES (%s, %s)', (masa_id, toplam))
    cur.execute('DELETE FROM siparisler WHERE masa_id = %s', (masa_id,))
    cur.execute('UPDATE masalar SET durum = %s WHERE masa_id = %s', ("bos", masa_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/odemeler')
def odemeler():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id, tutar, tarih FROM odemeler')
    odemeler = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([list(o) for o in odemeler])

@app.route('/masa_ekle', methods=['POST'])
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
def urun_ekle():
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO urunler (urun_adi, fiyat) VALUES (%s, %s)', (data['urun_adi'], data['fiyat']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/masa_sil/<int:masa_id>', methods=['POST'])
def masa_sil(masa_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # İlgili siparişleri sil
    cur.execute('DELETE FROM siparisler WHERE masa_id = %s', (masa_id,))
    # İlgili ödemeleri sil (isteğe bağlı, eğer istemiyorsan bu satırı kaldır)
    cur.execute('DELETE FROM odemeler WHERE masa_id = %s', (masa_id,))
    # Masayı sil
    cur.execute('DELETE FROM masalar WHERE masa_id = %s', (masa_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/urun_sil/<int:urun_id>', methods=['POST'])
def urun_sil(urun_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # İlgili siparişleri sil
    cur.execute('DELETE FROM siparisler WHERE urun_id = %s', (urun_id,))
    # Ürünü sil
    cur.execute('DELETE FROM urunler WHERE urun_id = %s', (urun_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/siparis_sil/<int:siparis_id>', methods=['POST'])
def siparis_sil(siparis_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT masa_id FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    masa_id = cur.fetchone()[0]
    cur.execute('DELETE FROM siparisler WHERE siparis_id = %s', (siparis_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "masa_id": masa_id})

@app.route('/siparis_duzenle/<int:siparis_id>', methods=['POST'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)