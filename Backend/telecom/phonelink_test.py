import numpy as np
import threading
import queue
import time
import os
import sys
import subprocess
import warnings
import sounddevice as sd     
import soundfile as sf       
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from groq import Groq

# --- CONFIGURATION ---
warnings.filterwarnings("ignore")
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=GROQ_API_KEY)

MODEL_SIZE = "medium"
DEVICE = "cuda"
COMPUTE_TYPE = "int8"

# --- UNIVERSAL SETTINGS (No IDs needed) ---
# We let Windows handle the device selection
SAMPLE_RATE = 44100    # Standard Windows Audio Rate
LISTEN_CHUNK = 0.1     
VOL_THRESHOLD = 0.005  # Lowered threshold (Bluetooth is often quiet)
SILENCE_LIMIT = 1.0
IS_AGENT_SPEAKING = False 

print(f"1. Loading Ear (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

print(f"--- AGENT READY ---")
print(f"🎤 Listening to: WINDOWS DEFAULT INPUT")
print(f"🔊 Speaking to: WINDOWS DEFAULT OUTPUT")

audio_queue = queue.Queue()
temp_buffer = queue.Queue()
conversation_history = []

def get_groq_reply(user_text):
    global conversation_history
    system_prompt = """
    You are a smart Telecom Assistant (Jio, Airtel, Vi).
    RULES:
    1. MEMORY: Keep context.
    2. LENGTH: Short (1-2 sentences).
    3. STYLE: Natural Tanglish.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-6:]) 
    messages.append({"role": "user", "content": user_text})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6, 
            max_tokens=500,
            stream=False
        )
        reply = completion.choices[0].message.content
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except:
        return "Mannikavum, network issue."

def speak_text(text):
    global IS_AGENT_SPEAKING
    if not text: return
    print(f"🗣️ Speaking...")
    
    IS_AGENT_SPEAKING = True
    
    voice = "ta-IN-ValluvarNeural"
    output_file = "reply.mp3"
    
    if os.path.exists(output_file):
        try: os.remove(output_file)
        except: pass

    # Generate MP3
    command = f'"{sys.executable}" -m edge_tts --text "{text}" --write-media {output_file} --voice {voice} --rate=+25%'
    subprocess.run(command, shell=True, capture_output=True, text=True)
    
    # Play to Default Device
    if os.path.exists(output_file):
        try:
            data, fs = sf.read(output_file, dtype='float32')
            sd.play(data, fs) # No device ID = Default
            sd.wait()
        except Exception as e:
            print(f"❌ Playback Error: {e}")
    
    IS_AGENT_SPEAKING = False
    print("🎤 Listening...")

def audio_callback(indata, frames, time, status):
    if IS_AGENT_SPEAKING: return
    temp_buffer.put(indata.copy())

def process_audio_buffer():
    audio_accumulator = []
    silence_counter = 0
    is_speaking = False
    
    while True:
        try:
            indata = temp_buffer.get() 
            volume = np.max(np.abs(indata))
            
            if volume > VOL_THRESHOLD:
                if not is_speaking: print("🎤 Listening...", end="\r", flush=True)
                is_speaking = True
                silence_counter = 0
            elif is_speaking:
                silence_counter += LISTEN_CHUNK
            
            if is_speaking:
                # Downsample 44100 -> 16000 for Whisper (Simple slicing for speed)
                # Taking every 3rd sample is rough but fast: 44100/3 ~ 14700 (Close enough for Whisper)
                # Better: Use proper resampling if needed, but let's try raw first.
                # Actually, Whisper is robust. Let's send raw and see.
                audio_accumulator.append(indata.flatten())
            
            if is_speaking and silence_counter > SILENCE_LIMIT:
                if audio_accumulator:
                    full_audio = np.concatenate(audio_accumulator).astype(np.float32)
                    audio_queue.put(full_audio)
                    print("🧠 Thinking... ", end="\r", flush=True)
                
                audio_accumulator = []
                is_speaking = False
                silence_counter = 0

        except Exception as e:
            continue

def run_agent():
    threading.Thread(target=process_audio_buffer, daemon=True).start()
    
    try:
        # Open Default Stream (No IDs)
        with sd.InputStream(channels=1, 
                            samplerate=SAMPLE_RATE, 
                            callback=audio_callback,
                            blocksize=int(SAMPLE_RATE * LISTEN_CHUNK),
                            dtype='float32'):
            
            print("✅ Connected to Windows Default Audio!")
            
            while True:
                audio_data = audio_queue.get()
                segments, _ = whisper_model.transcribe(
                    audio_data, beam_size=1, language=None, vad_filter=True,
                    initial_prompt="Hello."
                )
                user_text = " ".join([s.text for s in segments]).strip()
                
                if len(user_text) > 2:
                    print(f"\nUser: {user_text}")
                    reply = get_groq_reply(user_text)
                    print(f"Agent: {reply}")
                    speak_text(reply)
                    print("-" * 30)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Hint: Make sure you selected the Phone as Default Device in Settings.")

if __name__ == "__main__":
    run_agent()