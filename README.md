# 🎬 AI Subtitle Engineer | 專業雙模字幕轉錄工具

這是一個結合 OpenAI Whisper 與自動翻譯技術的媒體工程工具，現已全面支援「網址模式」與「本地上傳模式」。

## ✨ 功能特色
- **🔗 網址轉錄**: 支持 YouTube, X, Facebook, Instagram 等平台。
- **📁 檔案轉錄**: 直接上傳本地影片 (MP4, MKV, MOV 等) 進行 ASR。
- **🚀 GPU 加速**: 利用 NVIDIA CUDA 進行快速轉錄，支援 large-v3 模型。
- **🇹🇼 台灣在地化**: 自動翻譯並修正為台灣繁體中文口語格式。
- **🎨 玻璃擬態 UI**: 提供極致視覺體驗與即時進度監控。

## 🛠️ 快速上手
`ash
# 安裝
pip install -r requirements.txt

# 啟動網頁
python main.py
`
存取 http://localhost:8000 即可使用。

## �� Docker 支持
`ash
docker build -t ai-subtitle-engineer .
docker run --gpus all -p 8000:8000 ai-subtitle-engineer
`

## 🤖 GitHub Actions
本專案已配置 CI 流程，每次推送將自動檢查代碼品質與核心翻譯邏輯。
