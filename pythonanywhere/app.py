"""
AI Muzik Tespit Araci - PythonAnywhere API
===========================================
Bu dosyayi PythonAnywhere'a yukleyin.

Kurulum:
  1. PythonAnywhere'da yeni bir Web App olusturun (Flask, Python 3.10+)
  2. Bu dosyayi /home/KULLANICI_ADINIZ/mysite/flask_app.py olarak yukleyin
  3. Asagidaki pip install komutlarini calistirin
  4. WSGI dosyasini duzenleyin (asagidaki talimatlara bakin)
"""

import os
import sys
import json
import tempfile

# Encoding fix
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import librosa

app = Flask(__name__)
CORS(app)  # Cross-origin izni (PHP sunucudan gelen istekler icin)

# Gecici klasor
UPLOAD_DIR = tempfile.mkdtemp()

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
    return jsonify({
        "service": "AI Muzik Tespit Araci API",
        "version": "3.0",
        "endpoints": {
            "POST /api/analyze": "Muzik dosyasi analiz et (multipart/form-data, field: file)"
        },
        "status": "ok"
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yuklenemedi"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400
    
    # Gecici dosyaya kaydet
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
                print(f"Hata: {f.__name__}: {e}")
        
        toplam_ag = sum(a["agirlik"] for a in sonuclar)
        genel_skor = sum(a["ai_olasilik"] * a["agirlik"] for a in sonuclar) / toplam_ag if toplam_ag else 0
        
        if genel_skor > 0.75: guven = "Yuksek"
        elif genel_skor > 0.55: guven = "Orta"
        elif genel_skor > 0.45: guven = "Belirsiz"
        else: guven = "Dusuk"
        
        waveform = get_waveform_data(y, sr, sure)
        spectrum = get_spectrum_data(y, sr)
        
        # Temizle
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
        return jsonify({"error": str(e)}), 500


# ============================================================
# ANA PROGRAM (test icin)
# ============================================================

if __name__ == '__main__':
    print("\n  AI Muzik Tespit API - Test Modu")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)
