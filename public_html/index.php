<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Muzik Tespit Araci</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="index.php" style="color:#00b894;text-decoration:none;margin:0 12px;font-size:0.95em">Muzik Analiz</a>
            <a href="ocr.php" style="color:#8892b0;text-decoration:none;margin:0 12px;font-size:0.95em">OCR Belge Analiz</a>
        </div>

        <div class="header">
            <h1>AI MUZIK TESPIT ARACI</h1>
            <p>Muzik dosyanizi yukleyin, AI mi insanim mi ogrenin</p>
        </div>

        <div class="upload-area" id="dropZone">
            <div class="icon">&#127925;</div>
            <h3>Dosyanizi surukleyip birakin veya tiklayarak secin</h3>
            <p>WAV, MP3, FLAC, OGG, M4A - Maksimum 16MB</p>
            <input type="file" id="fileInput" class="file-input" accept=".wav,.mp3,.flac,.ogg,.m4a,.aiff">
        </div>

        <div class="file-info" id="fileInfo">
            <span class="file-icon">&#127926;</span>
            <span class="name" id="fileName"></span>
            <span class="size" id="fileSize"></span>
            <button class="btn-remove" id="btnRemove" onclick="removeFile()">&#10005;</button>
        </div>

        <button class="btn-analyze" id="analyzeBtn" disabled onclick="analyze()">
            &#9654; ANALIZ ET
        </button>

        <div class="progress-container" id="progress">
            <div class="spinner"></div>
            <p id="progressText">Dosya yukleniyor...</p>
        </div>

        <div class="results" id="results">
            <div class="score-card" id="scoreCard">
                <div class="score-emoji" id="scoreEmoji"></div>
                <div class="score-title" id="scoreTitle"></div>
                <div class="score-subtitle" id="scoreSubtitle"></div>
                <div class="score-circle" id="scoreCircle">
                    <span id="scorePercent"></span>
                </div>
                <div class="guven-badge" id="guvenBadge"></div>
            </div>

            <div class="grid">
                <div class="chart-card">
                    <h3>&#128200; DALGA SEKLI</h3>
                    <canvas id="waveformChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>&#128202; FREKANS SPEKTRUMU</h3>
                    <canvas id="spectrumChart"></canvas>
                </div>
            </div>

            <div id="analysisExplainer"></div>

            <div class="chart-card">
                <h3>&#128269; ANALIZ DETAYLARI</h3>
                <p style="color:#5a6680;font-size:0.85em;margin-bottom:12px">Her analizin ustune gelin, detayli aciklamasini gorun</p>
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
            AI Muzik Tespit Araci v3.0 | Istatistiksel analiz - kesin sonuc vermez
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="js/app.js"></script>
</body>
</html>
