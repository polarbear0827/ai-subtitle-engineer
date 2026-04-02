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
    from deep_translator import GoogleTranslator, MyMemoryTranslator
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

    def transcribe(
        self,
        audio_path: str,
        lang: Optional[str] = None,
        model_size: str = "large-v3",
        device: str = "auto",
        initial_prompt: Optional[str] = None,
    ):
        """ASR 辨識模組 — 自動偵測 GPU/CPU

        initial_prompt: 給 Whisper 的上下文提示字串，可減少俚語/專有名詞誤辨。
        例如日文：'タチ、ウケ、BL、カプ、推し'
        """
        logger.info(f"🎙️ ASR 開始 (模型: {model_size})...")
        if initial_prompt:
            logger.info(f"📝 initial_prompt: {initial_prompt}")

        attempts = [
            dict(device="auto", compute_type="auto"),
            dict(device="cpu",  compute_type="float32"),
        ]

        last_err = None
        for attempt in attempts:
            try:
                logger.info(f"嘗試: {attempt}")
                model = WhisperModel(model_size, **attempt)
                segments_gen, info = model.transcribe(
                    audio_path,
                    language=lang,
                    beam_size=5,
                    initial_prompt=initial_prompt,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                results = []
                for segment in segments_gen:
                    results.append({"start": segment.start, "end": segment.end, "text": segment.text.strip()})
                logger.info(f"偵測語言: {info.language}")
                return results, info.language
            except Exception as e:
                last_err = e
                logger.warning(f"⚠️ 失敗 ({attempt['device']}): {e}")
                if attempt['device'] == 'cpu':
                    break

        raise RuntimeError(f"無法完成 ASR 辨識。最後錯誤: {last_err}")

    def translate_batch(self, segments: List[Dict], source_lang: str, batch_size: int = 30):
        """翻譯與台灣繁體中文優化（含 retry + fallback）"""
        if source_lang in ['zh', 'zh-TW', 'zh-CN']:
            for s in segments: s['translated'] = convert(s['text'], 'zh-tw')
            return segments

        logger.info("🌍 翻譯處理中 (Google Translate + zhconv)...")

        def _translate_one(text: str, retries: int = 3) -> str:
            """單句翻譯，Google 失敗時指數退避 retry，最終 fallback 到 MyMemory。"""
            last_exc = None
            for i in range(retries):
                try:
                    result = GoogleTranslator(source='auto', target='zh-TW').translate(text)
                    # 504 / 其他 HTTP 錯誤頁面直接當作文字回傳，需要偵測
                    if result and '504' not in result and 'That' not in result:
                        return result
                    raise ValueError(f"Google 回傳錯誤頁面: {result[:60]}")
                except Exception as e:
                    last_exc = e
                    wait = 2 ** i  # 1s, 2s, 4s
                    logger.warning(f"⚠️ Google Translate 第 {i+1} 次失敗: {e}，等待 {wait}s 重試")
                    time.sleep(wait)
            # fallback: MyMemory (免費，500字/段上限)
            try:
                logger.info("↩️ fallback 到 MyMemory Translator")
                result = MyMemoryTranslator(source='auto', target='zh-TW').translate(text[:499])
                return result or text
            except Exception as e:
                logger.error(f"❌ MyMemory 也失敗: {e}")
                return text  # 翻不了就原文保留

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i+batch_size]
            combined = "\n---\n".join([s['text'] for s in batch])
            try:
                translated_bulk = _translate_one(combined)
                parts = [p.strip() for p in translated_bulk.split("\n---\n")]
                if len(parts) == len(batch):
                    for s, t in zip(batch, parts):
                        s['translated'] = convert(t, 'zh-tw')
                else:
                    # 分割數量不符（可能是 Google 合併行），逐句翻
                    logger.warning("⚠️ 批次分割數量不符，改逐句翻譯")
                    for s in batch:
                        s['translated'] = convert(_translate_one(s['text']), 'zh-tw')
            except Exception as e:
                logger.error(f"❌ 批次翻譯失敗: {e}，改逐句")
                for s in batch:
                    s['translated'] = convert(_translate_one(s['text']), 'zh-tw')
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
