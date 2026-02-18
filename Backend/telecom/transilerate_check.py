import pyaudio
import numpy as np
import threading
import queue
import time
import os
import requests
import torch
import sounddevice as sd
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from groq import Groq
from transformers import AutoTokenizer, VitsModel
import re

# --- 1. CONFIGURATION ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
client = Groq(api_key=GROQ_API_KEY)

# Audio Config
SAMPLE_RATE = 16000
LISTEN_CHUNK_S = 0.2
VOL_THRESHOLD = 0.008
SILENCE_LIMIT = 1.0 

# Model Config
WHISPER_SIZE = "medium"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TTS_MODEL_PATH = "local_models/mms-tts-tam" 

# Queues
audio_play_queue = queue.Queue()

print(f"🚀 Initializing on {DEVICE}...")

# --- 2. TEXT CLEANING UTILS ---
def clean_repeated_text(text):
    """
    Fixes Whisper looping: 'Hello hello hello hello' -> 'Hello'
    """
    words = text.split()
    if not words: return ""
    
    # Simple deduplication of consecutive identical phrases
    unique_words = []
    prev_word = ""
    for w in words:
        if w.lower() != prev_word.lower():
            unique_words.append(w)
            prev_word = w
    
    # If the whole sentence is just one word repeated many times
    if len(set(unique_words)) == 1 and len(words) > 3:
        return unique_words[0]
        
    return " ".join(unique_words)

# --- 3. CLASS: FAST TRANSLITERATOR ---
class FastTransliterator:
    def __init__(self):
        self.session = requests.Session()
        self.url = "https://inputtools.google.com/request"
    
    def convert(self, text):
        if len(text.strip()) < 2: return text
        params = {
            "text": text, "itc": "ta-t-i0-und", "num": "1",
            "cp": "0", "cs": "1", "ie": "utf-8", "oe": "utf-8"
        }
        try:
            response = self.session.get(self.url, params=params, timeout=1)
            data = response.json()
            if data[0] == "SUCCESS":
                return "".join([item[1][0] for item in data[1]])
            return text
        except:
            return text

# --- 4. LOAD MODELS ---
print("1️⃣ Loading Whisper (with Repetition Penalty)...")
# Using int8 for speed, float16 for accuracy. Switch if needed.
whisper_model = WhisperModel(WHISPER_SIZE, device=DEVICE, compute_type="float16")

print("2️⃣ Loading Bridge...")
transliterator = FastTransliterator()

print("3️⃣ Loading TTS...")
try:
    tokenizer_tts = AutoTokenizer.from_pretrained(TTS_MODEL_PATH)
    model_tts = VitsModel.from_pretrained(TTS_MODEL_PATH).to(DEVICE)
except:
    tokenizer_tts = AutoTokenizer.from_pretrained("facebook/mms-tts-tam")
    model_tts = VitsModel.from_pretrained("facebook/mms-tts-tam").to(DEVICE)

# --- 5. AUDIO PLAYER THREAD ---
def audio_player_worker():
    while True:
        audio_chunk = audio_play_queue.get()
        if audio_chunk is None: break
        try:
            sd.play(audio_chunk, samplerate=16000)
            sd.wait()
        except Exception as e:
            print(f"Playback Error: {e}")
        audio_play_queue.task_done()

player_thread = threading.Thread(target=audio_player_worker, daemon=True)
player_thread.start()

# --- 6. GENERATE AUDIO ---
def generate_and_queue_audio(tanglish_text):
    if not tanglish_text.strip(): return

    # A. Transliterate
    tamil_script = transliterator.convert(tanglish_text)
    
    # B. TTS Inference
    inputs = tokenizer_tts(text=tamil_script, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        output = model_tts(**inputs).waveform
    
    # C. Queue
    audio_np = output.cpu().float().numpy().squeeze()
    audio_play_queue.put(audio_np)
    
    print(f"   [🔊 Speaking] {tanglish_text}")

# --- 7. GROQ STREAMING (PUNCTUATION ONLY) ---
def process_conversation(user_text, history):
    print(f"\n🧠 Thinking...")
    
    # SYSTEM PROMPT: Force simple words to avoid bad transliteration
    system_prompt = """
    ROLE: You are 'Siva', a friendly Customer Support Executive for 'SuperNet' in Chennai.
    
    CRITICAL RULES (Follow these or you will be fired):
    1. OUTPUT FORMAT: Speak ONLY in "Tanglish" (Tamil words typed in English alphabets).
    2. FORBIDDEN: NEVER use Tamil Script (like தமிழ்). NEVER speak pure formal English.
    3. INPUT HANDLING: Even if the user speaks in Tamil Script, you MUST reply in Tanglish.
    4. TONE: Be helpful, polite, but casual. Use words like 'Sir', 'Madam', 'Kandippa', 'Aama', 'Line-la irunga'.
    
    KNOWLEDGE BASE (Use these plans):
    - "Smart Pack 299": Rs. 299, 1.5GB/day, 28 Days.
    - "Jumbo Pack 666": Rs. 666, 2GB/day, 84 Days.
    - "Data Add-on": Rs. 19 for 1GB.
    
    EXAMPLE CONVERSATION:
    User: "Enaku net vela seyala"
    Siva: "Aiyo apdiya sir? Kavalai padatheenga, naan check panren."
    
    User: (In Tamil Script) "எனக்கு ஒரு நல்ல பிளான் சொல்லுங்க"
    Siva: "Kandippa Madam. Namba kitta 'Jumbo Pack' onnu iruku. Just 666 rupees dhaan, 84 days valid."
    
    User: "What is your name?"
    Siva: "En peru Siva sir, SuperNet-la work panren."
    """
    
    messages = [{"role": "system", "content": system_prompt}] + history[-4:] + [{"role": "user", "content": user_text}]
    
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=250,
        temperature=0.6,
        stream=True
    )

    buffer_text = ""
    print("🗣️ Agent: ", end="", flush=True)

    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
            buffer_text += content

            # --- STRICT BUFFERING LOGIC ---
            # ONLY split if we hit a delimiter: . ? ! , 
            # This guarantees we never split a word like "expect" in half.
            if any(p in content for p in [".", "?", "!", ","]):
                
                # Split at the LAST punctuation mark found
                # This regex splits keeping the delimiter attached to the previous part
                parts = re.split(r'([.?!,])', buffer_text)
                
                # If we have at least one full phrase (text + punctuation)
                if len(parts) > 2:
                    # parts[0] is text, parts[1] is punct
                    to_speak = parts[0] + parts[1]
                    
                    if len(to_speak.split()) > 1: # Don't speak single words like "Ok."
                        generate_and_queue_audio(to_speak)
                    
                    # Keep the rest in buffer
                    buffer_text = "".join(parts[2:])

    # Flush remaining buffer
    if buffer_text.strip():
        generate_and_queue_audio(buffer_text)
    
    return "Response Completed"

# --- 8. MAIN LOOP ---
def run_agent():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)
    
    print("\n✅ AGENT READY. Speak now!")
    
    conversation_history = []
    chunk_samples = int(SAMPLE_RATE * LISTEN_CHUNK_S)
    
    while True:
        audio_buffer = []
        silence_frames = 0
        is_speaking = False
        
        while True:
            data = stream.read(chunk_samples, exception_on_overflow=False)
            audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            volume = np.max(np.abs(audio_chunk))
            
            if volume > VOL_THRESHOLD:
                is_speaking = True
                silence_frames = 0
            elif is_speaking:
                silence_frames += 1
            
            if is_speaking:
                audio_buffer.append(audio_chunk)
            
            if is_speaking and silence_frames > (SILENCE_LIMIT / LISTEN_CHUNK_S):
                break
                
        if audio_buffer:
            full_audio = np.concatenate(audio_buffer)
            
            # --- WHISPER FIX ---
            # repetition_penalty=1.2 kills the "Naan nalla iruken" loop
            segments, _ = whisper_model.transcribe(
                full_audio, 
                beam_size=1, 
                language=None, 
                condition_on_previous_text=False, 
                repetition_penalty=1.2, # <--- KEY FIX
                no_speech_threshold=0.5,
                initial_prompt="Machan eppadi irukka?" 
            )
            
            raw_text = " ".join([s.text for s in segments]).strip()
            
            # Clean up the text
            user_text = clean_repeated_text(raw_text)
            
            if len(user_text) < 3 or user_text.lower() in ["thank you", "subtitles"]: 
                continue 
            
            print(f"\n\n👤 User: {user_text}")
            
            reply = process_conversation(user_text, conversation_history)
            
            conversation_history.append({"role": "user", "content": user_text})

if __name__ == "__main__":
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\nExiting...")