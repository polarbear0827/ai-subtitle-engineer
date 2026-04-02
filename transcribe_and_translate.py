import os
import sys
import argparse
import time
import logging
import re
from typing import List, Optional, Dict
from datetime import timedelta

# 第三方庫檢測
try:
    import yt_dlp
    from faster_whisper import WhisperModel
    from deep_translator import GoogleTranslator
    from zhconv import convert
except ImportError as e:
    print(f"❌ 缺少必要套件: {e.name}. 請先執行 'pip install -r requirements.txt'")
    sys.exit(1)

# 設定 Logging (繁體中文)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class MediaSubtitleEngineer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def download_audio(self, url: str, cookie_path: Optional[str] = None) -> str:
        """影片下載與音軌提取"""
        logger.info(f"🚀 下載連結: {url}")
        output_tmpl = os.path.join(self.output_dir, '%(title)s.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_tmpl,
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        
        if cookie_path and os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
            
        logger.info(f"✅ 下載完成: {audio_path}")
        return audio_path

    def transcribe(self, audio_path: str, lang: Optional[str] = None, model_size: str = "large-v3", device: str = "auto"):
        """ASR 辨識模組 — 自動偵測 GPU/CPU"""
        logger.info(f"🎙️ ASR 開始 (模型: {model_size})...")

        model = None
        # 嘗試順序: auto(GPU優先) -> CPU float32
        attempts = [
            dict(device="auto", compute_type="auto"),
            dict(device="cpu",  compute_type="float32"),
        ]
        last_err = None
        for attempt in attempts:
            try:
                logger.info(f"嘗試載入模型: {attempt}")
                model = WhisperModel(model_size, **attempt)
                break
            except Exception as e:
                last_err = e
                logger.warning(f"⚠️ 模型載入失敗 ({attempt}): {e}")

        if model is None:
            raise RuntimeError(f"無法載入 Whisper 模型，所有嘗試均失敗。最後錯誤: {last_err}")

        segments, info = model.transcribe(
            audio_path, language=lang, beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        logger.info(f"偵測語言: {info.language}")
        results = []
        for segment in segments:
            results.append({"start": segment.start, "end": segment.end, "text": segment.text.strip()})
        return results, info.language

    def translate_batch(self, segments: List[Dict], source_lang: str, batch_size: int = 30):
        """翻譯與台灣繁體中文優化"""
        if source_lang in ['zh', 'zh-TW', 'zh-CN']:
            for s in segments: s['translated'] = convert(s['text'], 'zh-tw')
            return segments

        logger.info("🌍 翻譯處理中 (Google Translate + zhconv)...")
        translator = GoogleTranslator(source='auto', target='zh-TW')
        
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i+batch_size]
            combined = "\n---\n".join([s['text'] for s in batch])
            try:
                translated_bulk = translator.translate(combined)
                parts = [p.strip() for p in translated_bulk.split("\n---\n")]
                for s, t in zip(batch, parts):
                    s['translated'] = convert(t, 'zh-tw')
            except:
                for s in batch: s['translated'] = convert(translator.translate(s['text']), 'zh-tw')
        return segments

    def save_srt(self, segments: List[Dict], output_file: str):
        """匯出雙語 SRT"""
        def ts(s: float):
            td = timedelta(seconds=s)
            return f"{int(td.total_seconds()//3600):02}:{int((td.total_seconds()%3600)//60):02}:{int(td.total_seconds()%60):02},{int(td.microseconds/1000):03}"

        with open(output_file, 'w', encoding='utf-8') as f:
            for i, s in enumerate(segments, 1):
                f.write(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n{s.get('translated','')}\n\n")
        logger.info(f"📂 字幕已匯出: {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--output", default="final.srt")
    parser.add_argument("--cookies", default=None)
    parser.add_argument("--model", default="large-v3")
    args = parser.parse_args()

    tool = MediaSubtitleEngineer()
    try:
        audio = tool.download_audio(args.url, args.cookies)
        segs, d_lang = tool.transcribe(audio, lang=args.lang, model_size=args.model)
        results = tool.translate_batch(segs, d_lang)
        tool.save_srt(results, args.output)
        if os.path.exists(audio): os.remove(audio)
        print(f"\n✅ 成功！輸出檔案：{args.output}")
    except Exception as e:
        logger.error(f"💥 發生錯誤: {e}")

if __name__ == "__main__":
    main()
