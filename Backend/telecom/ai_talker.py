import pyaudio
import numpy as np
import threading
import queue
import time
import os
import google.generativeai as genai
from faster_whisper import WhisperModel
from dotenv import load_dotenv

# 1. Setup API and Models
load_dotenv()
API = os.getenv("API")
genai.configure(api_key=API)

# --- Configuration ---
MODEL_SIZE = "medium"
DEVICE = "cuda"
COMPUTE_TYPE = "int8"
SAMPLE_RATE = 16000

# --- Smart Recording Config ---
VOL_THRESHOLD = 0.01   # Adjust if it records silence
SILENCE_LIMIT = 1.0    # Stops recording after 1s silence
LISTEN_CHUNK = 0.1

print("1. Loading Brain (Gemini)...")
gemini_model = genai.GenerativeModel(
    "models/gemini-2.5-flash", # Use 1.5 Flash for speed (or 2.5 if available)
    system_instruction="""
    You are a helpful AI assistant who knows about all telecom plans. 
    Rules:
    1. Speak in casual 'Tanglish' (Tamil + English mix).
    2. Keep answers SHORT (1 sentence only).
    3. Do not be formal. Act like a human on the phone.
    4. If the user text looks like bad transcription, guess the meaning contextually.
    """
)

print(f"2. Loading Ear (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("--- AGENT READY (Speak now) ---")

audio_queue = queue.Queue()

def record_audio_smart():
    p = pyaudio.PyAudio()
    chunk_samples = int(SAMPLE_RATE * LISTEN_CHUNK)
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)
    
    try:
        while True:
            audio_buffer = []
            silence_counter = 0
            is_speaking = False
            
            while True:
                data = stream.read(chunk_samples, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                volume = np.max(np.abs(audio_chunk))
                
                if volume > VOL_THRESHOLD:
                    if not is_speaking: print("Listening...", end="\r", flush=True)
                    is_speaking = True
                    silence_counter = 0
                elif is_speaking:
                    silence_counter += LISTEN_CHUNK
                
                if is_speaking: audio_buffer.append(audio_chunk)
                
                if is_speaking and silence_counter > SILENCE_LIMIT:
                    break
            
            if audio_buffer:
                audio_queue.put(np.concatenate(audio_buffer))
                print("Thinking... ", end="\r", flush=True)

    except KeyboardInterrupt: pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def run_agent():
    threading.Thread(target=record_audio_smart, daemon=True).start()
    
    try:
        while True:
            # 1. Get Audio
            audio_data = audio_queue.get()
            
            # 2. Transcribe (Ear)
            segments, _ = whisper_model.transcribe(
                audio_data, 
                beam_size=1, 
                language=None, 
                vad_filter=True,
                initial_prompt="Hello, Thank you. Recharge pannanum. Offer ennathu?"
            )
            user_text = " ".join([s.text for s in segments]).strip()
            
            if len(user_text) > 2:
                print(f"\nUser: {user_text}")
                
                # 3. Generate Reply (Brain)
                response = gemini_model.generate_content(user_text)
                reply = response.text.strip()
                print(f"Agent: {reply}")
                print("-" * 30)
                
                # 4. (Future) Add TTS here: say_text(reply)

    except KeyboardInterrupt:
        print("\nCall Ended.")

if __name__ == "__main__":
    run_agent()