import websocket
import pyaudio
import keyboard
import time
import threading
import io
import soundfile as sf
import sounddevice as sd


WS_URL = "ws://localhost:8000/ws/voice"

RATE = 16000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1


# =============================
# AUDIO PLAYER THREAD
# =============================

def listen_server(ws):

    while True:

        try:
            audio_bytes = ws.recv()

            if not audio_bytes:
                continue

            # Decode wav/pcm
            data, sr = sf.read(
                io.BytesIO(audio_bytes),
                dtype="float32"
            )

            sd.play(data, sr)
            sd.wait()

        except Exception as e:
            print("🔇 Audio receive error:", e)
            break


# =============================
# MAIN
# =============================

def list_mics(p):

    print("\n🎙️ Available Microphones:\n")

    for i in range(p.get_device_count()):

        info = p.get_device_info_by_index(i)

        if info["maxInputChannels"] > 0:
            print(i, ":", info["name"])


def main():

    ws = websocket.WebSocket()
    ws.connect(WS_URL)

    print("✅ Connected to server")

    # Start listener thread
    listen_thread = threading.Thread(
        target=listen_server,
        args=(ws,),
        daemon=True
    )
    listen_thread.start()


    p = pyaudio.PyAudio()

    list_mics(p)

    mic_id = int(input("\nEnter mic ID: "))


    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=mic_id,
        frames_per_buffer=CHUNK
    )


    print("\n🎤 Hold SPACE to talk. Release to send.\n")


    try:

        while True:

            keyboard.wait("space")

            print("🎙️ Recording...")

            while keyboard.is_pressed("space"):

                data = stream.read(
                    CHUNK,
                    exception_on_overflow=False
                )

                ws.send_binary(data)


            # End of speech
            ws.send_binary(b"__END__")

            print("📤 Sent. Waiting reply...\n")

            time.sleep(0.3)


    except KeyboardInterrupt:

        print("👋 Closing...")

        ws.close()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    main()
