import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from faster_whisper import WhisperModel
from docx import Document

# -----------------------------
# App setup
# -----------------------------
app = FastAPI(title="Nova Transcribe (Faster-Whisper)")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -----------------------------
# Model
# -----------------------------
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "tiny")
# device="cpu" for free hosting; compute_type="int8" saves memory
MODEL = WhisperModel(DEFAULT_MODEL, device="cpu", compute_type="int8")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
async def health():
    return {"ok": True, "model": DEFAULT_MODEL}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "default_model": DEFAULT_MODEL}
    )

@app.post("/api/transcribe")
async def transcribe_api(
    file: UploadFile,
    model_size: str = Form(DEFAULT_MODEL),
    beam_size: int = Form(5),
    word_timestamps: Optional[bool] = Form(False)
):
    global MODEL

    base_name = os.path.splitext(file.filename or "audio")[0]
    ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    uid = uuid.uuid4().hex[:8]
    input_path = os.path.join(OUTPUT_DIR, f"{base_name}_{uid}{ext}")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    # reload model if user requested a different size
    current_model = DEFAULT_MODEL
    if model_size and model_size != current_model:
        try:
            MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
            current_model = model_size
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Failed to load model '{model_size}': {e}"})

    try:
        segments, info = MODEL.transcribe(input_path, beam_size=beam_size, word_timestamps=bool(word_timestamps))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Transcription failed: {e}"})

    text = " ".join([seg.text for seg in segments]).strip()
    language = info.language if hasattr(info, "language") else None
    duration = info.duration if hasattr(info, "duration") else None

    # Save as DOCX
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    docx_name = f"{base_name}_{ts}.docx"
    docx_path = os.path.join(OUTPUT_DIR, docx_name)

    doc = Document()
    doc.add_heading("Transcription", level=1)
    meta = doc.add_paragraph()
    meta.add_run("Source: ").bold = True
    meta.add_run(file.filename or "Uploaded file")
    meta.add_run("\nModel: ").bold = True
    meta.add_run(model_size)
    if language:
        meta.add_run("\nDetected language: ").bold = True
        meta.add_run(str(language))
    if duration:
        meta.add_run("\nDuration: ").bold = True
        meta.add_run(f"{duration:.1f}s")
    doc.add_paragraph("")
    if text:
        doc.add_paragraph(text)

    doc.save(docx_path)

    return {
        "ok": True,
        "text": text,
        "docx_file": f"/download/{docx_name}",
        "model": model_size,
        "language": language,
        "duration_seconds": duration,
        "filename": file.filename,
    }

@app.get("/download/{fname}")
async def download_file(fname: str):
    path = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=fname)
