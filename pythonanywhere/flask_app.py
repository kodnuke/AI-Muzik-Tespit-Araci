"""
AI Muzik Tespit Araci - PythonAnywhere API (v2 - Robust)
=========================================================
Kurulum:
  1. Bu dosyayi /home/kodnuke/mysite/flask_app.py olarak yukleyin
  2. Console'da: pip3 install --user flask librosa numpy soundfile numba
  3. WSGI dosyasini duzenleyin
  4. Reload butonuna basin
"""

import os
import sys
import json
import tempfile
import traceback

# Encoding fix
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

from flask import Flask, request, jsonify, make_response

# Import analiz kutuphaneleri - hata olursa bilgi ver
IMPORT_HATALARI = []
try:
    import numpy as np
except Exception as e:
    IMPORT_HATALARI.append(f"numpy: {e}")

try:
    import librosa
except Exception as e:
    IMPORT_HATALARI.append(f"librosa: {e}")

app = Flask(__name__)

# OCR modulleri
import re
OCR_ENGINE = "none"
try:
    import ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
    OCR_ENGINE = "ddddocr"
except ImportError:
    pass


def goruntu_oku(dosya_yolu):
    if OCR_ENGINE == "ddddocr":
        with open(dosya_yolu, 'rb') as f:
            img_bytes = f.read()
        result = ocr.classification(img_bytes)
        return result
    return ""


def belge_analiz(text):
    sonuclar = []
    # TC Kimlik
    tc = {"belge_tipi": "TC Kimlik", "bulundu": False, "alanlar": {}}
    m = re.search(r'(?:TC|Kimlik)\s*(?:No)?\s*[:=]?\s*(\d{11})', text, re.IGNORECASE)
    if m and m.group(1)[0] != '0':
        tc["alanlar"]["tc_no"] = m.group(1)
        tc["bulundu"] = True
    m = re.search(r'(?:Ad|Adi)\s*[:=]?\s*([A-ZÇĞİÖŞÜ][a-zçğıöşü\s]+)', text, re.IGNORECASE)
    if m: tc["alanlar"]["ad_soyad"] = m.group(1).strip(); tc["bulundu"] = True
    if tc["bulundu"]: sonuclar.append(tc)
    # Ruhsat
    rs = {"belge_tipi": "Arac Ruhsati", "bulundu": False, "alanlar": {}}
    m = re.search(r'((?:\d{2}|[A-Z]{1,2})\s*\d{1,4}\s*[A-Z]{1,4})', text)
    if m: rs["alanlar"]["plaka"] = m.group(1).strip(); rs["bulundu"] = True
    m = re.search(r'(?:Marka)\s*[:=]?\s*([\w\s]+)', text, re.IGNORECASE)
    if m: rs["alanlar"]["marka"] = m.group(1).strip(); rs["bulundu"] = True
    if rs["bulundu"]: sonuclar.append(rs)
    # Fatura
    ft = {"belge_tipi": "Fatura", "bulundu": False, "alanlar": {}}
    m = re.search(r'(?:Fatura|FATURA)\s*No\s*[:=]?\s*(\S+)', text, re.IGNORECASE)
    if m: ft["alanlar"]["fatura_no"] = m.group(1); ft["bulundu"] = True
    m = re.search(r'([\d.,]+)\s*(?:TL|TRY)', text, re.IGNORECASE)
    if m: ft["alanlar"]["tutar"] = m.group(1); ft["bulundu"] = True
    if ft["bulundu"]: sonuclar.append(ft)
    # Adres
    ad = {"belge_tipi": "Adres", "bulundu": False, "alanlar": {}}
    m = re.search(r'(?:Il|IL)\s*[:=]?\s*(\w+)', text, re.IGNORECASE)
    if m: ad["alanlar"]["il"] = m.group(1); ad["bulundu"] = True
    m = re.search(r'(?:Ilce)\s*[:=]?\s*(\w[\w\s]+)', text, re.IGNORECASE)
    if m: ad["alanlar"]["ilce"] = m.group(1).strip(); ad["bulundu"] = True
    if ad["bulundu"]: sonuclar.append(ad)
    # Telefon
    gn = {"belge_tipi": "Genel", "bulundu": False, "alanlar": {}}
    m = re.search(r'(?:Tel|Telefon)\s*[:=]?\s*(0\d{10})', text, re.IGNORECASE)
    if m: gn["alanlar"]["telefon"] = m.group(1); gn["bulundu"] = True
    m = re.search(r'([\w.+-]+@[\w.-]+\.[\w]{2,})', text)
    if m: gn["alanlar"]["eposta"] = m.group(1); gn["bulundu"] = True
    if gn["bulundu"]: sonuclar.append(gn)
    toplam = sum(len(s.get("alanlar", {})) for s in sonuclar)
    return {"tespit_edilen_belgeler": sonuclar, "toplam_alan": toplam}


@app.before_request
def handle_cors():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        return response


@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

UPLOAD_DIR = os.path.join(os.path.expanduser('~'), 'mysite', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================================
# ANALIZ MOTORU
# ============================================================

def yuksek_frekans_analizi(y, sr):
    fft = np.fft.fft(y)
    freqs = np.fft.fftfreq(len(fft), 1 / sr)
    pos_mask = freqs > 0
    magnitudes = np.abs(fft[pos_mask])
    freqs_pos = freqs[pos_mask]
    
    yuksek_mask = freqs_pos > 16000
    orta_mask = (freqs_pos > 8000) & (freqs_pos <= 16000)
    
    yuksek_enerji = np.mean(magnitudes[yuksek_mask]) if np.any(yuksek_mask) else 0
    orta_enerji = np.mean(magnitudes[orta_mask]) if np.any(orta_mask) else 1
    oran = yuksek_enerji / (orta_enerji + 1e-10)
    
    if oran > 0.8: ai = 0.7
    elif oran < 0.05: ai = 0.6
    elif 0.1 < oran < 0.4: ai = 0.25
    else: ai = 0.4
    
    return {"isim": "Yuksek Frekans", "deger": round(float(oran), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"16kHz+/8-16kHz: {oran:.4f}", "agirlik": 1.5, "kategori": "Spektral"}

def spektral_analiz(y, sr):
    flatness = np.mean(librosa.feature.spectral_flatness(y=y)[0])
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])
    bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0])
    
    if flatness < 0.01: ai = 0.65
    elif flatness < 0.05: ai = 0.5
    elif flatness > 0.2: ai = 0.3
    else: ai = 0.4
    
    return {"isim": "Spektral Kalite", "deger": round(float(flatness), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"Flatness={flatness:.4f}, C={centroid:.0f}Hz", "agirlik": 2.0, "kategori": "Spektral"}

def ritim_analizi(y, sr):
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'): tempo = tempo[0]
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    if len(beat_times) < 3:
        return {"isim": "Ritim & Dynamics", "deger": 0.0, "ai_olasilik": 0.5,
                "aciklama": "Yeterli beat algılanamadi", "agirlik": 1.5, "kategori": "Ritimik"}
    
    cv = np.std(np.diff(beat_times)) / (np.mean(np.diff(beat_times)) + 1e-10)
    rms = librosa.feature.rms(y=y)[0]
    rms_cv = np.std(rms) / (np.mean(rms) + 1e-10)
    
    if cv < 0.02: ai = 0.75
    elif cv < 0.05: ai = 0.55
    elif cv > 0.15: ai = 0.2
    else: ai = 0.35
    
    if rms_cv < 0.3: ai = min(ai + 0.15, 0.9)
    
    return {"isim": "Ritim & Dynamics", "deger": round(float(cv), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"Tempo={tempo:.0f}BPM, CV={cv:.4f}", "agirlik": 1.5, "kategori": "Ritimik"}

def harmonik_analiz(y, sr):
    y_harm, _ = librosa.effects.hpss(y)
    harm_oran = np.sum(y_harm ** 2) / (np.sum(y ** 2) + 1e-10)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    mean_chroma = np.mean(chroma, axis=1) + 1e-10
    entropi = -np.sum(mean_chroma * np.log(mean_chroma))
    
    if harm_oran > 0.95: ai = 0.7
    elif harm_oran > 0.85: ai = 0.5
    elif harm_oran < 0.5: ai = 0.25
    else: ai = 0.4
    if entropi < 1.5: ai = min(ai + 0.15, 0.85)
    
    return {"isim": "Harmonik Yapi", "deger": round(float(harm_oran), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"Oran={harm_oran:.3f}, Entropi={entropi:.2f}", "agirlik": 1.5, "kategori": "Harmonik"}

def sureksizlik_analiz(y, sr):
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    degisim = np.mean(np.abs(np.diff(rms)))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y, frame_length=2048, hop_length=512)[0])
    
    if degisim < 0.005: ai = 0.7
    elif degisim < 0.01: ai = 0.55
    elif degisim > 0.05: ai = 0.2
    else: ai = 0.35
    
    return {"isim": "Sureksizlik", "deger": round(float(degisim), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"Enerji degisimi={degisim:.5f}", "agirlik": 1.0, "kategori": "Dinamik"}

def watermark_analiz(y, sr):
    fft = np.fft.fft(y)
    freqs = np.fft.fftfreq(len(fft), 1 / sr)
    wb = (np.abs(freqs) > 19000) & (np.abs(freqs) < 20000)
    w_enerji = np.sum(np.abs(fft[wb])) if np.any(wb) else 0
    toplam = np.sum(np.abs(fft))
    fft_mag = np.abs(fft[freqs > 0])
    
    pik_oran = 0
    if len(fft_mag) > 100:
        pik_oran = np.sum(fft_mag > np.mean(fft_mag) + 5 * np.std(fft_mag)) / len(fft_mag)
    
    w_oran = w_enerji / (toplam + 1e-10)
    
    if w_oran > 1e-4 and pik_oran > 0.01: ai = 0.85
    elif w_oran > 1e-5: ai = 0.55
    else: ai = 0.3
    
    return {"isim": "Watermark", "deger": round(float(w_oran), 8), "ai_olasilik": round(ai, 4),
            "aciklama": f"Orani={w_oran:.8f}", "agirlik": 1.5, "kategori": "Watermark"}

def mfcc_analiz(y, sr):
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    cv = np.std(mfccs, axis=1) / (np.abs(np.mean(mfccs, axis=1)) + 1e-10)
    ort_cv = np.mean(cv)
    
    if ort_cv < 0.3: ai = 0.7
    elif ort_cv < 0.5: ai = 0.5
    elif ort_cv > 1.5: ai = 0.2
    else: ai = 0.35
    
    return {"isim": "MFCC Tini", "deger": round(float(ort_cv), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"CV={ort_cv:.4f}", "agirlik": 1.0, "kategori": "Tini"}

def kontrast_analiz(y, sr):
    rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0])
    contrast_std = np.std(librosa.feature.spectral_contrast(y=y, sr=sr))
    
    if contrast_std < 2.0: ai = 0.65
    elif contrast_std < 5.0: ai = 0.45
    elif contrast_std > 15.0: ai = 0.2
    else: ai = 0.35
    
    return {"isim": "Spektral Kontrast", "deger": round(float(contrast_std), 6), "ai_olasilik": round(ai, 4),
            "aciklama": f"Rolloff={rolloff:.0f}Hz, STD={contrast_std:.2f}", "agirlik": 1.0, "kategori": "Spektral"}


def get_waveform_data(y, sr, sure):
    step = max(1, len(y) // 2000)
    sampled = y[::step]
    time_axis = np.linspace(0, sure, len(sampled))
    return {
        "time": [round(float(t), 4) for t in time_axis[:2000]],
        "amplitude": [round(float(a), 4) for a in sampled[:2000]]
    }

def get_spectrum_data(y, sr):
    fft = np.fft.fft(y)
    freqs = np.fft.fftfreq(len(fft), 1/sr)
    pos = freqs > 0
    freqs_pos = freqs[pos]
    mag = np.abs(fft[pos])
    
    max_f = min(12000, sr // 2)
    mask = freqs_pos <= max_f
    step = max(1, np.sum(mask) // 500)
    
    f_sampled = freqs_pos[mask][::step]
    m_sampled = mag[mask][::step]
    
    return {
        "frequency": [round(float(f), 1) for f in f_sampled],
        "magnitude": [round(float(m), 2) for m in m_sampled]
    }


# ============================================================
# API ENDPOINTLERI
# ============================================================

@app.route('/')
def index():
    if IMPORT_HATALARI:
        return jsonify({
            "service": "AI Muzik Tespit Araci API",
            "status": "ERROR - eksik paketler",
            "hatalar": IMPORT_HATALARI,
            "cozum": "pip3 install --user numpy librosa flask soundfile numba"
        }), 500
    
    return jsonify({
        "service": "AI Muzik Tespit Araci API",
        "version": "3.0",
        "endpoints": {
            "POST /api/analyze": "Muzik dosyasi analiz et",
            "POST /api/ocr": "OCR belge analizi"
        },
        "status": "ok"
    })

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 204
    if IMPORT_HATALARI:
        return jsonify({"error": "Eksik paketler: " + ", ".join(IMPORT_HATALARI)}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yuklenemedi"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400
    
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    file.save(filepath)
    
    try:
        y, sr = librosa.load(filepath, sr=22050)
        sure = float(librosa.get_duration(y=y, sr=sr))
        
        fonks = [yuksek_frekans_analizi, spektral_analiz, ritim_analizi, harmonik_analiz,
                 sureksizlik_analiz, watermark_analiz, mfcc_analiz, kontrast_analiz]
        
        sonuclar = []
        for f in fonks:
            try:
                sonuclar.append(f(y, sr))
            except Exception as e:
                sonuclar.append({
                    "isim": f.__name__, "deger": 0, "ai_olasilik": 0.5,
                    "aciklama": f"Hata: {str(e)[:50]}", "agirlik": 1.0, "kategori": "Hata"
                })
        
        toplam_ag = sum(a["agirlik"] for a in sonuclar)
        genel_skor = sum(a["ai_olasilik"] * a["agirlik"] for a in sonuclar) / toplam_ag if toplam_ag else 0
        
        if genel_skor > 0.75: guven = "Yuksek"
        elif genel_skor > 0.55: guven = "Orta"
        elif genel_skor > 0.45: guven = "Belirsiz"
        else: guven = "Dusuk"
        
        waveform = get_waveform_data(y, sr, sure)
        spectrum = get_spectrum_data(y, sr)
        
        try: os.remove(filepath)
        except: pass
        
        return jsonify({
            "dosya_adi": file.filename,
            "sure": round(sure, 2),
            "sr": sr,
            "analizler": sonuclar,
            "genel_skor": round(genel_skor, 4),
            "ai_tahmini": genel_skor > 0.5,
            "guven": guven,
            "waveform": waveform,
            "spectrum": spectrum
        })
    
    except Exception as e:
        try: os.remove(filepath)
        except: pass
        return jsonify({"error": str(e), "trace": traceback.format_exc()[:500]}), 500


# ============================================================
# OCR ENDPOINT
# ============================================================

@app.route('/api/ocr', methods=['POST', 'OPTIONS'])
def ocr_analiz():
    if request.method == 'OPTIONS':
        return '', 204
    if OCR_ENGINE == 'none':
        return jsonify({"error": "OCR motoru yok. pip3 install --user pytesseract pillow"}), 500
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yuklenemedi"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp']:
        return jsonify({"error": f"Desteklenmeyen format: .{ext}"}), 400
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    file.save(filepath)
    try:
        ham_text = goruntu_oku(filepath)
        if not ham_text.strip():
            return jsonify({"error": "Metin okunamadi"}), 400
        analiz = belge_analiz(ham_text)
        try: os.remove(filepath)
        except: pass
        return jsonify({"dosya_adi": file.filename, "ocr_motoru": OCR_ENGINE, "ham_metin": ham_text, "analiz": analiz})
    except Exception as e:
        try: os.remove(filepath)
        except: pass
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Test modu - localhost:5000")
    app.run(debug=True, port=5000)
