import speech_recognition as sr

r = sr.Recognizer()

device_index = 2   # 👈 change this number to test

with sr.Microphone(device_index=device_index) as source:
    print(f"🎤 Using mic index {device_index}")
    r.adjust_for_ambient_noise(source, duration=1)
    print("Speak now...")
    audio = r.listen(source, timeout=5, phrase_time_limit=5)

print("Processing...")
print("You said:", r.recognize_google(audio))