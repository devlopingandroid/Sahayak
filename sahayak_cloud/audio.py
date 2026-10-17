"""Microphone and speaker are attached to the laptop, never the ESP32."""
import queue
import threading
import time
import sys
from collections import deque


class Audio:
    def __init__(self):
        self.jobs = queue.Queue(maxsize=8)
        self.lock = threading.Lock()
        self.error = None
        self.speaking = False
        self.completed = 0
        self.cancel_event = threading.Event()
        threading.Thread(target=self._speaker, daemon=True).start()

    def _speaker(self):
        try:
            if sys.platform == 'win32':
                # Keep COM and the synchronous SAPI voice on this worker thread.
                # This avoids pyttsx3's event loop becoming silent on later jobs.
                import pythoncom
                from win32com.client import Dispatch
                pythoncom.CoInitialize()
                engine = Dispatch('SAPI.SpVoice')
                engine.Rate = -1
                speak = lambda text: engine.Speak(text, 0)
            else:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                def speak(text):
                    engine.say(text)
                    engine.runAndWait()
        except Exception as exc:
            self.error = str(exc)
            return
        while True:
            text = self.jobs.get()
            try:
                with self.lock:
                    self.speaking = True
                    speak(text)
                    self.completed += 1
            except Exception as exc:
                self.error = str(exc)
            finally:
                self.speaking = False
                self.jobs.task_done()

    def speak(self, text):
        text = str(text).strip()
        if not text:
            raise ValueError('There is no answer to read aloud.')
        if self.error:
            raise ValueError(self.error)
        try:
            self.jobs.put_nowait(text[:1500])
        except queue.Full:
            raise ValueError('Speaker queue is busy. Please wait.')

    def listen(self, language='en-IN'):
        if not self.lock.acquire(blocking=False):
            raise ValueError('Laptop audio is busy. Wait until the spoken answer finishes.')
        try:
            import speech_recognition as sr
            import numpy as np
            self.cancel_event.clear()
            recognizer = sr.Recognizer()
            recognizer.operation_timeout = 15
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=.5)
                # Read short chunks so Stop closes the laptop mic promptly.
                seconds_per_chunk = source.CHUNK / source.SAMPLE_RATE
                pre_roll = deque(maxlen=max(1,int(.4 / seconds_per_chunk)))
                chunks=[]
                started=time.monotonic()
                speech_started=None
                last_voice=started
                while True:
                    if self.cancel_event.is_set():
                        raise ValueError('Listening cancelled.')
                    chunk=source.stream.read(source.CHUNK)
                    current=time.monotonic()
                    samples=np.frombuffer(chunk,dtype=np.int16).astype(np.float32)
                    energy=float(np.sqrt(np.mean(samples*samples))) if len(samples) else 0
                    voiced=energy>max(180,recognizer.energy_threshold)
                    if speech_started is None:
                        pre_roll.append(chunk)
                        if voiced:
                            speech_started=current
                            last_voice=current
                            chunks=list(pre_roll)
                        elif current-started>6:
                            raise ValueError('No speech detected. Please try again.')
                    else:
                        chunks.append(chunk)
                        if voiced:
                            last_voice=current
                        if current-last_voice>.85 or current-speech_started>12:
                            break
                audio=sr.AudioData(b''.join(chunks),source.SAMPLE_RATE,source.SAMPLE_WIDTH)
            if self.cancel_event.is_set():
                raise ValueError('Listening cancelled.')
            transcript=recognizer.recognize_google(audio, language=language)
            if self.cancel_event.is_set():
                raise ValueError('Listening cancelled.')
            return transcript
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f'Laptop microphone or speech service: {type(exc).__name__}. Check input device and internet.') from exc
        finally:
            self.lock.release()

    def cancel(self):
        self.cancel_event.set()
