import pyaudio
import numpy as np
import threading
import queue
import time
import google.generativeai as genai
from faster_whisper import WhisperModel
from dotenv import load_dotenv
import os


load_dotenv()
API = os.getenv("API")

genai.configure(api_key=API)

m_name = "models/gemini-2.5-flash"
model = genai.GenerativeModel("models/gemini-2.5-flash")

# --- Configuration ---
MODEL_SIZE = "medium"
DEVICE = "cuda"       # or "cpu"
COMPUTE_TYPE = "int8_float16" # use "int8" if on CPU
CHUNK_DURATION = 2    # Duration of audio chunks to process (seconds)
SAMPLE_RATE = 16000   # Whisper expects 16kHz
CHANNELS = 1

# --- Initialize Model ---
print("Loading model...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("Model loaded.")

# Thread-safe queue for audio chunks
audio_queue = queue.Queue()

def record_audio():
    """
    Continuously records audio from the microphone and puts chunks into the queue.
    """
    p = pyaudio.PyAudio()
    
    # Calculate frames per chunk
    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    
    stream = p.open(format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=1024)
    
    print(f"Listening... (Speak into your microphone)")
    
    try:
        while True:
            # Read audio data
            data = stream.read(chunk_size, exception_on_overflow=False)
            # Convert raw bytes to numpy array
            audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_queue.put(audio_array)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def process_audio():
    """
    Continuously pulls audio from the queue and transcribes it.
    """
    print("Transcription started. Press Ctrl+C to stop.")
    
    # Start recording in a separate thread
    recording_thread = threading.Thread(target=record_audio, daemon=True)
    recording_thread.start()
    
    try:
        while True:
            # Get audio chunk from queue (blocks until data is available)
            audio_chunk = audio_queue.get()
            
            # Transcribe the chunk
            # beam_size=5 provides better accuracy; set to 1 for faster speed
            segments, info = model.transcribe(audio_chunk, beam_size=1)
            
            # Print results "simultaneously"
            for segment in segments:
                # Use end="" and flush=True to print like a stream
                print(segment.text, end=" ", flush=True)

    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    process_audio()