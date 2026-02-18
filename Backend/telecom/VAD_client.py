import websocket
import pyaudio
import numpy as np
import threading
import io
import soundfile as sf
import sounddevice as sd
import time


WS_URL = "ws://localhost:8000/ws/voice"

RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1


# =============================
# AUDIO PLAYER
# =============================

def listen_server(ws):

    while True:

        try:
            audio_bytes = ws.recv()

            if not audio_bytes:
                continue

            data, sr = sf.read(
                io.BytesIO(audio_bytes),
                dtype="float32"
            )

            sd.play(data, sr)
            sd.wait()

        except:
            break


# =============================
# MAIN
# =============================

def main():

    ws = websocket.WebSocket()
    ws.connect(WS_URL)

    print("✅ Connected to server")

    # Listen thread
    threading.Thread(
        target=listen_server,
        args=(ws,),
        daemon=True
    ).start()


    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )


    print("\n📞 Call started. Speak normally...\n")


    silence_limit = 1     # seconds
    silence_count = 0
    threshold = 300        # adjust if needed

    speaking = False
    frames = []


    try:

        while True:

            data = stream.read(
                CHUNK,
                exception_on_overflow=False
            )

            audio = np.frombuffer(data, dtype=np.int16)

            rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))


            # Detect speech
            if rms > threshold:

                if not speaking:
                    print("🎙️ Speaking...")
                    speaking = True

                frames.append(data)
                silence_count = 0


            else:

                if speaking:

                    silence_count += CHUNK / RATE


                    if silence_count > silence_limit:

                        print("📤 Sending utterance")

                        for f in frames:
                            ws.send_binary(f)

                        ws.send_binary(b"__END__")

                        frames = []
                        speaking = False
                        silence_count = 0

                        time.sleep(0.2)


    except KeyboardInterrupt:

        print("👋 Call ended")

        ws.close()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    main()
