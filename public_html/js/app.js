/**
 * AI Muzik Tespit Araci - Web Client
 * 
 * Bu dosya public_html/js/ altina yerlestirilir.
 * API_URL'i kendi PythonAnywhere URL'niz ile degistirin.
 */

// ============================================================
// KONFIGURASYON - BURAYI DEGISTIRIN!
// ============================================================
const API_URL = 'https://kodnuke.pythonanywhere.com/api/analyze';

// ============================================================
// ANALIZ ACIKLAMALARI - Bilmeyenler icin
// ============================================================
const ANALIZ_ACIKLAMALARI = {
    'Yuksek Frekans': {
        baslik: 'Yuksek Frekans Analizi',
        kisa: 'Sesin yuksek frekanslardaki enerjisini olcer',
        uzun: 'Insan kulaqi yuksek frekanslari duyamaz ama AI muziklerde yuksek frekanslarda cok temiz, dogal olmayan enerji bulunur. Eger 16kHz ustunde cok fazla enerji varsa, bu AI uretimine isaret edebilir. Dogal muziklerde bu bolge genelde daha sessizdir.',
        ipucu: 'Dusuk degerler = daha dogal (insan), yuksek degerler = daha yapay (AI)'
    },
    'Spektral Kalite': {
        baslik: 'Spektral Kalite Analizi',
        kisa: 'Sesin genel kalitesini ve duzgunlugunu olcer',
        uzun: 'Sesin frekans dagiliminin ne kadar "duz" oldugunu gosterir. AI muzikler genellikle cok duzgun ve temiz spektruma sahiptir. Insan muziklerinde dogal dalgalanmalar, gurultu ve kusurlar bulunur. Flatness degeri dusukse (0.01 altinda) AI olasiligi yuksektir.',
        ipucu: 'Flatness dusuk = cok temiz ses (AI olabilir), yuksek = gurultulu/dogal ses (insan)'
    },
    'Ritim & Dynamics': {
        baslik: 'Ritim ve Dinamik Analizi',
        kisa: 'Tempo duzgunlugunu ve sesin guc degisimlerini olcer',
        uzun: 'AI muziklerde tempo cok duzgundur - her beat neredeyse ayni aralikla gelir. Insan muziklerinde ritimde kucuk dalgalanmalar olur (bu da muzige "ruh" katar). Ayrica sesin yukseklik dusukluk degisimleri (dynamics) de onemlidir. Cok duzgun dinamikler AI isareti olabilir.',
        ipucu: 'CV degeri dusuk = cok duzgun ritim (AI), yuksek = dogal dalgalanma (insan)'
    },
    'Harmonik Yapi': {
        baslik: 'Harmonik Yapi Analizi',
        kisa: 'Sesin tını ve harmonik dengesini olcer',
        uzun: 'Her sesin kendine ozel harmonik yapis vardir. AI muziklerde harmonikler cok simetrik ve "mukemmel" olabilir. Insan muziklerinde harmonikler daha kaotik ve cesitlidir. HPSS analizi ile sesin harmonik ve perkusif ayrimi yapilir. Entropi dusukse (1.5 altinda) yapaylik isareti olabilir.',
        ipucu: 'Harmonik oran yuksek = cok temiz ses (AI), entropi dusuk = cesitlilik az (AI)'
    },
    'Sureksizlik': {
        baslik: 'Sureksizlik Analizi',
        kisa: 'Sesin zaman icindeki degisim hizini olcer',
        uzun: 'Sesin zamanla ne kadar hizli degistigini gosterir. AI muziklerde ses genellikle yavas ve kademeli degisir. Insan muziklerinde ani degisimler, keskin gecisler ve dinamik patlamalar olur. Enerji degisimi cok dusukse (0.005 altinda) AI olasiligi yuksektir.',
        ipucu: 'Degisim dusuk = yavas/degisken olmayan ses (AI), yuksek = dinamik/dogal (insan)'
    },
    'Watermark': {
        baslik: 'Watermark Tarama',
        kisa: 'Sesin icindeki gizli AI imzasini arar',
        uzun: 'Bazi AI muzik ureticileri (Suno, Udio vb.) urettikleri sese 19-20kHz araliginda gizli bir "imza" veya watermark koyar. Bu bolge insan kulaqi tarafindan duyulamaz ama teknik olarak tespit edilebilir. Eger bu bolgede olağanustu enerji varsa, o sarkin AI ile uretilmis olma ihtimali cok yuksektir.',
        ipucu: 'Enerji var = AI watermark tespit edildi (cok guclu isaret), yok = normal'
    },
    'MFCC Tini': {
        baslik: 'MFCC Tini Profili',
        kisa: 'Sesin tini ozelliklerini analiz eder',
        uzun: 'MFCC (Mel-Frequency Cepstral Coefficients) sesin "rengi"ni temsil eden 13 sayidir. Insan konusmasi ve muzikte bu degerler cesitli ve degisken olur. AI muziklerde MFCC degerleri daha tekdüze ve az degisken olma egilimindedir. CV (katsayi degiskenligi) dusukse AI olasiligi yuksektir.',
        ipucu: 'CV dusuk = tini cok tekdüze (AI), yuksek = tini cesitli (insan)'
    },
    'Spektral Kontrast': {
        baslik: 'Spektral Kontrast Analizi',
        kisa: 'Frekanslar arasi farkliligi olcer',
        uzun: 'Sesin farkli frekans bantlari arasindaki farkliligi gosterir. Insan muziklerinde belirli frekans bantlari digerlerinden cok daha guclu olabilir (kontrast yuksek). AI muziklerde ise frekans dagilimi daha esit ve kontrast daha dusuk olma egilimindedir. Rolloff degeri de yuksek frekans enerji dagilimini gosterir.',
        ipucu: 'Kontrast dusuk = frekanslar esit (AI), yuksek = belirgin farkliliklar (insan)'
    }
};

const SKOR_YORUMLARI = [
    { max: 25, emoji: '🎵', renk: '#00b894', baslik: 'INSAN YAPIMI', aciklama: 'Bu muzik buyuk olcude ins tarafindan yapilmis gorunuyor. Dogal dalgalanmalar, cesitlilik ve kusurlar var.' },
    { max: 40, emoji: '🎶', renk: '#00b894', baslik: 'MUINEMELE INSAN', aciklama: 'Bu muzik insana ait gibi duruyor ama bazi ozellikleri AI ile benziyor. Belki AI araclarla duzenlenmis olabilir.' },
    { max: 55, emoji: '🤔', renk: '#fdcb6e', baslik: 'BELIRSIZ', aciklama: 'Bu muzik hem insani hem AI ozellikleri tasiyor. Kesin karar vermek zor. Belki insan-AI isbirligi ile yapilmis olabilir.' },
    { max: 70, emoji: '🤖', renk: '#fdcb6e', baslik: 'AI OLABILIR', aciklama: 'Bu muzikte belirgin yapay ozellikler var. AI ile uretilmis veya cok agir sekilde AI ile duzenlenmis olabilir.' },
    { max: 100, emoji: '🤖', renk: '#e94560', baslik: 'AI TARAFINDAN URETILMIS', aciklama: 'Bu muzik buyuk olcude AI tarafindan uretilmis. Cok temiz, cok duzgun ve dogal olmayan ozellikler tespit edildi.' }
];
// Ornek: const API_URL = 'https://ahmet.pythonanywhere.com/api/analyze';

// ============================================================
// DEGISKENLER
// ============================================================
let selectedFile = null;
let waveformChart = null;
let spectrumChart = null;

// ============================================================
// DOSYA YUKLEME
// ============================================================
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

// Drag & Drop events
['dragenter', 'dragover'].forEach(e => {
    dropZone.addEventListener(e, (ev) => {
        ev.preventDefault();
        dropZone.classList.add('dragover');
    });
});

['dragleave', 'drop'].forEach(e => {
    dropZone.addEventListener(e, (ev) => {
        ev.preventDefault();
        dropZone.classList.remove('dragover');
    });
});

dropZone.addEventListener('drop', (ev) => {
    const files = ev.dataTransfer.files;
    if (files.length) handleFile(files[0]);
});

fileInput.addEventListener('change', (ev) => {
    if (ev.target.files.length) handleFile(ev.target.files[0]);
});

function handleFile(file) {
    // Format kontrol
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = ['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aiff', 'aif'];

    if (!allowed.includes(ext)) {
        showError('Desteklenmeyen dosya formati: .' + ext);
        return;
    }

    // Boyut kontrol (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showError('Dosya cok buyuk! Maksimum 16MB olmali.');
        return;
    }

    selectedFile = file;
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatSize(file.size);
    document.getElementById('fileInfo').classList.add('show');
    document.getElementById('analyzeBtn').disabled = false;
    hideError();
}

function removeFile() {
    selectedFile = null;
    fileInput.value = '';
    document.getElementById('fileInfo').classList.remove('show');
    document.getElementById('analyzeBtn').disabled = true;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ============================================================
// ANALIZ
// ============================================================
async function analyze() {
    if (!selectedFile) return;

    const btn = document.getElementById('analyzeBtn');
    const progress = document.getElementById('progress');
    const progressText = document.getElementById('progressText');
    const results = document.getElementById('results');

    btn.disabled = true;
    progress.classList.add('show');
    results.classList.remove('show');
    hideError();

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        progressText.textContent = 'Dosya yukleniyor...';

        const resp = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        progressText.textContent = 'Analiz ediliyor...';

        const data = await resp.json();

        if (data.error) {
            showError('Hata: ' + data.error);
            return;
        }

        displayResults(data);

    } catch (err) {
        showError('Sunucu baglanti hatasi: ' + err.message + '\n\nAPI_URL: ' + API_URL);
    } finally {
        progress.classList.remove('show');
        btn.disabled = false;
    }
}

// ============================================================
// SONUCLARI GOSTER
// ============================================================
function displayResults(data) {
    const isAi = data.ai_tahmini;
    const skor = (data.genel_skor * 100).toFixed(1);

    // Score Card
    const card = document.getElementById('scoreCard');
    card.className = 'score-card ' + (isAi ? 'ai' : 'human');

    document.getElementById('scoreEmoji').innerHTML = isAi ? '&#129302;' : '&#127925;';

    const title = document.getElementById('scoreTitle');
    title.textContent = isAi ? 'AI TARAFINDAN URETILMIS OLABILIR' : 'INSAN TARAFINDAN URETILMIS GORUNUYOR';
    title.className = 'score-title ' + (isAi ? 'ai' : 'human');

    document.getElementById('scoreSubtitle').textContent =
        `${data.dosya_adi} | ${data.sure}s | ${data.sr}Hz`;

    const circle = document.getElementById('scoreCircle');
    circle.style.setProperty('--pct', skor + '%');
    circle.className = 'score-circle ' + (isAi ? 'ai' : 'human');
    document.getElementById('scorePercent').textContent = '%' + skor;

    const badge = document.getElementById('guvenBadge');
    badge.textContent = 'Guven: ' + data.guven;
    badge.className = 'guven-badge guven-' + data.guven;

    // Grafikler
    drawWaveform(data.waveform);
    drawSpectrum(data.spectrum);

    // Skor yorumu
    const yorum = SKOR_YORUMLARI.find(y => skor <= y.max) || SKOR_YORUMLARI[SKOR_YORUMLARI.length - 1];

    // Aciklama kutusu
    const aciklamaBox = document.getElementById('analysisExplainer');
    if (aciklamaBox) {
        aciklamaBox.innerHTML = `
            <div style="background:rgba(255,255,255,0.03);border:1px solid #2d3748;border-radius:12px;padding:20px;margin-bottom:20px">
                <h3 style="color:${yorum.renk};margin-bottom:10px;font-size:1.1em">${yorum.emoji} ${yorum.baslik} - %${skor}</h3>
                <p style="color:#8892b0;line-height:1.7;font-size:0.95em;margin-bottom:15px">${yorum.aciklama}</p>
                <details style="color:#5a6680;font-size:0.88em">
                    <summary style="cursor:pointer;color:#74b9ff;margin-bottom:8px">Nasil calisiyor? (Teknik detay)</summary>
                    <p style="line-height:1.7;margin-top:8px">Program ${data.analizler.length} farkli yontemle muzigi analiz eder. Her yontem 0-100 arasinda bir AI olasilik skoru verir. Sonra bu skorlar agirlikli ortalama ile birlestirilir. Dusuk skorlar muzigin insani ozellikler tasidigini, yuksek skorlar AI ile uretilmis olabilecegini gosterir.</p>
                </details>
            </div>
        `;
    }

    // Tablo
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

        const aciklama = ANALIZ_ACIKLAMALARI[a.isim];
        const tooltipText = aciklama ? aciklama.uzun : a.aciklama;
        const kisaAciklama = aciklama ? aciklama.kisa : '';

        tbody.innerHTML += `
            <tr class="analiz-row" onmouseover="showTooltip(this, '${a.isim}')" onmouseout="hideTooltip()">
                <td>
                    <strong>${a.isim}</strong><br>
                    <small style="color:#8892b0">${a.kategori}</small>
                    ${kisaAciklama ? `<br><small style="color:#5a6680;font-style:italic;font-size:0.82em">${kisaAciklama}</small>` : ''}
                </td>
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

    // Tooltip kutusu ekle
    if (!document.getElementById('analizTooltip')) {
        const tooltip = document.createElement('div');
        tooltip.id = 'analizTooltip';
        tooltip.style.cssText = 'display:none;position:fixed;z-index:1000;background:rgba(22,33,62,0.97);border:1px solid #2d3748;border-radius:12px;padding:18px;max-width:420px;box-shadow:0 12px 40px rgba(0,0,0,0.5);pointer-events:none';
        document.body.appendChild(tooltip);
    }

    document.getElementById('results').classList.add('show');
}

// Tooltip fonksiyonlari
window.showTooltip = function(row, analizIsmi) {
    const aciklama = ANALIZ_ACIKLAMALARI[analizIsmi];
    if (!aciklama) return;
    
    const tooltip = document.getElementById('analizTooltip');
    tooltip.innerHTML = `
        <div style="font-weight:700;color:#00b894;margin-bottom:8px;font-size:1em">${aciklama.baslik}</div>
        <div style="color:#e0e0e0;font-size:0.9em;line-height:1.7;margin-bottom:10px">${aciklama.uzun}</div>
        <div style="color:#fdcb6e;font-size:0.82em;border-top:1px solid #2d3748;padding-top:8px">💡 ${aciklama.ipucu}</div>
    `;
    tooltip.style.display = 'block';
    
    const rect = row.getBoundingClientRect();
    let left = rect.right + 10;
    let top = rect.top;
    
    if (left + 420 > window.innerWidth) {
        left = rect.left - 430;
    }
    if (left < 10) left = 10;
    if (top + 200 > window.innerHeight) {
        top = window.innerHeight - 220;
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
};

window.hideTooltip = function() {
    const tooltip = document.getElementById('analizTooltip');
    if (tooltip) tooltip.style.display = 'none';
};

// ============================================================
// GRAFIKLER
// ============================================================
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

// ============================================================
// YARDIMCI
// ============================================================
function showError(msg) {
    let el = document.querySelector('.error-msg');
    if (!el) {
        el = document.createElement('div');
        el.className = 'error-msg';
        document.querySelector('.upload-area').after(el);
    }
    el.textContent = msg;
    el.classList.add('show');
}

function hideError() {
    const el = document.querySelector('.error-msg');
    if (el) el.classList.remove('show');
}
