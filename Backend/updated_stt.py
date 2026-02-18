import pyaudio
import numpy as np
import threading
import queue
import time
from faster_whisper import WhisperModel

# --- Configuration for RTX 3050 ---
MODEL_SIZE = "medium"       # Smart enough for Tanglish
DEVICE = "cuda"             # Uses your GPU
COMPUTE_TYPE = "int8"       # Fits in 4GB VRAM & is fast
SAMPLE_RATE = 16000
CHANNELS = 1

# --- Smart Recording Settings ---
VOL_THRESHOLD = 0.01        # Volume sensitivity (Adjust if env is noisy)
SILENCE_LIMIT = 1.0         # Seconds of silence to wait before processing
LISTEN_CHUNK = 0.1          # Check audio every 0.1 seconds

# --- Initialize Whisper ---
print(f"Loading Whisper '{MODEL_SIZE}' model on {DEVICE}...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("Model loaded. Ready!")

# Thread-safe queue to pass audio from Recorder -> Transcriber
audio_queue = queue.Queue()

def record_audio_smart():
    """
    Smart Recorder:
    1. Waits for sound > VOL_THRESHOLD
    2. Records continuously while you speak
    3. Stops automatically after SILENCE_LIMIT seconds of silence
    """
    p = pyaudio.PyAudio()
    
    chunk_samples = int(SAMPLE_RATE * LISTEN_CHUNK)
    
    stream = p.open(format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=1024)
    
    print(f"\n[Status] Listening... (Speak naturally)")
    
    try:
        while True:
            audio_buffer = [] 
            silence_counter = 0
            is_speaking = False
            
            while True:
                # Read tiny chunk (0.1s)
                data = stream.read(chunk_samples, exception_on_overflow=False)
                
                # Convert to float32 for analysis
                audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Check current volume
                volume = np.max(np.abs(audio_chunk))
                
                # Logic: Detect Speech vs Silence
                if volume > VOL_THRESHOLD:
                    if not is_speaking:
                        print(" -> Speech detected...", end="\r", flush=True)
                    is_speaking = True
                    silence_counter = 0  # Reset silence timer
                elif is_speaking:
                    silence_counter += LISTEN_CHUNK # Count silence duration
                
                # Always keep recording if we are in a "session"
                if is_speaking:
                    audio_buffer.append(audio_chunk)
                
                # STOP CONDITION: Spoke before, but now silent for 1.0s
                if is_speaking and silence_counter > SILENCE_LIMIT:
                    break
            
            # Combine all chunks into one full sentence
            if audio_buffer:
                full_audio = np.concatenate(audio_buffer)
                audio_queue.put(full_audio)
                print(" -> Processing phrase...   ", end="\r", flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def process_audio():
    """
    Pulls full sentences from queue and transcribes them.
    """
    # Start the recorder in background
    recording_thread = threading.Thread(target=record_audio_smart, daemon=True)
    recording_thread.start()
    
    try:
        while True:
            # Block until a full sentence is ready
            audio_data = audio_queue.get()
            
            # Transcribe
            # initial_prompt hints the model to expect mixed English/Tamil
            segments, info = model.transcribe(
                audio_data, 
                beam_size=1, 
                language=None,    # Auto-detect language
                vad_filter=True,  # Extra filter to ignore breathing noises
                initial_prompt="Hello, Thank you. Recharge pannanum. Offer ennathu?"
            )
            
            print("\nUser said:", end=" ")
            for segment in segments:
                print(segment.text, end=" ", flush=True)
            print("\n" + "-"*30)
            
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    process_audio()