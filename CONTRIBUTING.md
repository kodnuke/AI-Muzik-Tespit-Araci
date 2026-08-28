# 🤝 Katkı Rehberi

AI Müzik Tespit Aracı'na katkıda bulunduğun için teşekkürler! Bu rehber sana yardımcı olacak.

## 🚀 Hızlı Başlangıç

1. Bu repository'yi fork et
2. Fork'nu klonla:
   ```bash
   git clone https://github.com/KULLANICI-ADIN/AI-Muzik-Tespit-Araci.git
   cd AI-Muzik-Tespit-Araci
   ```
3. Virtual environment oluştur ve bağımlılıkları kur:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```
4. Yeni bir dal oluştur:
   ```bash
   git checkout -b ozellik/ozellik-adi
   ```

## 📝 Değişiklik Yapma Kuralları

### Kodlama Tarzı
- Python kodlarında **PEP 8** standartlarına uy
- Değişken ve fonksiyon isimlerini **Türkçe** tut (mevcut kodla tutarlı ol)
- Her fonksiyona **docstring** ekle
- Tip imleri (type hints) kullan

### Commit Mesajları
- Açıklayıcı ve kısa yaz
- Örnek: `feat: yeni spektral analiz metodu eklendi`
- Örnek: `fix: MP3 yükleme hatası düzeltildi`
- Örnek: `docs: README güncellendi`

### Format
- `feat:` → yeni özellik
- `fix:` → hata düzeltme
- `docs:` → dokümantasyon
- `refactor:` → yeniden düzenleme
- `test:` → test ekleme/güncelleme
- `chore:` → bakım işleri

## 🧪 Test Etme

Değişikliklerini test etmeden PR açma:

```bash
# Komut satırı sürümünü test et
python music.py test_audio.wav

# Web arayüzünü test et
python app.py
# Tarayıcında http://localhost:5000 aç

# GUI'yi test et (opsiyonel, desktop gerektirir)
python gui.py
```

## 📋 Pull Request Oluşturma

1. **Branch ismi açıklayıcı olsun:** `ozellik/yeni-analiz-metodu` veya `fix/mp3-yukleme-hatasi`
2. **PR açıklamasında şunları belirt:**
   - Ne yaptın?
   - Neden yaptın?
   - Nasıl test ettin?
3. **Ekran görüntüsü varsa ekle** (GUI değişiklikleri için)
4. **Tek bir konuya odaklan** — birden fazla değişikliği ayrı PR'larda yap

## 🔍 İncelenecek Şeyler

PR'lar şu açılardan incelenecek:

- [ ] Kod çalışır durumda mı?
- [ ] Mevcut fonksiyonları bozuyor mu?
- [ ] Kod tarzı tutarlı mı?
- [ ] Docstring'ler yeterli mi?
- [ ] Gereksiz dosya eklenmemiş mi?

## 🐛 Hata Bildirme

Hata bulursan [GitHub Issues](https://github.com/kodnuke/AI-Muzik-Tespit-Araci/issues) üzerinden bildir. Lütfen şunları ekle:

- **Hatanın açıklaması** — ne olduğunu, ne beklediğini
- **Tekrar adımları** — hatayı nasıl tekrarlayabiliriz
- **Ortam bilgisi** — işletim sistemi, Python versiyonu
- **Hata çıktısı** — varsa terminal çıktısı veya ekran görüntüsü

## 💡 Yeni Özellik Önerileri

Yeni özellik önerileri için [GitHub Discussions](https://github.com/kodnuke/AI-Muzik-Tespit-Araci/discussions) kullanabilirsin veya doğrudan issue açabilirsin.

## 📄 Lisans

Katkıda bulunduğunda, katkıların [MIT Lisansı](LICENSE) altında yayınlanacağını kabul edersin.

## 🙋 Soruların mı var?

Herhangi bir sorun varsa GitHub Issues üzerinden çekinmeden sor!

---

Teşekkürler! 🎵
