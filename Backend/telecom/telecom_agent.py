import pyaudio
import numpy as np
import threading
import queue
import time
import os
import subprocess
import google.generativeai as genai
from faster_whisper import WhisperModel
from dotenv import load_dotenv

# 1. Setup Environment
load_dotenv()
API = os.getenv("API")
genai.configure(api_key=API)

# --- Configuration ---
MODEL_SIZE = "medium"
DEVICE = "cuda"              # Change to "cpu" if you don't have Nvidia
COMPUTE_TYPE = "int8"        # Optimized for 4GB VRAM
SAMPLE_RATE = 16000
LISTEN_CHUNK = 0.1
VOL_THRESHOLD = 0.01         # Adjust sensitivity
SILENCE_LIMIT = 1.0          # How long to wait before processing

# --- Initialize Brain (Gemini) ---
print("1. Loading Brain (Gemini)...")
gemini_model = genai.GenerativeModel(
    "models/gemini-2.5-flash", 
    system_instruction="""
    You are a knowledgeable Telecom AI Assistant.
    Rules:
    1. You know about all networks (Airtel, Jio, Vi, BSNL).
    2. Speak in casual 'Tanglish' (Tamil + English mix).
    3. Keep answers extremely SHORT (1 sentence max).
    4. Act like a helpful human friend, not a robot.
    """
)

# --- Initialize Ear (Whisper) ---
print(f"2. Loading Ear (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("--- AGENT READY (Speak now) ---")

# Queue for audio processing
audio_queue = queue.Queue()

import sys  # <--- Add this at the top

def speak_text(text):
    """
    Robust TTS: Uses sys.executable to find edge-tts and verifies file creation.
    """
    if not text: return

    print(f"🗣️ Speaking...")
    
    voice = "ta-IN-ValluvarNeural"
    output_file = "reply.mp3"
    
    # Clean up old file if it exists (prevents permission errors)
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except:
            pass

    # 1. Generate MP3 (Use sys.executable to ensure we use the correct Python env)
    # We use -m edge_tts to run it as a module (Safest way on Windows)
    command = f'"{sys.executable}" -m edge_tts --text "{text}" --write-media {output_file} --voice {voice} --rate=+20%'
    
    try:
        # Run the command and capture errors if it fails
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ TTS Error: {result.stderr}")
            return
            
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        return

    # 2. Verify file exists before playing
    if os.path.exists(output_file):
        # Play Audio (Windows)
        os.system(f"start {output_file}")
        
        # Smart wait: Estimate duration (0.4s per word)
        time.sleep(len(text.split()) * 0.4)
    else:
        print("❌ Error: Audio file was not created.")

def record_audio_smart():
    """Smart Microphone: Records only when you speak."""
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
                
                # Speech Detection Logic
                if volume > VOL_THRESHOLD:
                    if not is_speaking: print("🎤 Listening...", end="\r", flush=True)
                    is_speaking = True
                    silence_counter = 0
                elif is_speaking:
                    silence_counter += LISTEN_CHUNK
                
                if is_speaking: audio_buffer.append(audio_chunk)
                
                # Stop if silence > 1.0s
                if is_speaking and silence_counter > SILENCE_LIMIT:
                    break
            
            if audio_buffer:
                audio_queue.put(np.concatenate(audio_buffer))
                print("🧠 Thinking... ", end="\r", flush=True)

    except KeyboardInterrupt: pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def run_agent():
    # Start recording in background
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
                
                # 4. Speak Reply (Mouth)
                speak_text(reply)
                
                print("-" * 30)

    except KeyboardInterrupt:
        print("\nCall Ended.")

if __name__ == "__main__":
    run_agent()