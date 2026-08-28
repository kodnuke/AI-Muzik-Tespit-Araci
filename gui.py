"""
AI Muzik Tespit Araci - Grafiksel Arayuz
=========================================
Muzik dosyalarini grafigsel olarak analiz eden masaustu uygulamasi.

Kullanim:
    python gui.py

Gerekli paketler:
    pip install librosa numpy scipy soundfile rich matplotlib
"""

import sys
import os
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np
import librosa
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ============================================================
# ANALIZ MOTORU (music.py'den bagimsiz)
# ============================================================

@dataclass
class AnalizSonucu:
    isim: str
    deger: float
    ai_olasilik: float
    aciklama: str
    agirlik: float = 1.0
    kategori: str = "Genel"

@dataclass
class Rapor:
    dosya_adi: str
    dosya_yolu: str
    sure: float
    sr: int
    analizler: List[AnalizSonucu] = field(default_factory=list)
    genel_skor: float = 0.0
    ai_tahmini: bool = False
    guven: str = "Dusuk"
    waveform: np.ndarray = None
    sr_waveform: int = 22050

    def guncelle(self):
        if not self.analizler:
            return
        toplam_agirlik = sum(a.agirlik for a in self.analizler)
        self.genel_skor = sum(a.ai_olasilik * a.agirlik for a in self.analizler) / toplam_agirlik
        self.ai_tahmini = self.genel_skor > 0.5
        if self.genel_skor > 0.75:
            self.guven = "Yuksek"
        elif self.genel_skor > 0.55:
            self.guven = "Orta"
        elif self.genel_skor > 0.45:
            self.guven = "Belirsiz"
        else:
            self.guven = "Dusuk"


class AnalizMotoru:
    """Tum analiz metodlarini iceren motor sinifi."""
    
    @staticmethod
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
        
        if oran > 0.8:
            ai_olasilik = 0.7
        elif oran < 0.05:
            ai_olasilik = 0.6
        elif 0.1 < oran < 0.4:
            ai_olasilik = 0.25
        else:
            ai_olasilik = 0.4
        
        return AnalizSonucu(
            isim="Yuksek Frekans",
            deger=float(oran),
            ai_olasilik=ai_olasilik,
            aciklama=f"16kHz+/8-16kHz: {oran:.4f}",
            agirlik=1.5,
            kategori="Spektral"
        )
    
    @staticmethod
    def spektral_analiz(y, sr):
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        flatness_ort = np.mean(flatness)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        centroid_ort = np.mean(centroid)
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        bandwidth_ort = np.mean(bandwidth)
        
        if flatness_ort < 0.01:
            ai_olasilik = 0.65
        elif flatness_ort < 0.05:
            ai_olasilik = 0.5
        elif flatness_ort > 0.2:
            ai_olasilik = 0.3
        else:
            ai_olasilik = 0.4
        
        return AnalizSonucu(
            isim="Spektral Kalite",
            deger=float(flatness_ort),
            ai_olasilik=ai_olasilik,
            aciklama=f"Flatness={flatness_ort:.4f}, C={centroid_ort:.0f}Hz",
            agirlik=2.0,
            kategori="Spektral"
        )
    
    @staticmethod
    def ritim_analizi(y, sr):
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, '__len__'):
            tempo = tempo[0]
        
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        if len(beat_times) < 3:
            return AnalizSonucu("Ritim", 0.0, 0.5, "Yeterli beat algılanamadi", 1.0, "Ritimik")
        
        beat_intervals = np.diff(beat_times)
        cv = np.std(beat_intervals) / (np.mean(beat_intervals) + 1e-10)
        
        rms = librosa.feature.rms(y=y)[0]
        rms_cv = np.std(rms) / (np.mean(rms) + 1e-10)
        
        if cv < 0.02:
            ai_olasilik = 0.75
        elif cv < 0.05:
            ai_olasilik = 0.55
        elif cv > 0.15:
            ai_olasilik = 0.2
        else:
            ai_olasilik = 0.35
        
        if rms_cv < 0.3:
            ai_olasilik = min(ai_olasilik + 0.15, 0.9)
        
        return AnalizSonucu(
            isim="Ritim & Dynamics",
            deger=float(cv),
            ai_olasilik=ai_olasilik,
            aciklama=f"Tempo={tempo:.0f}BPM, CV={cv:.4f}",
            agirlik=1.5,
            kategori="Ritimik"
        )
    
    @staticmethod
    def harmonik_analiz(y, sr):
        y_harmonic, _ = librosa.effects.hpss(y)
        harmonik_enerji = np.sum(y_harmonic ** 2)
        toplam_enerji = np.sum(y ** 2) + 1e-10
        harmonik_oran = harmonik_enerji / toplam_enerji
        
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_entropi = -np.sum((np.mean(chroma, axis=1) + 1e-10) * np.log(np.mean(chroma, axis=1) + 1e-10))
        
        if harmonik_oran > 0.95:
            ai_olasilik = 0.7
        elif harmonik_oran > 0.85:
            ai_olasilik = 0.5
        elif harmonik_oran < 0.5:
            ai_olasilik = 0.25
        else:
            ai_olasilik = 0.4
        
        if chroma_entropi < 1.5:
            ai_olasilik = min(ai_olasilik + 0.15, 0.85)
        
        return AnalizSonucu(
            isim="Harmonik Yapi",
            deger=float(harmonik_oran),
            ai_olasilik=ai_olasilik,
            aciklama=f"Oran={harmonik_oran:.3f}, Entropi={chroma_entropi:.2f}",
            agirlik=1.5,
            kategori="Harmonik"
        )
    
    @staticmethod
    def sureksizlik_analizi(y, sr):
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        energy_diff = np.abs(np.diff(rms))
        ortalama_degisim = np.mean(energy_diff)
        
        zcr = librosa.feature.zero_crossing_rate(y, frame_length=2048, hop_length=512)[0]
        zcr_ort = np.mean(zcr)
        
        if ortalama_degisim < 0.005:
            ai_olasilik = 0.7
        elif ortalama_degisim < 0.01:
            ai_olasilik = 0.55
        elif ortalama_degisim > 0.05:
            ai_olasilik = 0.2
        else:
            ai_olasilik = 0.35
        
        return AnalizSonucu(
            isim="Sureksizlik",
            deger=float(ortalama_degisim),
            ai_olasilik=ai_olasilik,
            aciklama=f"Enerji degisimi={ortalama_degisim:.5f}",
            agirlik=1.0,
            kategori="Dinamik"
        )
    
    @staticmethod
    def watermark_analizi(y, sr):
        fft = np.fft.fft(y)
        freqs = np.fft.fftfreq(len(fft), 1 / sr)
        
        watermark_band = (np.abs(freqs) > 19000) & (np.abs(freqs) < 20000)
        watermark_enerji = np.sum(np.abs(fft[watermark_band])) if np.any(watermark_band) else 0
        toplam_enerji = np.sum(np.abs(fft))
        
        fft_mag = np.abs(fft[freqs > 0])
        if len(fft_mag) > 100:
            pik_esi = np.mean(fft_mag) + 5 * np.std(fft_mag)
            pik_oran = np.sum(fft_mag > pik_esi) / len(fft_mag)
        else:
            pik_oran = 0
        
        watermark_oran = watermark_enerji / (toplam_enerji + 1e-10)
        
        if watermark_oran > 1e-4 and pik_oran > 0.01:
            ai_olasilik = 0.85
        elif watermark_oran > 1e-5:
            ai_olasilik = 0.55
        else:
            ai_olasilik = 0.3
        
        return AnalizSonucu(
            isim="Watermark",
            deger=float(watermark_oran),
            ai_olasilik=ai_olasilik,
            aciklama=f"Orani={watermark_oran:.8f}",
            agirlik=1.5,
            kategori="Watermark"
        )
    
    @staticmethod
    def mfcc_analiz(y, sr):
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        std_degerleri = np.std(mfccs, axis=1)
        ort_degerleri = np.mean(mfccs, axis=1)
        cv = std_degerleri / (np.abs(ort_degerleri) + 1e-10)
        ortalama_cv = np.mean(cv)
        
        if ortalama_cv < 0.3:
            ai_olasilik = 0.7
        elif ortalama_cv < 0.5:
            ai_olasilik = 0.5
        elif ortalama_cv > 1.5:
            ai_olasilik = 0.2
        else:
            ai_olasilik = 0.35
        
        return AnalizSonucu(
            isim="MFCC Tini",
            deger=float(ortalama_cv),
            ai_olasilik=ai_olasilik,
            aciklama=f"CV={ortalama_cv:.4f}",
            agirlik=1.0,
            kategori="Tini"
        )
    
    @staticmethod
    def kontrast_analiz(y, sr):
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        rolloff_ort = np.mean(rolloff)
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_std = np.std(contrast)
        
        if contrast_std < 2.0:
            ai_olasilik = 0.65
        elif contrast_std < 5.0:
            ai_olasilik = 0.45
        elif contrast_std > 15.0:
            ai_olasilik = 0.2
        else:
            ai_olasilik = 0.35
        
        return AnalizSonucu(
            isim="Spektral Kontrast",
            deger=float(contrast_std),
            ai_olasilik=ai_olasilik,
            aciklama=f"Rolloff={rolloff_ort:.0f}Hz, STD={contrast_std:.2f}",
            agirlik=1.0,
            kategori="Spektral"
        )
    
    @classmethod
    def tum_analizleri_calistir(cls, y, sr):
        analizler = [
            cls.yuksek_frekans_analizi,
            cls.spektral_analiz,
            cls.ritim_analizi,
            cls.harmonik_analiz,
            cls.sureksizlik_analizi,
            cls.watermark_analizi,
            cls.mfcc_analiz,
            cls.kontrast_analiz,
        ]
        sonuclar = []
        for fonk in analizler:
            try:
                sonuc = fonk(y, sr)
                sonuclar.append(sonuc)
            except Exception as e:
                print(f"Hata: {fonk.__name__} - {e}")
        return sonuclar


# ============================================================
# GUI UYGULAMASI
# ============================================================

class AIMuzikAnalizApp:
    """AI Muzik Tespit Araci GUI Uygulamasi."""
    
    def __init__(self):
        # Ana pencere
        self.root = tk.Tk()
        self.root.title("AI Muzik Tespit Araci")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Tema
        self.colors = {
            'bg': '#1a1a2e',
            'bg_light': '#16213e',
            'bg_card': '#0f3460',
            'accent': '#e94560',
            'accent2': '#533483',
            'text': '#ffffff',
            'text_dim': '#a0a0a0',
            'success': '#00b894',
            'warning': '#fdcb6e',
            'danger': '#e94560',
            'info': '#74b9ff',
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Stil
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Degiskenler
        self.dosya_yolu = tk.StringVar(value="Dosya secilmedi...")
        self.analiz_devam = False
        self.rapor = None
        
        # Arayuzu olustur
        self.arayuz_olustur()
        
        # Sürükle-bırak binding (Windows)
        self.root.drop_target_register = None  # tkdnd varsa
        
    def configure_styles(self):
        """Tema stillerini ayarla."""
        self.style.configure('Title.TLabel', 
                           background=self.colors['bg'], 
                           foreground=self.colors['text'],
                           font=('Segoe UI', 24, 'bold'))
        self.style.configure('Subtitle.TLabel', 
                           background=self.colors['bg'], 
                           foreground=self.colors['text_dim'],
                           font=('Segoe UI', 12))
        self.style.configure('Card.TFrame', 
                           background=self.colors['bg_card'])
        self.style.configure('Card.TLabel', 
                           background=self.colors['bg_card'],
                           foreground=self.colors['text'],
                           font=('Segoe UI', 11))
        self.style.configure('Accent.TButton',
                           font=('Segoe UI', 12, 'bold'))
        
    def arayuz_olustur(self):
        """Ana arayuz yapısını olustur."""
        # Ana container
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # ust kisim - baslik ve dosya secme
        self.ust_frame = tk.Frame(self.main_frame, bg=self.colors['bg'])
        self.ust_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Baslik
        baslik_frame = tk.Frame(self.ust_frame, bg=self.colors['bg'])
        baslik_frame.pack(fill=tk.X)
        
        tk.Label(baslik_frame, 
                text="AI MUZIK TESPIT ARACI",
                bg=self.colors['bg'],
                fg=self.colors['accent'],
                font=('Segoe UI', 28, 'bold')).pack(side=tk.LEFT)
        
        tk.Label(baslik_frame,
                text="v2.0",
                bg=self.colors['bg'],
                fg=self.colors['text_dim'],
                font=('Segoe UI', 14)).pack(side=tk.LEFT, padx=(10, 0), pady=(5, 0))
        
        # Alt baslik
        tk.Label(self.ust_frame,
                text="Muzik dosyalarinizi analiz edin - AI mi insanim mi?",
                bg=self.colors['bg'],
                fg=self.colors['text_dim'],
                font=('Segoe UI', 11)).pack(anchor=tk.W, pady=(5, 0))
        
        # Dosya secme alani
        dosya_frame = tk.Frame(self.ust_frame, bg=self.colors['bg_light'], 
                              highlightbackground=self.colors['accent2'],
                              highlightthickness=2)
        dosya_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Dosya yolu gosterimi
        self.dosya_label = tk.Label(dosya_frame, 
                                   textvariable=self.dosya_yolu,
                                   bg=self.colors['bg_light'],
                                   fg=self.colors['text'],
                                   font=('Consolas', 11),
                                   anchor=tk.W)
        self.dosya_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15, pady=12)
        
        # Sec butonu
        self.sec_btn = tk.Button(dosya_frame, text="DOSYA SEC",
                                bg=self.colors['accent2'],
                                fg=self.colors['text'],
                                font=('Segoe UI', 11, 'bold'),
                                relief=tk.FLAT,
                                padx=20, pady=10,
                                cursor='hand2',
                                command=self.dosya_sec)
        self.sec_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Analiz butonu
        self.analiz_btn = tk.Button(dosya_frame, text="ANALIZ ET",
                                   bg=self.colors['accent'],
                                   fg=self.colors['text'],
                                   font=('Segoe UI', 11, 'bold'),
                                   relief=tk.FLAT,
                                   padx=20, pady=10,
                                   cursor='hand2',
                                   state=tk.DISABLED,
                                   command=self.analiz_baslat)
        self.analiz_btn.pack(side=tk.RIGHT, padx=5, pady=10)
        
        # Orta kisim - grafikler ve sonuclar
        orta_frame = tk.Frame(self.main_frame, bg=self.colors['bg'])
        orta_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        # Sol panel - grafikler
        sol_panel = tk.Frame(orta_frame, bg=self.colors['bg'])
        sol_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Waveform grafigi
        self.waveform_frame = tk.LabelFrame(sol_panel, text="DALGA SEKLI",
                                           bg=self.colors['bg_card'],
                                           fg=self.colors['text'],
                                           font=('Segoe UI', 10, 'bold'))
        self.waveform_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.waveform_fig = Figure(figsize=(5, 2), dpi=100, facecolor=self.colors['bg_card'])
        self.waveform_ax = self.waveform_fig.add_subplot(111)
        self.waveform_ax.set_facecolor(self.colors['bg_light'])
        self.waveform_ax.tick_params(colors=self.colors['text_dim'], labelsize=8)
        self.waveform_fig.tight_layout(pad=1)
        
        self.waveform_canvas = FigureCanvasTkAgg(self.waveform_fig, self.waveform_frame)
        self.waveform_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Spektrum grafigi
        self.spektrum_frame = tk.LabelFrame(sol_panel, text="FREKANS SPEKTRUMU",
                                           bg=self.colors['bg_card'],
                                           fg=self.colors['text'],
                                           font=('Segoe UI', 10, 'bold'))
        self.spektrum_frame.pack(fill=tk.BOTH, expand=True)
        
        self.spektrum_fig = Figure(figsize=(5, 2), dpi=100, facecolor=self.colors['bg_card'])
        self.spektrum_ax = self.spektrum_fig.add_subplot(111)
        self.spektrum_ax.set_facecolor(self.colors['bg_light'])
        self.spektrum_ax.tick_params(colors=self.colors['text_dim'], labelsize=8)
        self.spektrum_fig.tight_layout(pad=1)
        
        self.spektrum_canvas = FigureCanvasTkAgg(self.spektrum_fig, self.spektrum_frame)
        self.spektrum_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Sag panel - sonuclar
        sag_panel = tk.Frame(orta_frame, bg=self.colors['bg'], width=380)
        sag_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(15, 0))
        sag_panel.pack_propagate(False)
        
        # Sonuc karti
        self.sonuc_frame = tk.LabelFrame(sag_panel, text="SONUC",
                                        bg=self.colors['bg_card'],
                                        fg=self.colors['text'],
                                        font=('Segoe UI', 12, 'bold'))
        self.sonuc_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.sonuc_label = tk.Label(self.sonuc_frame,
                                   text="Analiz bekleniyor...",
                                   bg=self.colors['bg_card'],
                                   fg=self.colors['text_dim'],
                                   font=('Segoe UI', 14),
                                   wraplength=350,
                                   justify=tk.CENTER)
        self.sonuc_label.pack(padx=20, pady=20)
        
        # Skor gosterge
        skor_frame = tk.Frame(self.sonuc_frame, bg=self.colors['bg_card'])
        skor_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.skor_label = tk.Label(skor_frame,
                                  text="AI Skoru: ---%",
                                  bg=self.colors['bg_card'],
                                  fg=self.colors['accent'],
                                  font=('Segoe UI', 18, 'bold'))
        self.skor_label.pack()
        
        self.guven_label = tk.Label(skor_frame,
                                   text="Guven: ---",
                                   bg=self.colors['bg_card'],
                                   fg=self.colors['text_dim'],
                                   font=('Segoe UI', 11))
        self.guven_label.pack()
        
        # Analiz detaylari tablosu
        tablo_frame = tk.LabelFrame(sag_panel, text="ANALIZ DETAYLARI",
                                   bg=self.colors['bg_card'],
                                   fg=self.colors['text'],
                                   font=('Segoe UI', 10, 'bold'))
        tablo_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ('analiz', 'skor', 'ai_olasi')
        self.tablo = ttk.Treeview(tablo_frame, columns=columns, show='headings', height=8)
        
        self.tablo.heading('analiz', text='Analiz')
        self.tablo.heading('skor', text='Deger')
        self.tablo.heading('ai_olasi', text='AI Olasilik')
        
        self.tablo.column('analiz', width=140)
        self.tablo.column('skor', width=80, anchor=tk.CENTER)
        self.tablo.column('ai_olasi', width=80, anchor=tk.CENTER)
        
        # Treeview stil
        self.style.configure('Treeview',
                           background=self.colors['bg_light'],
                           foreground=self.colors['text'],
                           fieldbackground=self.colors['bg_light'],
                           font=('Segoe UI', 9))
        self.style.configure('Treeview.Heading',
                           background=self.colors['accent2'],
                           foreground=self.colors['text'],
                           font=('Segoe UI', 9, 'bold'))
        
        scrollbar = ttk.Scrollbar(tablo_frame, orient=tk.VERTICAL, command=self.tablo.yview)
        self.tablo.configure(yscrollcommand=scrollbar.set)
        
        self.tablo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Alt bilgi
        alt_frame = tk.Frame(self.main_frame, bg=self.colors['bg'])
        alt_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(alt_frame,
                text="Desteklenen: WAV, MP3, FLAC, OGG, M4A, AIFF | Gerekli: librosa, numpy, scipy, matplotlib",
                bg=self.colors['bg'],
                fg=self.colors['text_dim'],
                font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(alt_frame, mode='indeterminate', length=200)
        self.progress.pack(side=tk.RIGHT, padx=10)
        
        # Durum etiketi
        self.durum_label = tk.Label(alt_frame,
                                   text="Hazir",
                                   bg=self.colors['bg'],
                                   fg=self.colors['success'],
                                   font=('Segoe UI', 9))
        self.durum_label.pack(side=tk.RIGHT)
        
    def dosya_sec(self):
        """Dosya secme dialogu."""
        dosya_turleri = [
            ("Muzik Dosyalari", "*.wav *.mp3 *.flac *.ogg *.m4a *.aiff *.aif"),
            ("WAV", "*.wav"),
            ("MP3", "*.mp3"),
            ("FLAC", "*.flac"),
            ("Tum Dosyalar", "*.*")
        ]
        
        dosya = filedialog.askopenfilename(
            title="Muzik Dosyasi Sec",
            filetypes=dosya_turleri
        )
        
        if dosya:
            self.dosya_yolu.set(dosya)
            self.analiz_btn.config(state=tk.NORMAL)
            self.durum_label.config(text="Dosya secildi", fg=self.colors['info'])
    
    def analiz_baslat(self):
        """Analizi arka planda baslat."""
        if self.analiz_devam:
            return
        
        dosya = self.dosya_yolu.get()
        if not dosya or dosya == "Dosya secilmedi...":
            messagebox.showwarning("Uyari", "Lutfen bir dosya secin!")
            return
        
        self.analiz_devam = True
        self.analiz_btn.config(state=tk.DISABLED)
        self.sec_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.durum_label.config(text="Analiz ediliyor...", fg=self.colors['warning'])
        self.tablo.delete(*self.tablo.get_children())
        self.sonuc_label.config(text="Analiz ediliyor...", fg=self.colors['text_dim'])
        self.skor_label.config(text="AI Skoru: ...")
        self.guven_label.config(text="Guven: ...")
        
        # Grafikleri temizle
        self.waveform_ax.clear()
        self.waveform_ax.set_facecolor(self.colors['bg_light'])
        self.waveform_ax.set_title("Yukleniyor...", color=self.colors['text_dim'], fontsize=9)
        self.waveform_canvas.draw()
        
        self.spektrum_ax.clear()
        self.spektrum_ax.set_facecolor(self.colors['bg_light'])
        self.spektrum_ax.set_title("Yukleniyor...", color=self.colors['text_dim'], fontsize=9)
        self.spektrum_canvas.draw()
        
        # Arka planda calistir
        thread = threading.Thread(target=self.analiz_calistir, args=(dosya,))
        thread.daemon = True
        thread.start()
    
    def analiz_calistir(self, dosya_yolu):
        """Analizi arka planda calistir."""
        try:
            # Dosyani yukle
            y, sr = librosa.load(dosya_yolu, sr=22050)
            sure = librosa.get_duration(y=y, sr=sr)
            
            # Rapor olustur
            rapor = Rapor(
                dosya_adi=os.path.basename(dosya_yolu),
                dosya_yolu=dosya_yolu,
                sure=sure,
                sr=sr,
                waveform=y,
                sr_waveform=sr
            )
            
            # Analizleri calistir
            sonuclar = AnalizMotoru.tum_analizleri_calistir(y, sr)
            rapor.analizler = sonuclar
            rapor.guncelle()
            
            self.rapor = rapor
            
            # GUI'yi guncelle (ana thread'de)
            self.root.after(0, self.sonuclari_goster, rapor)
            
        except Exception as e:
            self.root.after(0, self.hata_goster, str(e))
        finally:
            self.analiz_devam = False
            self.root.after(0, self.analiz_tamamlandi)
    
    def sonuclari_goster(self, rapor):
        """Analiz sonuclarini GUI'de goster."""
        # Durum guncelle
        self.durum_label.config(text="Analiz tamamlandi", fg=self.colors['success'])
        
        # Sonuc karti
        if rapor.ai_tahmini:
            sonuc_renk = self.colors['danger']
            sonuc_text = "AI TARAFINDAN\nURETILMIS OLABILIR"
            emoji = "ROBOT"
        else:
            sonuc_renk = self.colors['success']
            sonuc_text = "INSAN TARAFINDAN\nURETILMIS GORUNUYOR"
            emoji = "INSAN"
        
        self.sonuc_label.config(text=f"{sonuc_text}", fg=sonuc_renk)
        self.skor_label.config(text=f"AI Skoru: %{rapor.genel_skor*100:.1f}", fg=sonuc_renk)
        self.guven_label.config(text=f"Guven: {rapor.guven}")
        
        # Tabloyu doldur
        for a in rapor.analizler:
            if a.ai_olasilik > 0.6:
                renk = 'danger'
            elif a.ai_olasilik > 0.4:
                renk = 'warning'
            else:
                renk = 'success'
            
            self.tablo.insert('', tk.END, values=(
                a.isim,
                f"{a.deger:.4f}",
                f"%{a.ai_olasilik*100:.0f}"
            ))
        
        # Grafikleri ciz
        self.grafikleri_ciz(rapor)
    
    def grafikleri_ciz(self, rapor):
        """Waveform ve spektrum grafiklerini ciz."""
        y = rapor.waveform
        sr = rapor.sr_waveform
        
        # Waveform
        self.waveform_ax.clear()
        self.waveform_ax.set_facecolor(self.colors['bg_light'])
        
        time_axis = np.linspace(0, rapor.sure, len(y))
        self.waveform_ax.plot(time_axis, y, color=self.colors['accent'], linewidth=0.5, alpha=0.8)
        self.waveform_ax.fill_between(time_axis, y, alpha=0.3, color=self.colors['accent2'])
        self.waveform_ax.set_xlabel('Saniye', color=self.colors['text_dim'], fontsize=8)
        self.waveform_ax.set_ylabel('Genlik', color=self.colors['text_dim'], fontsize=8)
        self.waveform_ax.set_title('Dalga Sekli', color=self.colors['text'], fontsize=10, fontweight='bold')
        self.waveform_ax.tick_params(colors=self.colors['text_dim'], labelsize=7)
        self.waveform_ax.set_xlim(0, rapor.sure)
        
        # Grid
        self.waveform_ax.grid(True, alpha=0.2, color=self.colors['text_dim'])
        
        self.waveform_fig.tight_layout(pad=1)
        self.waveform_canvas.draw()
        
        # Spektrum (FFT)
        self.spektrum_ax.clear()
        self.spektrum_ax.set_facecolor(self.colors['bg_light'])
        
        fft = np.fft.fft(y)
        freqs = np.fft.fftfreq(len(fft), 1/sr)
        pos_mask = freqs > 0
        magnitude = np.abs(fft[pos_mask])
        freqs_pos = freqs[pos_mask]
        
        # Frekans araligini sinirla (0-12kHz)
        max_freq = min(12000, sr // 2)
        freq_mask = freqs_pos <= max_freq
        
        self.spektrum_ax.semilogy(freqs_pos[freq_mask], magnitude[freq_mask], 
                                  color=self.colors['info'], linewidth=0.5, alpha=0.8)
        
        # 16kHz cizgisi
        if max_freq > 16000:
            self.spektrum_ax.axvline(x=16000, color=self.colors['warning'], 
                                     linestyle='--', alpha=0.7, label='16kHz')
        
        self.spektrum_ax.set_xlabel('Frekans (Hz)', color=self.colors['text_dim'], fontsize=8)
        self.spektrum_ax.set_ylabel('Genlik (log)', color=self.colors['text_dim'], fontsize=8)
        self.spektrum_ax.set_title('Frekans Spektrumu', color=self.colors['text'], fontsize=10, fontweight='bold')
        self.spektrum_ax.tick_params(colors=self.colors['text_dim'], labelsize=7)
        self.spektrum_ax.set_xlim(0, max_freq)
        
        # Grid
        self.spektrum_ax.grid(True, alpha=0.2, color=self.colors['text_dim'])
        
        self.spektrum_fig.tight_layout(pad=1)
        self.spektrum_canvas.draw()
    
    def hata_goster(self, hata):
        """Hata mesaji goster."""
        self.durum_label.config(text="Hata olustu", fg=self.colors['danger'])
        messagebox.showerror("Hata", f"Analiz sirasinda hata olustu:\n\n{hata}")
    
    def analiz_tamamlandi(self):
        """Analiz tamamlandiginda butonlari aktiflesir."""
        self.analiz_btn.config(state=tk.NORMAL)
        self.sec_btn.config(state=tk.NORMAL)
        self.progress.stop()
    
    def calistir(self):
        """Uygulamayi baslat."""
        self.root.mainloop()


# ============================================================
# KONSOL MODU (GUI olmadan)
# ============================================================

def konsol_modu(dosya_yolu):
    """Konsol tabanli analiz (GUI olmadan)."""
    print(f"\n>> Analiz ediliyor: {dosya_yolu}\n")
    
    try:
        y, sr = librosa.load(dosya_yolu, sr=22050)
        sure = librosa.get_duration(y=y, sr=sr)
        print(f"  [OK] Yuklendi: {sure:.1f}s, {sr}Hz\n")
    except Exception as e:
        print(f"  [HATA] Dosya yuklenemedi: {e}")
        return
    
    rapor = Rapor(
        dosya_adi=os.path.basename(dosya_yolu),
        dosya_yolu=dosya_yolu,
        sure=sure,
        sr=sr
    )
    
    sonuclar = AnalizMotoru.tum_analizleri_calistir(y, sr)
    rapor.analizler = sonuclar
    rapor.guncelle()
    
    # Sonuclari yazdir
    print("=" * 60)
    print(f"  AI MUZIK ANALIZ RAPORU - {rapor.dosya_adi}")
    print("=" * 60)
    
    for a in rapor.analizler:
        if a.ai_olasilik > 0.6:
            durum = "[!!]"
        elif a.ai_olasilik > 0.4:
            durum = "[~]"
        else:
            durum = "[OK]"
        print(f"  {durum} {a.isim:20s} | {a.deger:10.4f} | AI: %{a.ai_olasilik*100:.0f} | {a.aciklama}")
    
    print("-" * 60)
    
    if rapor.ai_tahmini:
        print(f"\n  >> AI TARAFINDAN URETILMIS OLABILIR (Skor: %{rapor.genel_skor*100:.1f})")
    else:
        print(f"\n  >> INSAN TARAFINDAN URETILMIS GORUNUYOR (Skor: %{rapor.genel_skor*100:.1f})")
    
    print(f"  Guven: {rapor.guven}")
    print(f"  Sure: {rapor.sure:.1f}s | Ornekleme: {rapor.sr}Hz\n")
    
    # JSON kaydet
    json_dosya = rapor.dosya_adi.rsplit('.', 1)[0] + "_analiz.json"
    veri = {
        "dosya": rapor.dosya_adi,
        "sure_saniye": round(rapor.sure, 2),
        "ornekleme_hizi": rapor.sr,
        "genel_skor": round(rapor.genel_skor, 4),
        "ai_tahmini": rapor.ai_tahmini,
        "guven": rapor.guven,
        "analizler": [
            {"isim": a.isim, "deger": round(a.deger, 6), 
             "ai_olasilik": round(a.ai_olasilik, 4), "aciklama": a.aciklama}
            for a in rapor.analizler
        ]
    }
    
    with open(json_dosya, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    
    print(f"  JSON rapor: {json_dosya}\n")


# ============================================================
# ANA PROGRAM
# ============================================================

def main():
    """Ana fonksiyon."""
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
    
    if len(sys.argv) > 1:
        # Konsol modu
        if sys.argv[1] == "--konsol" and len(sys.argv) > 2:
            konsol_modu(sys.argv[2])
        elif sys.argv[1] == "--yardim" or sys.argv[1] == "-h":
            print("""
AI Muzik Tespit Araci v2.0
==========================

Kullanim:
    python gui.py              - GUI modunda baslat
    python gui.py --konsol <dosya>  - Konsol modunda analiz et
    python gui.py --yardim     - Yardim goster
""")
        else:
            # Dogrudan dosya verildiyse konsol modu
            konsol_modu(sys.argv[1])
    else:
        # GUI modu
        try:
            app = AIMuzikAnalizApp()
            app.calistir()
        except Exception as e:
            print(f"GUI baslatilamadi: {e}")
            print("Konsol modu icin: python gui.py --konsol <dosya>")


if __name__ == "__main__":
    main()
