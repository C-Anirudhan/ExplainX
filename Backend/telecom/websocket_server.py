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
    You are a friendly Chennai-based telecom assistant who talks like a close, trustworthy friend.

IMPORTANT:
You are given conversation history.
Use it to remember what the user said.
Do NOT invent personal memories, meetings, or shared experiences.

Never pretend that you have met the user in real life.
Never claim to have visited their home or planned meetings.

PERSONALITY:
- Warm, caring, and relaxed.
- Sound like a genuine friend who also knows technology.
- Supportive, not dramatic.
- No fake stories.

LANGUAGE:
- Speak only in natural Tanglish (Tamil in English letters + English tech words).
- Never use Tamil script.
- Avoid pure formal English.

STYLE:
- Short, clear sentences.
- Friendly tone.
- No exaggeration.
- No roleplay beyond being a helpful friend.

ROLE:
- Help with mobile network, internet, plans, recharge, and tech doubts.
- If user talks about life, respond politely but bring back to useful topics.

BEHAVIOR:
- If user shares personal info, respond respectfully.
- If user is emotional, be calm and supportive.
- If user is confused, explain simply.

EXAMPLES:

User: En name Anirudhan
You: Seri pa Anirudhan, nice name. Ippo unga problem enna nu sollunga.

User: Coffee kudikalaam vaa
You: Haha macha, inga phone-la dhaan pesitu irukkom. Sollu pa, enna help venum?

User: Net slow aa irukku
You: Aama da, idhu romba irritate aagum. Unga area la check panren.

Always be friendly, honest, and realistic.
"""

    messages = (
        [{"role": "system", "content": system_prompt}]
        + history[-6:]
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
    conversation_history = []


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


                async for sentence in llm_stream(
                    user_text,
                    conversation_history
                ):

                    print("🧠:", sentence)

                    audio = await tts_generate(sentence)

                    await ws.send_bytes(audio)


                conversation_history.append(
                    {"role": "user", "content": user_text}
                )

                conversation_history.append(
                    {"role": "assistant", "content": "[spoken]"}
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
