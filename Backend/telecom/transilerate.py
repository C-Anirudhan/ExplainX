import pyaudio
import numpy as np
import threading
import queue
import time
import os
import torch
import sounddevice as sd
import re
import io
import soundfile as sf

from faster_whisper import WhisperModel
from dotenv import load_dotenv
from groq import Groq

# ElevenLabs (NEW SDK)
from elevenlabs import ElevenLabs


# =========================
# 1. CONFIG
# =========================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing in .env")

if not ELEVENLABS_API_KEY:
    raise ValueError("❌ ELEVENLABS_API_KEY missing in .env")


client = Groq(api_key=GROQ_API_KEY)
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


SAMPLE_RATE = 16000
LISTEN_CHUNK_S = 0.2
VOL_THRESHOLD = 0.008
SILENCE_LIMIT = 1.0

WHISPER_SIZE = "medium"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

audio_play_queue = queue.Queue()

print(f"\n🚀 Initializing on {DEVICE}...")


# =========================
# 2. LOAD MODELS
# =========================

print("1️⃣ Loading Whisper...")

whisper_model = WhisperModel(
    WHISPER_SIZE,
    device=DEVICE,
    compute_type="float16" if DEVICE == "cuda" else "int8"
)


# =========================
# 3. TTS FUNCTION (ELEVENLABS)
# =========================

def generate_indus_audio(text):

    if not text.strip():
        return

    try:

        audio_stream = eleven_client.text_to_speech.convert(
            voice_id="EXAVITQu4vr4xnSDxMaL",   # Adam (good neutral voice)
            model_id="eleven_multilingual_v2",
            text=text
        )

        audio_bytes = b"".join(audio_stream)

        audio_play_queue.put(audio_bytes)

        print(f"\n🔊 Speaking: {text}")

    except Exception as e:
        print("❌ TTS Error:", e)


# =========================
# 4. AUDIO PLAYER THREAD
# =========================

def audio_player_worker():

    while True:

        audio_chunk = audio_play_queue.get()

        if audio_chunk is None:
            break

        try:
            data, samplerate = sf.read(
                io.BytesIO(audio_chunk),
                dtype="float32"
            )

            sd.play(data, samplerate)
            sd.wait()

        except Exception as e:
            print("❌ Playback Error:", e)

        audio_play_queue.task_done()


player_thread = threading.Thread(
    target=audio_player_worker,
    daemon=True
)

player_thread.start()


# =========================
# 5. GROQ STREAMING
# =========================

def process_conversation(user_text, history):

    print("\n🧠 Thinking...")

    system_prompt = """
ROLE: You are a friendly Chennai Tamil person.

RULES:
- Speak only in natural Tanglish.
- Never use Tamil script.
- No formal English.
- Be casual and warm.

STYLE:
Use words like: macha, pa, aama, seri, aiyo.

EXAMPLES:
User: Hi epdi irukka?
You: Naan super-aa iruken macha, neenga epdi?
"""

    messages = (
        [{"role": "system", "content": system_prompt}]
        + history[-6:]
        + [{"role": "user", "content": user_text}]
    )

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.6,
        stream=True
    )

    buffer_text = ""
    full_response = ""

    print("\n🗣️ Siva:", end=" ", flush=True)

    for chunk in stream:

        content = chunk.choices[0].delta.content

        if not content:
            continue

        print(content, end="", flush=True)

        buffer_text += content
        full_response += content

        if any(p in content for p in [".", "?", "!"]):

            parts = re.split(r'([.?!])', buffer_text)

            if len(parts) > 2:

                to_speak = parts[0] + parts[1]

                if len(to_speak.split()) > 5:
                    generate_indus_audio(to_speak)

                buffer_text = "".join(parts[2:])


    if buffer_text.strip():
        generate_indus_audio(buffer_text)

    return full_response.strip()


# =========================
# 6. MAIN LOOP
# =========================

def run_agent():

    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=1024
    )

    print("\n✅ AGENT SIVA READY. Speak now 🎤")

    conversation_history = []

    chunk_samples = int(SAMPLE_RATE * LISTEN_CHUNK_S)


    while True:

        audio_buffer = []
        silence_frames = 0
        is_speaking = False


        while True:

            data = stream.read(
                chunk_samples,
                exception_on_overflow=False
            )

            audio_chunk = np.frombuffer(
                data,
                dtype=np.int16
            ).astype(np.float32) / 32768.0

            volume = np.max(np.abs(audio_chunk))


            if volume > VOL_THRESHOLD:

                is_speaking = True
                silence_frames = 0

            elif is_speaking:

                silence_frames += 1


            if is_speaking:
                audio_buffer.append(audio_chunk)


            if is_speaking and silence_frames > (
                SILENCE_LIMIT / LISTEN_CHUNK_S
            ):
                break


        if not audio_buffer:
            continue


        full_audio = np.concatenate(audio_buffer)


        segments, _ = whisper_model.transcribe(
            full_audio,
            beam_size=1,
            language=None,
            condition_on_previous_text=False,
            repetition_penalty=1.1,
        )


        user_text = " ".join(
            [s.text for s in segments]
        ).strip()


        if len(user_text) < 3:
            continue


        print(f"\n\n👤 User: {user_text}")


        reply = process_conversation(
            user_text,
            conversation_history
        )


        conversation_history.append(
            {"role": "user", "content": user_text}
        )

        conversation_history.append(
            {"role": "assistant", "content": reply}
        )


# =========================
# 7. ENTRY
# =========================

if __name__ == "__main__":

    try:
        run_agent()

    except KeyboardInterrupt:

        print("\n👋 Exiting...")

        audio_play_queue.put(None)
