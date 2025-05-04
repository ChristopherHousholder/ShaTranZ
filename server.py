# server.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import whisper
import pyttsx3
import uvicorn
import tempfile
import os
import base64

app = FastAPI()
model = whisper.load_model("small")  # <-- UPDATED from "base" to "small"

@app.post("/transcribe/")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("en")
):
    tmp_path = wav_path = None
    try:
        suffix = os.path.splitext(file.filename)[1] or ".3gp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = await file.read()
            tmp.write(data)
            tmp_path = tmp.name

        result = model.transcribe(tmp_path, language=language, fp16=False)
        trans = model.transcribe(tmp_path, task="translate", language=language, fp16=False)
        eng_text = trans.get("text", "").strip()

        # Server-side: filter hallucinated junk
        if not eng_text or len(eng_text) < 5:
            eng_text = "(no meaningful speech detected)"

        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wf:
            wav_path = wf.name
        engine.save_to_file(eng_text, wav_path)
        engine.runAndWait()

        with open(wav_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse({
            "translated_text": eng_text,
            "audio_base64": audio_b64
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for p in (tmp_path, wav_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
