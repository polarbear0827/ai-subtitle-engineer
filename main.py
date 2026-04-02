import os, uuid, asyncio, logging, shutil
from typing import Dict, Optional
from fastapi import FastAPI, Request, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from transcribe_and_translate import MediaSubtitleEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Subtitle Tool")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
for d in [OUTPUT_DIR, UPLOAD_DIR]:
    if not os.path.exists(d): os.makedirs(d)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
TASKS: Dict[str, dict] = {}
async def run_task(task_id: str, source: str, model_size: str, lang: Optional[str], is_file: bool = False):
    TASKS[task_id]["status"] = "running"
    eng = MediaSubtitleEngineer(OUTPUT_DIR)
    loop = asyncio.get_event_loop()
    def log_cb(msg):
        TASKS[task_id]["logs"].append(msg); logger.info(f"[{task_id}] {msg}")
    try:
        if is_file:
            log_cb(f"處理檔案: {os.path.basename(source)}")
            audio_path = source
        else:
            log_cb(f"分析網址: {source}")
            audio_path = await loop.run_in_executor(None, eng.download_audio, source)
        log_cb("✅ 音軌分析中，啟動 ASR...")
        segs, d_lang = await loop.run_in_executor(None, eng.transcribe, audio_path, lang, model_size)
        log_cb(f"✅ 辨識完成 ({d_lang})，翻譯中...")
        results = await loop.run_in_executor(None, eng.translate_batch, segs, d_lang)
        out_name = f"{uuid.uuid4().hex[:8]}.srt"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        await loop.run_in_executor(None, eng.save_srt, results, out_path)
        if os.path.exists(audio_path): os.remove(audio_path)
        TASKS[task_id]["status"] = "done"; TASKS[task_id]["output_file"] = f"/output/{out_name}"
        log_cb("✨ 任務完成！")
    except Exception as e:
        TASKS[task_id]["status"] = "error"; log_cb(f"❌ 錯誤: {str(e)}")
@app.get("/", response_class=HTMLResponse)
async def home(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/transcribe")
async def start_url_task(background_tasks: BackgroundTasks, url: str = Form(...), model: str = Form("large-v3"), lang: str = Form(None)):
    tid = str(uuid.uuid4()); TASKS[tid] = {"status": "pending", "logs": [], "output_file": ""}
    background_tasks.add_task(run_task, tid, url, model, lang or None, False)
    return {"task_id": tid}

@app.post("/api/upload")
async def start_file_task(background_tasks: BackgroundTasks, file: UploadFile = File(...), model: str = Form("large-v3"), lang: str = Form(None)):
    tid = str(uuid.uuid4()); TASKS[tid] = {"status": "pending", "logs": [], "output_file": ""}
    tmp_path = os.path.join(UPLOAD_DIR, f"{tid}{os.path.splitext(file.filename)[1]}")
    with open(tmp_path, "wb") as f: shutil.copyfileobj(file.file, f)
    background_tasks.add_task(run_task, tid, tmp_path, model, lang or None, True)
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
                if TASKS[task_id]["status"]=="done": yield f"data: COMPLETED:{TASKS[task_id]['output_file']}\n\n"
                break
            await asyncio.sleep(0.8)
    return StreamingResponse(generate(), media_type="text/event-stream")

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
