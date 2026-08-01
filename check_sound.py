import sounddevice as sd
try:
    print(sd.query_devices())
    print("\nDefault device:", sd.default.device)
except Exception as e:
    print("Error querying devices:", e)
