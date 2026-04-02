import os
import uuid
import asyncio
import logging
from typing import Dict, Optional
from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 引入核心辨識模組
from transcribe_and_translate import MediaSubtitleEngineer

# 日誌設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Subtitle Tool")

# 路徑設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# 任務與日誌管理 (task_id -> info)
TASKS: Dict[str, dict] = {}

async def run_subtitle_task(task_id: str, url: str, model_size: str, lang: Optional[str]):
    TASKS[task_id]["status"] = "running"
    TASKS[task_id]["logs"].append("🚀 啟動任務...")
    
    eng = MediaSubtitleEngineer(OUTPUT_DIR)
    loop = asyncio.get_event_loop()
    
    def log_cb(msg):
        TASKS[task_id]["logs"].append(msg)
        logger.info(f"[{task_id}] {msg}")

    try:
        log_cb(f"正在分析連結: {url}")
        # 下載
        audio_path = await loop.run_in_executor(None, eng.download_audio, url)
        log_cb("✅ 下載完成，開始轉錄...")
        # 轉錄
        segs, d_lang = await loop.run_in_executor(None, eng.transcribe, audio_path, lang, model_size)
        log_cb(f"✅ 辨識完成 (語言: {d_lang})，正在進行翻譯...")
        # 翻譯
        results = await loop.run_in_executor(None, eng.translate_batch, segs, d_lang)
        # 存檔
        out_name = f"{uuid.uuid4().hex[:8]}.srt"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        await loop.run_in_executor(None, eng.save_srt, results, out_path)
        
        if os.path.exists(audio_path): os.remove(audio_path)
        
        TASKS[task_id]["status"] = "done"
        TASKS[task_id]["output_file"] = f"/output/{out_name}"
        log_cb("✨ 全部的任務皆已完成！")
        
    except Exception as e:
        TASKS[task_id]["status"] = "error"
        log_cb(f"❌ 發生錯誤: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/transcribe")
async def start_task(background_tasks: BackgroundTasks, url: str = Form(...), model: str = Form("large-v3"), lang: str = Form(None)):
    tid = str(uuid.uuid4())
    TASKS[tid] = {"status": "pending", "logs": [], "output_file": ""}
    l = lang.strip() if lang and lang.strip() else None
    background_tasks.add_task(run_subtitle_task, tid, url, model, l)
    return {"task_id": tid}

@app.get("/api/logs/{task_id}")
async def stream_logs(task_id: str):
    async def generate():
        last = 0
        while True:
            if task_id not in TASKS: break
            curr = TASKS[task_id]["logs"]
            if len(curr) > last:
                for i in range(last, len(curr)): yield f"data: {curr[i]}\n\n"
                last = len(curr)
            if TASKS[task_id]["status"] in ["done", "error"]:
                if TASKS[task_id]["status"] == "done":
                    yield f"data: COMPLETED:{TASKS[task_id]['output_file']}\n\n"
                break
            await asyncio.sleep(0.8)
    return StreamingResponse(generate(), media_type="text/event-stream")

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
