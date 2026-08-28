"""
AI Muzik Tespit Araci
====================
Bu program, bir muzik dosyasinin yapay zeka tarafindan uretilip uretilmedigini
cesitli ses analizleri ile tespit etmeye calisir.

Kullanim:
    python music.py <music_file>

Ornek:
    python music.py ai_music.wav
    python music.py orijinal_sarki.mp3

Gerekli paketler:
    pip install librosa numpy scipy soundfile rich
"""

import sys
import os
import json
from dataclasses import dataclass, field
from typing import Optional

import librosa
import numpy as np
from scipy import stats

# Rich kutuphanesi varsa guzel cikti, yoksa duz cikti
try:
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except (ImportError, Exception):
    RICH_AVAILABLE = False


# --- Veri Yapilari ---

@dataclass
class AnalizSonucu:
    """Tek bir analiz parametresinin sonucu"""
    isim: str
    deger: float
    ai_olasilik: float  # 0.0 - 1.0 arasi (1.0 = kesin AI)
    aciklama: str
    agirlik: float = 1.0


@dataclass
class Rapor:
    """Tum analiz sonuclarini bir araya getiren rapor"""
    dosya_adi: str
    sure: float  # saniye
    sr: int
    analizler: list = field(default_factory=list)
    genel_skor: float = 0.0
    ai_tahmini: bool = False
    guven: str = "Dusuk"

    def __post_init__(self):
        self.guncelle()

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


# --- Analiz Fonksiyonlari ---

def yuksek_frekans_analizi(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    AI muzikte genellikle 16kHz uzeri frekanslarda anormal enerji bulunur.
    AI modelleri ultra yuksek frekans detaylarini dogru uretemez.
    """
    fft = np.fft.fft(y)
    freqs = np.fft.fftfreq(len(fft), 1 / sr)
    
    # Pozitif frekanslar
    pos_mask = freqs > 0
    magnitudes = np.abs(fft[pos_mask])
    freqs_pos = freqs[pos_mask]
    
    # 16kHz uzeri enerji orani
    yuksek_mask = freqs_pos > 16000
    orta_mask = (freqs_pos > 8000) & (freqs_pos <= 16000)
    
    yuksek_enerji = np.mean(magnitudes[yuksek_mask]) if np.any(yuksek_mask) else 0
    orta_enerji = np.mean(magnitudes[orta_mask]) if np.any(orta_mask) else 1
    
    oran = yuksek_enerji / (orta_enerji + 1e-10)
    
    # AI: cok yuksek veya cok dusuk high-freq enerjisi
    if oran > 0.8:
        ai_olasilik = 0.7  # Anormal yuksek
    elif oran < 0.05:
        ai_olasilik = 0.6  # Anormal dusuk (fazla temiz)
    elif 0.1 < oran < 0.4:
        ai_olasilik = 0.25  # Dogal aralik
    else:
        ai_olasilik = 0.4
    
    return AnalizSonucu(
        isim="Yuksek Frekans Analizi",
        deger=float(oran),
        ai_olasilik=ai_olasilik,
        aciklama=f"16kHz+/8-16kHz enerji orani: {oran:.4f}",
        agirlik=1.5
    )


def spektral_analiz(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    Spektral flatness analizi.
    AI muzikte tini cok duzgun ve "plastik" olur.
    """
    # Spektral centroid
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    centroid_ort = np.mean(centroid)
    
    # Spektral flatness (AI = daha duzgun)
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    flatness_ort = np.mean(flatness)
    
    # Spektral bandwidth
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    bandwidth_ort = np.mean(bandwidth)
    
    # Dusuk flatness = daha tonal = AI olasiligi yuksek
    if flatness_ort < 0.01:
        ai_olasilik = 0.65
    elif flatness_ort < 0.05:
        ai_olasilik = 0.5
    elif flatness_ort > 0.2:
        ai_olasilik = 0.3  # Gurultulu, dogal
    else:
        ai_olasilik = 0.4
    
    skor_metni = f"Flatness={flatness_ort:.4f}, Centroid={centroid_ort:.0f}Hz, BW={bandwidth_ort:.0f}Hz"
    
    return AnalizSonucu(
        isim="Spektral Kalite",
        deger=float(flatness_ort),
        ai_olasilik=ai_olasilik,
        aciklama=skor_metni,
        agirlik=2.0
    )


def ritim_analizi(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    Tempo ve ritim duzenliligi analizi.
    AI muzikte tempo cok duzgun, ritim kaliplari tekrar edici olur.
    """
    # Tempo ve beat detection
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = tempo[0]
    
    # Beat araliklari
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    if len(beat_times) < 3:
        return AnalizSonucu(
            isim="Ritim Analizi",
            deger=0.0,
            ai_olasilik=0.5,
            aciklama="Yeterli beat algılanamadi",
            agirlik=1.0
        )
    
    beat_intervals = np.diff(beat_times)
    
    # Beat araliklarinin cv (coefficient of variation)
    cv = np.std(beat_intervals) / (np.mean(beat_intervals) + 1e-10)
    
    # RMS varyansi (dynamics)
    rms = librosa.feature.rms(y=y)[0]
    rms_cv = np.std(rms) / (np.mean(rms) + 1e-10)
    
    # Dusuk cv = cok duzgun ritim = AI
    if cv < 0.02:
        ai_olasilik = 0.75
    elif cv < 0.05:
        ai_olasilik = 0.55
    elif cv > 0.15:
        ai_olasilik = 0.2
    else:
        ai_olasilik = 0.35
    
    # Dynamics de dusukse AI olasiligini artir
    if rms_cv < 0.3:
        ai_olasilik = min(ai_olasilik + 0.15, 0.9)
    
    return AnalizSonucu(
        isim="Ritim & Dynamics",
        deger=float(cv),
        ai_olasilik=ai_olasilik,
        aciklama=f"Tempo={tempo:.1f}BPM, Ritim CV={cv:.4f}, Dyn CV={rms_cv:.4f}",
        agirlik=1.5
    )


def harmonik_analiz(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    Harmonik-parcacik ayrimi ve harmonik spektrum analizi.
    AI muzikte harmonik yapi cok "mukemmel" ve simetrik olur.
    """
    # Harmonic-percussive separation
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    
    # Harmonik orani
    harmonik_enerji = np.sum(y_harmonic ** 2)
    toplam_enerji = np.sum(y ** 2) + 1e-10
    harmonik_oran = harmonik_enerji / toplam_enerji
    
    # Chroma analizi - harmonik karmasilik
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_entropi = stats.entropy(np.mean(chroma, axis=1) + 1e-10)
    
    # Dusuk entropi = cok basit harmonik yapi = AI
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
        aciklama=f"Harmonik oran={harmonik_oran:.3f}, Chroma entropi={chroma_entropi:.2f}",
        agirlik=1.5
    )


def sureksizlik_analizi(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    Sinyalin sureksizligi ve gecis analizi.
    AI muzikte gecisler cok yumusak ve "tuhaftir".
    """
    frame_length = 2048
    hop_length = 512
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # Enerji degisim hizi
    energy_diff = np.abs(np.diff(rms))
    ortalama_degisim = np.mean(energy_diff)
    
    # Zero crossing rate
    zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]
    zcr_ort = np.mean(zcr)
    
    # AI: cok yumusak gecisler, dusuk zero-crossing
    if ortalama_degisim < 0.005:
        ai_olasilik = 0.7
    elif ortalama_degisim < 0.01:
        ai_olasilik = 0.55
    elif ortalama_degisim > 0.05:
        ai_olasilik = 0.2
    else:
        ai_olasilik = 0.35
    
    return AnalizSonucu(
        isim="Sureksizlik & Gecis",
        deger=float(ortalama_degisim),
        ai_olasilik=ai_olasilik,
        aciklama=f"Ort. enerji degisimi={ortalama_degisim:.5f}, ZCR={zcr_ort:.4f}",
        agirlik=1.0
    )


def watermark_analizi(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    AI muzik modellerinin watermark arama analizi.
    Bazi AI servisleri yuksek frekansa watermark yerlestirir.
    """
    fft = np.fft.fft(y)
    freqs = np.fft.fftfreq(len(fft), 1 / sr)
    
    # Olasi watermark frekanslarini tara
    watermark_enerji = 0
    toplam_enerji = np.sum(np.abs(fft))
    
    # 19-20kHz arasi (AI watermark icin yaygin)
    watermark_band = (np.abs(freqs) > 19000) & (np.abs(freqs) < 20000)
    if np.any(watermark_band):
        watermark_enerji = np.sum(np.abs(fft[watermark_band]))
    
    # Anormal pikleri kontrol et
    fft_mag = np.abs(fft[freqs > 0])
    if len(fft_mag) > 100:
        pik_esi = np.mean(fft_mag) + 5 * np.std(fft_mag)
        pik_sayisi = np.sum(fft_mag > pik_esi)
        pik_oran = pik_sayisi / len(fft_mag)
    else:
        pik_oran = 0
    
    watermark_oran = watermark_enerji / (toplam_enerji + 1e-10)
    
    if watermark_oran > 1e-4 and pik_oran > 0.01:
        ai_olasilik = 0.85  # Watermark benzeri sinyal
    elif watermark_oran > 1e-5:
        ai_olasilik = 0.55
    else:
        ai_olasilik = 0.3  # Belirgin watermark yok
    
    return AnalizSonucu(
        isim="Watermark Tarama",
        deger=float(watermark_oran),
        ai_olasilik=ai_olasilik,
        aciklama=f"Watermark enerji orani={watermark_oran:.8f}, Pik orani={pik_oran:.4f}",
        agirlik=1.5
    )


def mfcc_analiz(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    MFCC (Mel-Frequency Cepstral Coefficients) analizi.
    AI muzikte MFCC dagilimlari cok duzgun ve Gaussian benzeri olur.
    """
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    
    # Her koefisyan icin istatistikler
    std_degerleri = np.std(mfccs, axis=1)
    ort_degerleri = np.mean(mfccs, axis=1)
    
    # Normalize varyasyon katsayisi
    cv = std_degerleri / (np.abs(ort_degerleri) + 1e-10)
    ortalama_cv = np.mean(cv)
    
    # Dusuk varyasyon = AI
    if ortalama_cv < 0.3:
        ai_olasilik = 0.7
    elif ortalama_cv < 0.5:
        ai_olasilik = 0.5
    elif ortalama_cv > 1.5:
        ai_olasilik = 0.2
    else:
        ai_olasilik = 0.35
    
    return AnalizSonucu(
        isim="MFCC Tini Profili",
        deger=float(ortalama_cv),
        ai_olasilik=ai_olasilik,
        aciklama=f"MFCC ortalama CV={ortalama_cv:.4f}",
        agirlik=1.0
    )


def fonksiyonel_analiz(y: np.ndarray, sr: int) -> AnalizSonucu:
    """
    Spektral kontrast deseni analizi.
    AI muzikte belirli frekans araliklarinda anormal desenler olusur.
    """
    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    rolloff_ort = np.mean(rolloff)
    
    # Spectral contrast
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    contrast_std = np.std(contrast)
    
    # AI: cok dar spektral kontrast
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
        aciklama=f"Rolloff={rolloff_ort:.0f}Hz, Kontrast STD={contrast_std:.2f}",
        agirlik=1.0
    )


# --- Rapor Olusturucu ---

def analiz_calistir(dosya_yolu: str) -> Optional[Rapor]:
    """Tum analizleri calistir ve rapor olustur."""
    
    if not os.path.exists(dosya_yolu):
        print(f"[HATA] Dosya bulunamadi: {dosya_yolu}")
        return None
    
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"\n>> Analiz ediliyor: {dosya_yolu}\n")
    else:
        print(f"\n>> Analiz ediliyor: {dosya_yolu}\n")
    
    try:
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Yukleniyor...", total=None)
                y, sr = librosa.load(dosya_yolu, sr=22050)
                sure = librosa.get_duration(y=y, sr=sr)
                progress.update(task, description=f"Yuklendi: {sure:.1f}s, {sr}Hz")
        else:
            y, sr = librosa.load(dosya_yolu, sr=22050)
            sure = librosa.get_duration(y=y, sr=sr)
            print(f"  [OK] Yuklendi: {sure:.1f}s, {sr}Hz")
        
    except Exception as e:
        print(f"  [HATA] Dosya yuklenemedi: {e}")
        print("   Desteklenen formatlar: WAV, MP3, FLAC, OGG, M4A")
        return None
    
    rapor = Rapor(
        dosya_adi=os.path.basename(dosya_yolu),
        sure=sure,
        sr=sr
    )
    
    # Analizleri calistir
    analiz_fonksiyonlari = [
        yuksek_frekans_analizi,
        spektral_analiz,
        ritim_analizi,
        harmonik_analiz,
        sureksizlik_analizi,
        watermark_analizi,
        mfcc_analiz,
        fonksiyonel_analiz,
    ]
    
    for fonk in analiz_fonksiyonlari:
        try:
            sonuc = fonk(y, sr)
            rapor.analizler.append(sonuc)
            durum = "[!!]" if sonuc.ai_olasilik > 0.6 else "[~]" if sonuc.ai_olasilik > 0.4 else "[OK]"
            if RICH_AVAILABLE:
                console.print(f"  {durum} {sonuc.isim}: {sonuc.aciklama}")
            else:
                print(f"  {durum} {sonuc.isim}: {sonuc.aciklama}")
        except Exception as e:
            print(f"  [!] {fonk.__name__} hatasi: {e}")
    
    rapor.guncelle()
    return rapor


def rapor_goster(rapor: Rapor):
    """Raporu ekranda goster."""
    
    if RICH_AVAILABLE:
        console = Console()
        
        # Tablo
        tablo = Table(
            title=f"AI Muzik Analiz Raporu - {rapor.dosya_adi}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        tablo.add_column("Analiz", style="cyan", width=25)
        tablo.add_column("Deger", justify="right", width=12)
        tablo.add_column("AI Olasilik", justify="right", width=12)
        tablo.add_column("Aciklama", width=50)
        
        for a in rapor.analizler:
            olasilik_renk = "red" if a.ai_olasilik > 0.6 else "yellow" if a.ai_olasilik > 0.4 else "green"
            tablo.add_row(
                a.isim,
                f"{a.deger:.4f}",
                f"[{olasilik_renk}]{a.ai_olasilik:.0%}[/]",
                a.aciklama
            )
        
        console.print(tablo)
        
        # Sonuc paneli
        if rapor.ai_tahmini:
            sonuc_renk = "red"
            sonuc_metin = "AI TARAFINDAN URETILMIS OLABILIR"
        else:
            sonuc_renk = "green"
            sonuc_metin = "INSAN TARAFINDAN URETILMIS GORUNUYOR"
        
        panel_icerik = f"""
[{sonuc_renk} bold]{sonuc_metin}[/]

[bold]Genel AI Skoru:[/] [{sonuc_renk}]{rapor.genel_skor:.1%}[/]
[bold]Guven Seviyesi:[/] {rapor.guven}
[bold]Dosya:[/] {rapor.dosya_adi}
[bold]Sure:[/] {rapor.sure:.1f} saniye
[bold]Ornekleme Hizi:[/] {rapor.sr} Hz
"""
        
        console.print(Panel(
            panel_icerik,
            title="[bold]SONUC[/]",
            border_style=sonuc_renk,
            padding=(1, 2)
        ))
        
        # Uyari
        console.print("\n[yellow]Not: Bu analiz istatistiksel tahminlerdir, kesin sonuc vermez.[/]")
        console.print("[yellow]   AI muzik teknolojisi surekli gelismektedir.[/]\n")
        
    else:
        # Duz metin ciktisi
        print("\n" + "=" * 70)
        print(f"  AI MUZIK ANALIZ RAPORU - {rapor.dosya_adi}")
        print("=" * 70)
        
        for a in rapor.analizler:
            durum = "[!!]" if a.ai_olasilik > 0.6 else "[~]" if a.ai_olasilik > 0.4 else "[OK]"
            print(f"  {durum} {a.isim:25s} | Olasilik: {a.ai_olasilik:6.0%} | {a.aciklama}")
        
        print("-" * 70)
        
        if rapor.ai_tahmini:
            print(f"\n  >> SONUC: AI TARAFINDAN URETILMIS OLABILIR (Skor: {rapor.genel_skor:.0%})")
        else:
            print(f"\n  >> SONUC: INSAN TARAFINDAN URETILMIS GORUNUYOR (Skor: {rapor.genel_skor:.0%})")
        
        print(f"  Guven: {rapor.guven}")
        print(f"  Sure: {rapor.sure:.1f}s | Ornekleme: {rapor.sr}Hz")
        print("\n  Not: Bu analiz istatistiksel tahminlerdir, kesin sonuc vermez.\n")


def json_rapor_kaydet(rapor: Rapor, cikti_dosyasi: str = None):
    """Raporu JSON olarak kaydet."""
    if cikti_dosyasi is None:
        cikti_dosyasi = rapor.dosya_adi.rsplit('.', 1)[0] + "_analiz.json"
    
    veri = {
        "dosya": rapor.dosya_adi,
        "sure_saniye": round(rapor.sure, 2),
        "ornekleme_hizi": rapor.sr,
        "genel_skor": round(rapor.genel_skor, 4),
        "ai_tahmini": rapor.ai_tahmini,
        "guven": rapor.guven,
        "analizler": [
            {
                "isim": a.isim,
                "deger": round(a.deger, 6),
                "ai_olasilik": round(a.ai_olasilik, 4),
                "aciklama": a.aciklama,
                "agirlik": a.agirlik
            }
            for a in rapor.analizler
        ]
    }
    
    with open(cikti_dosyasi, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    
    print(f"  JSON rapor kaydedildi: {cikti_dosyasi}")


# --- Ana Program ---

def yardim():
    """Yardim mesajini goster."""
    print("""
+------------------------------------------------------------+
|              AI Muzik Tespit Araci                          |
+------------------------------------------------------------+
|                                                              |
|  Kullanim:                                                   |
|    python music.py <muzik_dosyasi>                           |
|    python music.py <dosya> --json                             |
|    python music.py --yardim                                   |
|                                                              |
|  Secenekler:                                                 |
|    --json    Sonuclari JSON dosyasina kaydet                 |
|    --yardim  Bu yardim mesajini gosterir                     |
|                                                              |
|  Desteklenen Formatlar:                                      |
|    WAV, MP3, FLAC, OGG, M4A, AIFF                           |
|                                                              |
|  Gerekli Paketler:                                           |
|    pip install librosa numpy scipy soundfile rich             |
|                                                              |
+------------------------------------------------------------+
""")


def main():
    """Ana fonksiyon."""
    if len(sys.argv) < 2 or "--yardim" in sys.argv or "-h" in sys.argv:
        yardim()
        sys.exit(0)
    
    dosya_yolu = sys.argv[1]
    json_kaydet = "--json" in sys.argv
    
    # Analizi calistir
    rapor = analiz_calistir(dosya_yolu)
    
    if rapor is None:
        sys.exit(1)
    
    # Raporu goster
    rapor_goster(rapor)
    
    # JSON kaydet
    if json_kaydet:
        json_rapor_kaydet(rapor)


if __name__ == "__main__":
    main()
