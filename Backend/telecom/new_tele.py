import pyaudio
import numpy as np
import threading
import queue
import time
import os
import sys
import subprocess
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from groq import Groq

# 1. Setup Environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=GROQ_API_KEY)

# --- Configuration ---
MODEL_SIZE = "medium"
DEVICE = "cuda" # or "cpu"
COMPUTE_TYPE = "int8"
SAMPLE_RATE = 16000
LISTEN_CHUNK = 0.1
VOL_THRESHOLD = 0.01
SILENCE_LIMIT = 1.0  

# --- Initialize Ear ---
print(f"1. Loading Ear (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("--- AGENT READY (Speak now) ---")

# GLOBAL VARIABLES
audio_buffer = np.array([], dtype=np.float32)
is_recording = False
silence_detected = False
conversation_history = []

# --- UPDATED PROMPT: STRICT TANGLISH ---
purpose = {"internet":"""
    You are a smart Telecom Assistant for Indian networks (Jio, Airtel, Vi).
    
    CRITICAL RULES:
    1. MEMORY: Remember the context (e.g., if talking about Airtel, stay on Airtel).
    
    2. LENGTH ADAPTATION: 
       - Default: Keep answers SHORT (1 sentence).
       - Exception: If the user asks to "explain", "speak longer", or "details", give a FULL explanation (2-3 sentences).
    
    3. CLOSING LOGIC (Be Careful): 
       - ONLY say "Okay sir, Nandri" if the user explicitly says "Bye", "Later", "Cut call", or "No thanks".
       - If the user says "Okay, tell me more", DO NOT STOP. Continue explaining.
    
    4. CORRECTION: 
       - "8L" -> "Airtel"
       - "5E" -> "5G"
       - "Chartta" -> "Short"
       - "Langa" -> "Long"
    
    5. STYLE: Speak in natural 'Tanglish' (Tamil words in English script).
    
    Example Interaction:
    User (Tamil Script): எனக்கு ஜியோ பிளான் வேணும்
    You: Kandippa sir, Jio la 5G plans pathi sollava illa 4G data packs venuma?
    """}

def get_groq_reply(user_text):
    global conversation_history
    system_prompt = purpose["internet"]
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-6:]) 
    messages.append({"role": "user", "content": user_text})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6, 
            max_tokens=500
        )
        reply = completion.choices[0].message.content
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"Groq Error: {e}")
        return "Network issue."

def speak_text(text):
    """TTS updated to Indian English for better Tanglish pronunciation"""
    if not text: return
    print(f"\n🗣️ Speaking...")
    
    # CHANGED VOICE: 'ta-IN-ValluvarNeural' handles Tanglish much better than 'ta-IN'
    voice = "ta-IN-ValluvarNeural" 
    output_file = "reply.mp3"
    
    if os.path.exists(output_file):
        try: os.remove(output_file)
        except: pass

    command = f'"{sys.executable}" -m edge_tts --text "{text}" --write-media {output_file} --voice {voice} --rate=+40%'
    
    try:
        subprocess.run(command, shell=True, capture_output=True, text=True)
        if os.path.exists(output_file):
            if os.name == 'nt': # Windows
                os.system(f"start {output_file}")
                time.sleep(len(text.split()) * 0.4) 
            else:
                os.system(f"mpg123 {output_file}")
    except Exception as e:
        print(f"TTS Error: {e}")

# --- THREAD 1: AUDIO RECORDER ---
def recording_thread():
    global audio_buffer, is_recording, silence_detected
    
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)
    chunk_samples = int(SAMPLE_RATE * LISTEN_CHUNK)
    
    print("\n🎤 Listening... (Start speaking)")
    
    temp_buffer = []
    silence_counter = 0
    has_spoken = False
    is_recording = True
    silence_detected = False
    
    try:
        while True:
            data = stream.read(chunk_samples, exception_on_overflow=False)
            audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            volume = np.max(np.abs(audio_chunk))
            
            if volume > VOL_THRESHOLD:
                silence_counter = 0
                has_spoken = True
            elif has_spoken:
                silence_counter += LISTEN_CHUNK
            
            if has_spoken:
                temp_buffer.append(audio_chunk)
                audio_buffer = np.concatenate(temp_buffer)
            
            if has_spoken and silence_counter > SILENCE_LIMIT:
                silence_detected = True
                break
                
    except Exception as e:
        print(e)
    finally:
        is_recording = False
        stream.stop_stream()
        stream.close()
        p.terminate()

# --- MAIN LOOP ---
def run_agent():
    global audio_buffer, is_recording, silence_detected
    
    while True:
        audio_buffer = np.array([], dtype=np.float32)
        silence_detected = False
        
        # Start Recording
        rec_thread = threading.Thread(target=recording_thread)
        rec_thread.start()
        
        last_transcribe_time = time.time()
        current_text = ""
        
        # Real-Time Transcription Loop
        while rec_thread.is_alive():
            if time.time() - last_transcribe_time > 0.5 and len(audio_buffer) > SAMPLE_RATE:
                
                # NOTE: Whisper might still output Tamil script here. That is OKAY.
                # The LLM will convert it to Tanglish.
                segments, _ = whisper_model.transcribe(
                    audio_buffer, 
                    beam_size=1, 
                    language=None, 
                    vad_filter=True,
                    initial_prompt="Winoth, neenga eppadi irukeenga? Naan nalla iruken."
                )
                
                new_text = " ".join([s.text for s in segments]).strip()
                if new_text != current_text:
                    current_text = new_text
                    # Use a font that supports Tamil if your terminal shows boxes, 
                    # but mostly this is just for you to see.
                    print(f"\rUser: {current_text}...", end="", flush=True)
                
                last_transcribe_time = time.time()
            
            time.sleep(0.1)
        
        rec_thread.join()
        
        # Final Processing
        if len(audio_buffer) > 0:
            segments, _ = whisper_model.transcribe(audio_buffer, beam_size=1, language=None,initial_prompt="Winoth, neenga eppadi irukeenga? Naan nalla iruken.")
            final_text = " ".join([s.text for s in segments]).strip()
            
            if len(final_text) > 2:
                print(f"\rUser: {final_text}      ") 
                
                # The Brain handles the conversion to Tanglish
                reply = get_groq_reply(final_text)
                print(f"Agent: {reply}")
                
                speak_text(reply)
            else:
                print("\r(No speech detected)      ")
        
        print("-" * 30)

if __name__ == "__main__":
    run_agent()