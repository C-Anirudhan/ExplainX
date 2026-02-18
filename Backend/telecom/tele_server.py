import os
import uvicorn
import requests
import edge_tts
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from groq import Groq
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# ⚠️ YOUR NGROK DOMAIN (No https://)
NGROK_DOMAIN = "seasonably-unsalted-pearlene.ngrok-free.dev"

client = Groq(api_key=GROQ_API_KEY)
print("Loading Whisper Model...")
whisper_model = WhisperModel("medium", device="cuda", compute_type="int8")
print("✅ Ready! Waiting for TeleCMI calls...")

app = FastAPI()

# Mount folder to serve MP3 files
os.makedirs("audio_files", exist_ok=True)
app.mount("/audio", StaticFiles(directory="audio_files"), name="audio")

# --- 1. START OF CALL (TeleCMI hits this first) ---
@app.post("/telecmi")
async def handle_call(request: Request):
    print("📞 Incoming Call from TeleCMI!")
    
    # We generate the Intro MP3 if it doesn't exist
    if not os.path.exists("audio_files/intro.mp3"):
        communicate = edge_tts.Communicate("Vanakkam! I am your AI Assistant. Speak now.", "ta-IN-ValluvarNeural")
        await communicate.save("audio_files/intro.mp3")

    # PIOPIY (TeleCMI) Action List
    # 1. Play Intro -> 2. Record User
    actions = [
        {
            "action": "play",
            "file": f"https://{NGROK_DOMAIN}/audio/intro.mp3"
        },
        {
            "action": "record",
            "url": f"https://{NGROK_DOMAIN}/handle_recording", # Send recording here
            "format": "mp3", # TeleCMI supports MP3
            "timeout": 10,   # Stop recording after 10s
            "beep": True     # Play beep sound
        }
    ]
    return JSONResponse(content=actions)

# --- 2. HANDLE RECORDING (User Spoke) ---
@app.post("/handle_recording")
async def handle_recording(request: Request):
    print("🎤 User Audio Received! Processing...")
    
    # TeleCMI sends the recording URL in the body
    data = await request.json()
    recording_url = data.get("recording_url")
    
    if not recording_url:
        print("❌ No recording found.")
        return JSONResponse(content=[{"action": "hangup"}])

    # 1. Download User's Audio
    audio_content = requests.get(recording_url).content
    with open("temp_user.mp3", "wb") as f:
        f.write(audio_content)

    # 2. Transcribe (Whisper)
    segments, _ = whisper_model.transcribe("temp_user.mp3")
    user_text = " ".join([s.text for s in segments]).strip()
    print(f"User Said: {user_text}")

    # 3. Get AI Reply (Groq)
    reply_text = get_groq_reply(user_text)
    print(f"Agent Reply: {reply_text}")

    # 4. Generate MP3 Response
    communicate = edge_tts.Communicate(reply_text, "ta-IN-ValluvarNeural")
    await communicate.save("audio_files/reply.mp3")

    # 5. Reply & Loop (Play Reply -> Record Again)
    actions = [
        {
            "action": "play",
            "file": f"https://{NGROK_DOMAIN}/audio/reply.mp3"
        },
        {
            "action": "record",
            "url": f"https://{NGROK_DOMAIN}/handle_recording",
            "format": "mp3",
            "timeout": 10,
            "beep": True
        }
    ]
    return JSONResponse(content=actions)

def get_groq_reply(text):
    if not text: return "I didn't hear anything."
    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a friendly Tamil friend. Speak short Tanglish."},
                {"role": "user", "content": text}
            ]
        )
        return chat.choices[0].message.content
    except:
        return "Network issue."

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)