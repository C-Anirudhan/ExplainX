import os
import io
import re
import asyncio
import numpy as np
import soundfile as sf
import torch
import tempfile
import wave


from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
from groq import Groq
from elevenlabs import ElevenLabs


# ============================
# CONFIG
# ============================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY")

if not ELEVEN_API_KEY:
    raise ValueError("Missing ELEVENLABS_API_KEY")


client = Groq(api_key=GROQ_API_KEY)
tts_client = ElevenLabs(api_key=ELEVEN_API_KEY)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SAMPLE_RATE = 16000


# ============================
# LOAD MODELS
# ============================

print("🚀 Loading Whisper...")

whisper = WhisperModel(
    "medium",
    device=DEVICE,
    compute_type="float16" if DEVICE == "cuda" else "int8"
)


# ============================
# FASTAPI
# ============================

app = FastAPI()


# ============================
# TTS
# ============================

async def tts_generate(text: str):

    audio_stream = tts_client.text_to_speech.convert(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_multilingual_v2",
        text=text
    )

    audio_bytes = b"".join(audio_stream)

    return audio_bytes


# ============================
# LLM STREAM (ASYNC GENERATOR)
# ============================

async def llm_stream(user_text, history):

    system_prompt = """
ROLE: You are a friendly, colloquial Tamil person from Chennai having a casual chat.

CORE INSTRUCTIONS:

Your name is K.Kumar.Use this name whenever your name is asked.

1. LANGUAGE: Speak ONLY in "Tanglish" (Tamil words typed in English script).
   - Example: "Saptiya?" instead of "Did you eat?" or "சாப்பிட்டியா?"
   - Example: "Romba thanks macha" instead of "Thank you very much."

2. FORBIDDEN:
   - NEVER use Tamil Script (like வணக்கம்).
   - NEVER speak in pure, formal English (like "Hello, how are you?").
   - NEVER act like a robot or AI assistant.

3. TONE & STYLE:
   - Be warm, casual, and expressive.
   - Use filler words natural to Tamil speech: 'Macha', 'Pa', 'Aama', 'Sari', 'Aiyo'.
   - Use Tamil grammar structure even when using English words (SOV structure).
     - Wrong: "I will call you tomorrow."
     - Right: "Naan unna nalaiku call panren."

4. CONVERSATION FLOW:
   - Keep replies short and crisp (1-2 sentences), like a WhatsApp chat.
   - Ask follow-up questions to keep the chat going.

EXAMPLE INTERACTION:
User: "Hi, eppadi irukka?"
You: "Hey! Naan semmaiya iruken pa. Neenga eppadi? Saptacha?"

User: "Romba bore adikudhu."
You: "Aiyo, yenna aachu? Edhavathu movie polama illa namma friends kitta pesalama?"
"""


    messages = (
        [{"role": "system", "content": system_prompt}]
        + history[-10:]
        + [{"role": "user", "content": user_text}]
    )

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6,
        max_tokens=250,
        stream=True
    )

    buffer = ""

    for chunk in stream:

        content = chunk.choices[0].delta.content

        if not content:
            continue

        buffer += content

        if any(p in content for p in [".", "?", "!"]):

            parts = re.split(r"([.?!])", buffer)

            if len(parts) > 2:

                yield parts[0] + parts[1]

                buffer = "".join(parts[2:])


    if buffer.strip():
        yield buffer


# ============================
# SPEECH TO TEXT
# ============================

def transcribe_audio(audio_bytes):

    if len(audio_bytes) < 4000:
        return ""

    # Create temp wav
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:

        wf = wave.open(tmp.name, "wb")

        wf.setnchannels(1)
        wf.setsampwidth(2)   # int16
        wf.setframerate(16000)

        wf.writeframes(audio_bytes)

        wf.close()

        temp_path = tmp.name


    segments, _ = whisper.transcribe(
        temp_path,
        beam_size=1,
        language=None,
        vad_filter=True,
        condition_on_previous_text=False
    )

    text = " ".join(s.text for s in segments)

    # Cleanup
    try:
        os.remove(temp_path)
    except:
        pass

    return text.strip()




# ============================
# WEBSOCKET
# ============================

@app.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):

    await ws.accept()

    print("✅ Client connected")

    audio_buffer = bytearray()

    # Conversation memory (empty at start)
    history = []


    try:

        while True:

            data = await ws.receive_bytes()

            # End of speech marker
            if data == b"__END__":
                print("📦 Audio bytes:", len(audio_buffer))


                user_text = transcribe_audio(bytes(audio_buffer))

                print("👤 User:", user_text)

                audio_buffer.clear()


                if len(user_text) < 2:
                    continue


                full_reply = ""


                async for sentence in llm_stream(
                    user_text,
                    history
                ):

                    print("🧠:", sentence)

                    full_reply += sentence

                    audio = await tts_generate(sentence)

                    await ws.send_bytes(audio)


                # Store in history
                history.append(
                    {"role": "user", "content": user_text}
                )

                history.append(
                    {"role": "assistant", "content": full_reply}
                )


            else:

                audio_buffer.extend(data)


    except WebSocketDisconnect:

        print("❌ Client disconnected")


# ============================
# START SERVER
# ============================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "websocket_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )



