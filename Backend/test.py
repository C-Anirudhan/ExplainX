import sounddevice as sd
import numpy as np

def print_sound_level(indata, frames, time, status):
    volume_norm = np.linalg.norm(indata) * 10
    print(f"|{'#' * int(volume_norm)}", end='\r')

print("\n--- 📊 LIVE AUDIO TEST ---")
print("1. Speak into your Phone.")
print("2. Watch which Device ID shows moving bars (#####).")
print("3. Press Ctrl+C to stop testing a device and move to the next.\n")

devices = sd.query_devices()

for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"\n🎧 Testing Device ID {i}: {dev['name']}")
        try:
            with sd.InputStream(device=i, callback=print_sound_level):
                input(f"   Press Enter to stop testing Device {i}...")
        except:
            print("   ❌ Access Denied (Skipping)")