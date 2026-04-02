<p align="center">
  <img src="assets/banner.png" width="800" alt="AI Subtitle Engineer Banner">
</p>

<h1 align="center">🎬 AI Subtitle Engineer</h1>
<p align="center">旗艦級影片字幕自動化工具｜GPU 加速｜雙語 SRT 輸出</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://developer.nvidia.com/cuda-zone"><img src="https://img.shields.io/badge/GPU-CUDA%2012%20Accelerated-76b900.svg" alt="CUDA 12"></a>
  <a href="https://github.com/SYSTRAN/faster-whisper"><img src="https://img.shields.io/badge/ASR-faster--whisper%20large--v3-purple.svg" alt="Faster Whisper"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
</p>

---

## ✨ 核心特色

| 功能 | 說明 |
|---|---|
| 🤖 **GPU 加速 ASR** | Faster-Whisper large-v3，自動偵測 GPU/CPU，Windows 免裝 CUDA Toolkit |
| 🌐 **多平台下載** | YouTube、X (Twitter)、Facebook、Instagram 等 yt-dlp 支援的所有平台 |
| 📁 **本地檔案上傳** | 直接拖放影片上傳，無需網址 |
| 🎯 **語境提示 (initial_prompt)** | 輸入俚語/專有名詞提示，大幅提升 Whisper 辨識精準度 |
| 🌍 **台灣繁體中文翻譯** | Google Translate + 指數退避 retry + MyMemory fallback，不怕 504 斷線 |
| 📝 **雙語 SRT 輸出** | 原文 + 台灣繁體中文對照，直接用於剪輯軟體 |
| 🔄 **SSE 即時日誌** | 網頁端即時顯示 ASR 進度，不需手動 refresh |

---

## 🖥️ Web UI 預覽

- **玻璃擬態設計**：深色漸層 + 毛玻璃效果
- **雙模式切換**：🔗 網址模式 ／ 📁 檔案模式
- **語境提示欄**：輸入關鍵詞提示 Whisper（例：`タチ、ウケ、BL、推し`）

---

## 🛠️ 安裝與啟動

### 環境需求

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html)（需加入 PATH）
- NVIDIA GPU（選用，沒有 GPU 自動 fallback 到 CPU）

### 安裝依賴

```bash
pip install -r requirements.txt
```

> **Windows GPU 用戶注意**：本工具已內建自動掛載 CUDA 12 DLL 路徑，  
> **不需要**另外安裝 CUDA Toolkit，`pip install` 即可享受 GPU 加速。

### 啟動服務

#### 🐳 Docker（推薦，GPU 支援）

```bash
docker build -t ai-subtitle-engineer .
docker run --gpus all -p 8000:8000 ai-subtitle-engineer
```

#### 💻 本地 Python

```bash
python main.py
```

開啟瀏覽器前往 **http://localhost:8000**

---

## 🕹️ CLI 模式

也可以直接用命令列執行（不啟動 Web 服務）：

```bash
python transcribe_and_translate.py \
  --url "https://www.youtube.com/watch?v=..." \
  --model large-v3 \
  --lang ja \
  --output output.srt
```

| 參數 | 說明 | 預設值 |
|---|---|---|
| `--url` | 影片網址（YouTube、X、IG 等） | 必填 |
| `--model` | Whisper 模型規格 | `large-v3` |
| `--lang` | 原始語系（`en`、`ja`、`zh`...） | 自動偵測 |
| `--output` | 輸出 SRT 檔名 | `final.srt` |
| `--cookies` | cookies.txt 路徑（私人影片用） | 無 |

---

## 🔧 技術架構

```
main.py                    ← FastAPI Web Server + SSE 日誌推送
transcribe_and_translate.py ← 核心引擎
  ├── download_audio()     ← yt-dlp 音軌提取
  ├── transcribe()         ← Faster-Whisper ASR（GPU auto-fallback）
  ├── translate_batch()    ← Google Translate + retry + MyMemory fallback
  └── save_srt()          ← 雙語 SRT 輸出
```

### GPU 加速原理（Windows）

Windows 上 ctranslate2 需要 `cublas64_12.dll`，本工具在啟動時自動從  
`nvidia-cublas-cu12` / `nvidia-cudnn-cu12` pip 套件中載入 DLL，  
無需手動安裝 CUDA Toolkit。

### 翻譯 Retry 機制

```
Google Translate → 失敗(1s) → 重試 → 失敗(2s) → 重試 → 失敗(4s)
    → fallback MyMemory → 失敗 → 保留原文
```

---

## 📦 依賴套件

| 套件 | 用途 |
|---|---|
| `faster-whisper` | GPU 加速語音辨識 |
| `yt-dlp` | 多平台影片下載 |
| `deep-translator` | Google + MyMemory 翻譯 |
| `zhconv` | 繁簡轉換＋台灣用語校正 |
| `fastapi` + `uvicorn` | Web API 服務 |
| `nvidia-cublas-cu12` | CUDA 12 cuBLAS DLL（Windows GPU） |
| `nvidia-cudnn-cu12` | CUDA 12 cuDNN DLL（Windows GPU） |

---

## ⚠️ 注意事項

- 翻譯使用 Google Translate 非官方介面，存在速率限制。高頻使用建議改串 Google Cloud Translation API。
- Instagram/Facebook 私人內容需提供 cookies.txt（CLI `--cookies` 參數）。
- `output/` 與 `uploads/` 目錄已加入 `.gitignore`，不會上傳使用者資料。

---

*Built with [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) · Powered by Antigravity*