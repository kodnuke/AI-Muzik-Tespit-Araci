"""
AI Muzik Tespit Araci - Web Versiyonu
======================================
Tarayici calistiran web tabanli analiz araci.

Kullanim:
    python app.py

Tarayicide acin:
    http://localhost:5000

Gerekli paketler:
    pip install flask librosa numpy soundfile
"""

import sys
import os
import json
import base64
import io
import threading

# Encoding fix
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

from flask import Flask, render_template_string, request, jsonify
import numpy as np
import librosa

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    
    if oran > 0.8: ai_olasilik = 0.7
    elif oran < 0.05: ai_olasilik = 0.6
    elif 0.1 < oran < 0.4: ai_olasilik = 0.25
    else: ai_olasilik = 0.4
    
    return {"isim": "Yuksek Frekans", "deger": round(float(oran), 6), "ai_olasilik": round(ai_olasilik, 4),
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

def analiz_calistir(y, sr):
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
    
    return {
        "analizler": sonuclar,
        "genel_skor": round(genel_skor, 4),
        "ai_tahmini": genel_skor > 0.5,
        "guven": guven
    }


# ============================================================
# WAVEFORM & SPECTRUM DATA (JSON icin)
# ============================================================

def get_waveform_data(y, sr, sure):
    # Her 200. ornegi al (performans icin)
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
    
    # 0-12kHz, her 50. frekans
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
# HTML TEMPLATE
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Muzik Tespit Araci</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0c0c1e 0%, #1a1a3e 50%, #0c0c1e 100%);
            color: #fff;
            min-height: 100vh;
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        /* Header */
        .header {
            text-align: center;
            padding: 40px 0 30px;
        }
        .header h1 {
            font-size: 2.8em;
            background: linear-gradient(135deg, #e94560, #533483, #74b9ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }
        .header p { color: #8892b0; font-size: 1.1em; }
        
        /* Upload Area */
        .upload-area {
            background: rgba(15, 52, 96, 0.4);
            border: 2px dashed #533483;
            border-radius: 16px;
            padding: 50px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }
        .upload-area:hover, .upload-area.dragover {
            border-color: #e94560;
            background: rgba(233, 69, 96, 0.1);
            transform: scale(1.01);
        }
        .upload-area .icon { font-size: 4em; margin-bottom: 15px; }
        .upload-area h3 { font-size: 1.3em; margin-bottom: 8px; color: #ccd6f6; }
        .upload-area p { color: #8892b0; font-size: 0.9em; }
        
        .file-input { display: none; }
        
        .file-info {
            background: rgba(83, 52, 131, 0.3);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: none;
            align-items: center;
            gap: 15px;
        }
        .file-info.show { display: flex; }
        .file-info .name { flex: 1; font-weight: 500; }
        .file-info .size { color: #8892b0; }
        
        /* Analyze Button */
        .btn-analyze {
            display: block;
            width: 100%;
            max-width: 400px;
            margin: 0 auto 30px;
            padding: 16px 32px;
            background: linear-gradient(135deg, #e94560, #533483);
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 1.2em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(233, 69, 96, 0.4); }
        .btn-analyze:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* Progress */
        .progress-container { display: none; text-align: center; padding: 30px; }
        .progress-container.show { display: block; }
        .spinner {
            width: 50px; height: 50px;
            border: 4px solid rgba(233, 69, 96, 0.2);
            border-top-color: #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* Results */
        .results { display: none; animation: fadeIn 0.5s ease; }
        .results.show { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Score Card */
        .score-card {
            background: rgba(15, 52, 96, 0.5);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
            margin-bottom: 30px;
            border: 1px solid rgba(233, 69, 96, 0.3);
        }
        .score-card.ai { border-color: #e94560; }
        .score-card.human { border-color: #00b894; }
        
        .score-emoji { font-size: 4em; margin-bottom: 10px; }
        .score-title { font-size: 1.8em; font-weight: 700; margin-bottom: 5px; }
        .score-title.ai { color: #e94560; }
        .score-title.human { color: #00b894; }
        .score-subtitle { color: #8892b0; margin-bottom: 15px; }
        
        .score-circle {
            width: 120px; height: 120px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            margin: 15px auto;
            font-size: 1.8em; font-weight: 700;
            position: relative;
        }
        .score-circle.ai { background: conic-gradient(#e94560 var(--pct), rgba(233,69,96,0.15) var(--pct)); }
        .score-circle.human { background: conic-gradient(#00b894 var(--pct), rgba(0,184,148,0.15) var(--pct)); }
        .score-circle::after {
            content: '';
            position: absolute;
            width: 90px; height: 90px;
            background: #0c0c1e;
            border-radius: 50%;
        }
        .score-circle span { position: relative; z-index: 1; }
        
        .guven-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            margin-top: 10px;
        }
        .guven-Yuksek { background: rgba(233, 69, 96, 0.3); color: #e94560; }
        .guven-Orta { background: rgba(253, 203, 110, 0.3); color: #fdcb6e; }
        .guven-Belirsiz { background: rgba(116, 185, 255, 0.3); color: #74b9ff; }
        .guven-Dusuk { background: rgba(0, 184, 148, 0.3); color: #00b894; }
        
        /* Grid */
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        
        .chart-card {
            background: rgba(15, 52, 96, 0.4);
            border-radius: 14px;
            padding: 20px;
            border: 1px solid rgba(83, 52, 131, 0.3);
        }
        .chart-card h3 { font-size: 1em; margin-bottom: 15px; color: #ccd6f6; }
        
        /* Analysis Table */
        .analysis-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
        }
        .analysis-table th {
            text-align: left;
            padding: 12px 16px;
            color: #8892b0;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .analysis-table td {
            padding: 14px 16px;
            background: rgba(15, 52, 96, 0.3);
        }
        .analysis-table tr td:first-child { border-radius: 10px 0 0 10px; }
        .analysis-table tr td:last-child { border-radius: 0 10px 10px 0; }
        
        .risk-badge {
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .risk-high { background: rgba(233, 69, 96, 0.2); color: #e94560; }
        .risk-mid { background: rgba(253, 203, 110, 0.2); color: #fdcb6e; }
        .risk-low { background: rgba(0, 184, 148, 0.2); color: #00b894; }
        
        .progress-bar-bg {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #5a6078;
            font-size: 0.85em;
        }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2em; }
            .upload-area { padding: 30px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI MUZIK TESPIT ARACI</h1>
            <p>Muzik dosyanizi yukleyin, AI mi insanim mi ogrenin</p>
        </div>
        
        <div class="upload-area" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <div class="icon">&#127925;</div>
            <h3>Dosyanizi surukleyip birakin veya tiklayarak secin</h3>
            <p>WAV, MP3, FLAC, OGG, M4A - Maksimum 50MB</p>
        </div>
        <input type="file" id="fileInput" class="file-input" accept=".wav,.mp3,.flac,.ogg,.m4a,.aiff">
        
        <div class="file-info" id="fileInfo">
            <span style="font-size:1.5em">&#127926;</span>
            <span class="name" id="fileName"></span>
            <span class="size" id="fileSize"></span>
        </div>
        
        <button class="btn-analyze" id="analyzeBtn" disabled onclick="analyze()">
            &#9654; ANALIZ ET
        </button>
        
        <div class="progress-container" id="progress">
            <div class="spinner"></div>
            <p>Analiz ediliyor... Lutfen bekleyin</p>
        </div>
        
        <div class="results" id="results">
            <!-- Score Card -->
            <div class="score-card" id="scoreCard">
                <div class="score-emoji" id="scoreEmoji"></div>
                <div class="score-title" id="scoreTitle"></div>
                <div class="score-subtitle" id="scoreSubtitle"></div>
                <div class="score-circle" id="scoreCircle" style="--pct: 0%">
                    <span id="scorePercent"></span>
                </div>
                <div class="guven-badge" id="guvenBadge"></div>
            </div>
            
            <!-- Charts -->
            <div class="grid">
                <div class="chart-card">
                    <h3>&#128200; DALGA SEKLI (Waveform)</h3>
                    <canvas id="waveformChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>&#128202; FREKANS SPEKTRUMU</h3>
                    <canvas id="spectrumChart"></canvas>
                </div>
            </div>
            
            <!-- Analysis Table -->
            <div class="chart-card">
                <h3>&#128269; ANALIZ DETAYLARI</h3>
                <table class="analysis-table">
                    <thead>
                        <tr>
                            <th>Analiz</th>
                            <th>Deger</th>
                            <th>AI Olasilik</th>
                            <th>Grafik</th>
                            <th>Aciklama</th>
                        </tr>
                    </thead>
                    <tbody id="analysisBody"></tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            AI Muzik Tespit Araci v3.0 Web | Istatistiksel analiz - kesin sonuc vermez
        </div>
    </div>
    
    <script>
        let selectedFile = null;
        let waveformChart = null;
        let spectrumChart = null;
        
        // Drag & Drop
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        
        ['dragenter', 'dragover'].forEach(e => {
            dropZone.addEventListener(e, (ev) => { ev.preventDefault(); dropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(e => {
            dropZone.addEventListener(e, (ev) => { ev.preventDefault(); dropZone.classList.remove('dragover'); });
        });
        dropZone.addEventListener('drop', (ev) => {
            const files = ev.dataTransfer.files;
            if (files.length) handleFile(files[0]);
        });
        
        fileInput.addEventListener('change', (ev) => {
            if (ev.target.files.length) handleFile(ev.target.files[0]);
        });
        
        function handleFile(file) {
            selectedFile = file;
            const ext = file.name.split('.').pop().toLowerCase();
            const allowed = ['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aiff', 'aif'];
            
            if (!allowed.includes(ext)) {
                alert('Desteklenmeyen dosya formati: .' + ext);
                return;
            }
            
            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = formatSize(file.size);
            document.getElementById('fileInfo').classList.add('show');
            document.getElementById('analyzeBtn').disabled = false;
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1048576).toFixed(1) + ' MB';
        }
        
        async function analyze() {
            if (!selectedFile) return;
            
            document.getElementById('analyzeBtn').disabled = true;
            document.getElementById('progress').classList.add('show');
            document.getElementById('results').classList.remove('show');
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            try {
                const resp = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await resp.json();
                
                if (data.error) {
                    alert('Hata: ' + data.error);
                    return;
                }
                
                displayResults(data);
            } catch (err) {
                alert('Analiz hatasi: ' + err.message);
            } finally {
                document.getElementById('progress').classList.remove('show');
                document.getElementById('analyzeBtn').disabled = false;
            }
        }
        
        function displayResults(data) {
            const isAi = data.ai_tahmini;
            const skor = (data.genel_skor * 100).toFixed(1);
            
            // Score Card
            const card = document.getElementById('scoreCard');
            card.className = 'score-card ' + (isAi ? 'ai' : 'human');
            
            document.getElementById('scoreEmoji').textContent = isAi ? '&#129302;' : '&#127925;';
            
            const title = document.getElementById('scoreTitle');
            title.textContent = isAi ? 'AI TARAFINDAN URETILMIS OLABILIR' : 'INSAN TARAFINDAN URETILMIS GORUNUYOR';
            title.className = 'score-title ' + (isAi ? 'ai' : 'human');
            
            document.getElementById('scoreSubtitle').textContent = `${data.dosya_adi} | ${data.sure}s | ${data.sr}Hz`;
            
            const circle = document.getElementById('scoreCircle');
            circle.style.setProperty('--pct', skor + '%');
            circle.className = 'score-circle ' + (isAi ? 'ai' : 'human');
            document.getElementById('scorePercent').textContent = '%' + skor;
            
            const badge = document.getElementById('guvenBadge');
            badge.textContent = 'Guven: ' + data.guven;
            badge.className = 'guven-badge guven-' + data.guven;
            
            // Waveform
            drawWaveform(data.waveform);
            drawSpectrum(data.spectrum);
            
            // Table
            const tbody = document.getElementById('analysisBody');
            tbody.innerHTML = '';
            
            data.analizler.forEach(a => {
                const pct = (a.ai_olasilik * 100).toFixed(0);
                let riskClass = 'risk-low';
                let riskText = 'Dusuk';
                if (a.ai_olasilik > 0.6) { riskClass = 'risk-high'; riskText = 'Yuksek'; }
                else if (a.ai_olasilik > 0.4) { riskClass = 'risk-mid'; riskText = 'Orta'; }
                
                let barColor = '#00b894';
                if (a.ai_olasilik > 0.6) barColor = '#e94560';
                else if (a.ai_olasilik > 0.4) barColor = '#fdcb6e';
                
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${a.isim}</strong><br><small style="color:#8892b0">${a.kategori}</small></td>
                        <td>${a.deger.toFixed(4)}</td>
                        <td><span class="risk-badge ${riskClass}">%${pct} ${riskText}</span></td>
                        <td style="width:200px">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width:${pct}%;background:${barColor}"></div>
                            </div>
                        </td>
                        <td style="color:#8892b0;font-size:0.9em">${a.aciklama}</td>
                    </tr>`;
            });
            
            document.getElementById('results').classList.add('show');
        }
        
        function drawWaveform(data) {
            const ctx = document.getElementById('waveformChart').getContext('2d');
            if (waveformChart) waveformChart.destroy();
            
            waveformChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.time,
                    datasets: [{
                        data: data.amplitude,
                        borderColor: '#e94560',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(233, 69, 96, 0.15)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { 
                            display: true, 
                            title: { display: true, text: 'Saniye', color: '#8892b0' },
                            ticks: { color: '#8892b0', maxTicksLimit: 10 },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        y: { 
                            display: true,
                            title: { display: true, text: 'Genlik', color: '#8892b0' },
                            ticks: { color: '#8892b0' },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        }
                    }
                }
            });
        }
        
        function drawSpectrum(data) {
            const ctx = document.getElementById('spectrumChart').getContext('2d');
            if (spectrumChart) spectrumChart.destroy();
            
            spectrumChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.frequency,
                    datasets: [{
                        data: data.magnitude,
                        borderColor: '#74b9ff',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(116, 185, 255, 0.15)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            display: true,
                            title: { display: true, text: 'Frekans (Hz)', color: '#8892b0' },
                            ticks: { color: '#8892b0', maxTicksLimit: 10 },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        y: {
                            type: 'logarithmic',
                            display: true,
                            title: { display: true, text: 'Genlik (log)', color: '#8892b0' },
                            ticks: { color: '#8892b0' },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "Dosya yuklenemedi"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400
    
    # Kaydet
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        # Yukle ve analiz et
        y, sr = librosa.load(filepath, sr=22050)
        sure = float(librosa.get_duration(y=y, sr=sr))
        
        sonuclar = []
        fonks = [yuksek_frekans_analizi, spektral_analiz, ritim_analizi, harmonik_analiz,
                 sureksizlik_analiz, watermark_analiz, mfcc_analiz, kontrast_analiz]
        
        for f in fonks:
            try:
                sonuclar.append(f(y, sr))
            except Exception as e:
                print(f"Hata: {f.__name__}: {e}")
        
        # Skor hesapla
        toplam_ag = sum(a["agirlik"] for a in sonuclar)
        genel_skor = sum(a["ai_olasilik"] * a["agirlik"] for a in sonuclar) / toplam_ag if toplam_ag else 0
        
        if genel_skor > 0.75: guven = "Yuksek"
        elif genel_skor > 0.55: guven = "Orta"
        elif genel_skor > 0.45: guven = "Belirsiz"
        else: guven = "Dusuk"
        
        # Grafik verileri
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
# ANA PROGRAM
# ============================================================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  AI MUZIK TESPIT ARACI - WEB")
    print("=" * 50)
    print("\n  Tarayicinizi acin: http://localhost:5000")
    print("  Durdurmak icin: Ctrl+C\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
