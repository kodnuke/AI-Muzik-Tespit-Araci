# 🎵 AI Müzik Tespit Aracı

Müzik dosyalarının **yapay zeka tarafından üretilip üretilmediğini** istatistiksel ses analizleri ile tespit eden açık kaynaklı araç.

> ⚠️ **Uyarı:** Bu araç istatistiksel analizlere dayanır ve kesin sonuç vermez. AI müziğin hızla geliştiği göz önünde bulundurulmalıdır.

## 📸 Özellikler

- 🔍 **8 Farklı Analiz Metodu** — Yüksek frekans, spektral, ritimik, harmonik, dinamik, watermark, MFCC ve kontrast analizleri
- 🖥️ **3 Kullanım Modu** — Komut satırı (CLI), masaüstü GUI (Tkinter) ve web arayüzü (Flask)
- 📊 **Görsel Grafikler** — Dalga şekli (waveform) ve frekans spektrumu grafikleri
- 🎯 **Ağırlıklı Skorlama** — Her analizin güvenilirliğine göre ağırlıklandırılmış genel skor
- 🌐 **Web Deploy** — PythonAnywhere ve PHP sunucu desteği
- 📦 **PyInstaller Desteği** — Tek dosya olarak paketleme imkanı

## 🚀 Kurulum

### Gereksinimler

- Python 3.9+
- pip

### Bağımlılıkları Yükleme

```bash
pip install -r requirements.txt
```

Veya tek tek:

```bash
pip install librosa numpy scipy flask flask-cors matplotlib soundfile rich
```

## 📖 Kullanım

### 1. Komut Satırı (CLI)

```bash
python music.py dosyaadi.wav
```

Örnek çıktı:

```
╔══════════════════════════════════════════════════╗
║         AI MÜZİK TESPİT ARACI RAPORU            ║
╠══════════════════════════════════════════════════╣
║ Dosya: ornek_sarki.mp3                          ║
║ Süre:  214.50 saniye                            ║
║ Örnekleme: 22050 Hz                             ║
╠══════════════════════════════════════════════════╣
║ Genel AI Skoru: %42.5                           ║
║ Tahmin: İNSAN TARAFINDAN ÜRETİLMİŞ             ║
║ Güven: Orta                                     ║
╚══════════════════════════════════════════════════╝
```

### 2. Masaüstü GUI

```bash
python gui.py
```

Dosya seçip "Analiz Et" butonuna tıklayın. Grafikler ve detaylı sonuçlar otomatik gösterilir.

### 3. Web Arayüzü

```bash
python app.py
```

Tarayıcınızda açın: **http://localhost:5000**

Sürükle-bırak ile dosya yükleyebilir, anında sonuç alabilirsiniz.

## 🔬 Analiz Metotları

| Analiz | Açıklama | Ağırlık |
|--------|----------|---------|
| **Yüksek Frekans** | 16kHz+ enerji oranını inceler | 1.5 |
| **Spektral Kalite** | Spectral flatness, centroid, bandwidth | 2.0 |
| **Ritim & Dynamics** | Beat düzenliliği ve RMS değişimleri | 1.5 |
| **Harmonik Yapı** | Harmonik-percussive ayrımı ve chroma entropisi | 1.5 |
| **Süreksizlik** | Enerji değişim hızı ve zero-crossing rate | 1.0 |
| **Watermark** | 19-20kHz arası watermark tespiti | 1.5 |
| **MFCC Timbre** | MFCC katsayılarının değişim katsayısı | 1.0 |
| **Spektral Kontrast** | Spectral rolloff ve kontrast standart sapması | 1.0 |

## 📁 Proje Yapısı

```
ai-muzik-tespit/
├── music.py              # Komut satırı sürümü
├── gui.py                # Masaüstü GUI (Tkinter)
├── app.py                # Web arayüzü (Flask)
├── requirements.txt      # Python bağımlılıkları
├── KURULUM_TALIMATLARI.txt  # Detaylı kurulum rehberi
├── public_html/          # PHP web frontend
│   ├── index.php
│   ├── css/style.css
│   └── js/app.js
└── pythonanywhere/       # PythonAnywhere deploy dosyaları
    ├── app.py
    └── flask_app.py
```

## 🌐 Web Deploy

Detaylı kurulum adımları için [KURULUM_TALIMATLARI.txt](KURULUM_TALIMATLARI.txt) dosyasına bakın.

Kısaca:
1. PythonAnywhere'da Flask uygulaması oluşturun
2. `pythonanywhere/flask_app.py` dosyasını yükleyin
3. Bağımlılıkları pip ile kurun
4. `public_html/` dosyalarını PHP sunucunuza yükleyin
5. `js/app.js` içindeki `API_URL` adresini güncelleyin

## 🛠️ PyInstaller ile Paketleme

```bash
# GUI sürümü (tek dosya)
pyinstaller AI_Muzik_Tespit_GUI.spec

# Konsol sürümü
pyinstaller AI_Muzik_Tespit_Konsol.spec
```

## 🤝 Katkıda Bulunma

Katılımlarınız hoș geldiniz! Şu adımları izleyin:

1. Bu projeyi fork edin
2. Yeni bir dal oluşturun (`git checkout -b ozellik/yerin-adi`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Push edin (`git push origin ozellik/yerin-adi`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında yayınlanmıştır.

## ⚡ Teknik Detaylar

- **Örnekleme:** Tüm dosyalar 22050 Hz'e downsample edilir
- **Analiz penceresi:** 2048 örnek, 512 örnek kayma (hop length)
- **Frekans analizi:** FFT tabanlı, 0-22kHz aralığı
- **Skor hesaplama:** Ağırlıklı ortalama, %50 eşiği

## 📬 İletişim

Sorularınız veya önerileriniz için GitHub Issues üzerinden ulaşabilirsiniz.

---

*AI Müzik Tespit Aracı v3.0 — İstatistiksel analiz ile müzik kaynaklarını keşfedin* 🎵
