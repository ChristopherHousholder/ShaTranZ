# server.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import whisper
import uvicorn
import tempfile
import os
import base64

# Google TTS
from google.cloud import texttospeech
import json

# Set credentials path for Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "shatranzserver-f1c1233314df.json"

# Init TTS client
tts_client = texttospeech.TextToSpeechClient()

def synthesize_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    return response.audio_content

app = FastAPI()
model = whisper.load_model("small")

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

        if not eng_text or len(eng_text) < 5:
            eng_text = "(no meaningful speech detected)"

        audio_bytes = synthesize_speech(eng_text)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse({
            "translated_text": eng_text,
            "audio_base64": audio_b64
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for p in (tmp_path,):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
