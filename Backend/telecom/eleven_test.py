import pyaudio
import numpy as np
import threading
import queue
import time
import os
import sys
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from groq import Groq
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

# 1. Setup Environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=GROQ_API_KEY)

# --- ElevenLabs Configuration ---
ELEVENLABS_API_KEY = "sk_af5f5f72f81c63b5dffae05305fcdbb5e27045dae84349c2"
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb" # "Nitish" or your specific voice
MODEL_ID = "eleven_multilingual_v2"

# --- General Configuration ---
MODEL_SIZE = "medium"
DEVICE = "cuda"
COMPUTE_TYPE = "int8"
SAMPLE_RATE = 16000
LISTEN_CHUNK = 0.1
VOL_THRESHOLD = 0.01
SILENCE_LIMIT = 1.0

# --- Initialize Ear ---
print(f"1. Loading Ear (Whisper {MODEL_SIZE})...")
whisper_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("--- AGENT READY (Speak now) ---")

audio_queue = queue.Queue()
# GLOBAL HISTORY LIST
conversation_history = []

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
    """,
    "friendly":"""
    You are a chill, friendly AI companion who speaks in 'Tanglish' (Tamil + English).
    
    YOUR PERSONA:
    - You are like a close friend ("Machi" or "Bro").
    - You are NOT a customer support agent. Do NOT say "How can I help you?".
    - Instead, ask "Enna aachu?" (What happened?) or "Sollu bro" (Tell me bro).
    
    RULES:
    1. LENGTH: short and snappy (2-3 sentences). Fast conversation.
    2. STYLE: Casual. Use words like "Super", "Machi", "Theriyum", "Okay pa".
    3. CORRECTION: 
       - If user says "Parama", assume they mean "Aprama" (Later).
       - Ignore small grammar mistakes in transcription.
    
    EXAMPLE:
    User: "Bore adikudhu"
    You: "Aiyo, yen machi? Vaa edhavadhu padam paakalaama or game vilaiyaadalaama?"
    """}

def get_groq_reply(user_text):
    """
    Uses Llama 3.3 70B with SMART ADAPTABILITY.
    """
    global conversation_history
    
    system_prompt = purpose["internet"]

    # Build Message Chain
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
        
        # Update History
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": reply})
        
        return reply
    except Exception as e:
        print(f"Groq Error: {e}")
        return "Mannikavum, network issue."

def speak_text(text):
    """Uses ElevenLabs TTS (High Quality)."""
    if not text: return
    print(f"🗣️ Generating Audio (ElevenLabs)...")
    
    try:
        audio = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        print(f"▶️ Playing Audio...")
        play(audio)
    except Exception as e:
        print(f"❌ ElevenLabs TTS Error: {e}")

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
                    if not is_speaking: print("🎤 Listening...", end="\r", flush=True)
                    is_speaking = True
                    silence_counter = 0
                elif is_speaking:
                    silence_counter += LISTEN_CHUNK
                
                if is_speaking: audio_buffer.append(audio_chunk)
                
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
    threading.Thread(target=record_audio_smart, daemon=True).start()
    
    try:
        while True:
            audio_data = audio_queue.get()
            
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
                
                # Call Brain (Now with Memory)
                reply = get_groq_reply(user_text)
                
                print(f"Agent: {reply}")
                speak_text(reply)
                print("-" * 30)

    except KeyboardInterrupt:
        print("\nCall Ended.")

if __name__ == "__main__":
    run_agent()