# 🎬 自動化影片字幕提取與翻譯工具 (AI Subtitle Engineer)

[![CI](https://github.com/USER/subtitles/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/subtitles/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

這是一個專為高效能、高品質設計的自動化工具。支援從多個平台 (YouTube, X, Instagram, Facebook) 下載影片，利用 `Faster-Whisper` ASR 硬體加速進行語音辨識，並將結果翻譯為 **台灣繁體中文口語** 的雙語 SRT 字幕。

## ✨ 功能亮點
- **🚀 極速辨識**: 基於 `Faster-Whisper` 並針對 NVIDIA GPU (CUDA) 開啟 `int8_float16` 量化。
- **🌐 多平台支援**: 整合 `yt-dlp` 下載技術，處理各類 User-Agent 與 Cookie。
- **🇹🇼 台灣口語優化**: 自動透過 `zhconv` 修正大陸用語為台灣慣用語 (如: 軟體 -> 軟體)。
- **📂 雙語輸出**: 直接產出符合專業標準的雙語對照 SRT 字幕。
- **🎨 現代 Web UI**: 提供精美的玻璃擬態 (Glassmorphism) 網頁介面。

## 🛠️ 安裝與安裝
請確保系統已安裝 `ffmpeg`。

```bash
# 複製專案
git clone https://github.com/YourUsername/subtitle-tool.git
cd subtitle-tool

# 安裝依賴
pip install -r requirements.txt
```

## 🚀 執行與使用
### 1. 網頁版 (推薦)
```bash
python main.py
```
啟動後開啟瀏覽器訪問 `http://localhost:8000`。

### 2. 命令行版 (CLI)
```bash
python transcribe_and_translate.py --url "影片網址" --output "字幕名稱.srt"
```

## 🐳 Docker 部署 (GPU 支援)
```bash
docker build -t subtitle-tool .
docker run --gpus all -p 8000:8000 subtitle-tool
```

## 📜 授權條款
MIT License.
