// Remote dashboards use this browser's microphone and speaker, never server audio.
let activeRecognition: any = null;
export function browserMicrophoneAvailable() {
  return typeof window !== "undefined" && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
}
export function speakInBrowser(text: string, language = "en-IN") {
  if (!("speechSynthesis" in window)) throw new Error("Spoken feedback is unavailable in this browser.");
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = language;
  utterance.rate = .95;
  window.speechSynthesis.speak(utterance);
}
export function stopBrowserListening() {
  activeRecognition?.abort();
}
export function listenInBrowser(language = "en-IN"): Promise<string> {
  if (!browserMicrophoneAvailable()) return Promise.reject(new Error("Use Chrome or Edge for microphone input, or type your question."));
  if (activeRecognition) return Promise.reject(new Error("The microphone is already listening."));
  window.speechSynthesis?.cancel();
  return new Promise((resolve, reject) => {
    const Constructor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new Constructor();
    activeRecognition = recognition;
    recognition.lang = language;
    recognition.continuous = false;
    recognition.interimResults = false;
    let settled = false;
    const finish = (text?: string, error?: string) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      activeRecognition = null;
      recognition.abort();
      error ? reject(new Error(error)) : resolve(text!);
    };
    const timeout = setTimeout(() => finish(undefined, "No speech received. Please try again or type your question."), 18000);
    recognition.onresult = (event: any) => {
      const text = event.results?.[0]?.[0]?.transcript?.trim();
      finish(text, text ? undefined : "I could not understand that. Please try again.");
    };
    recognition.onerror = (event: any) => finish(undefined,
      event.error === "not-allowed" ? "Allow microphone access for this dashboard in your browser."
      : event.error === "audio-capture" ? "No microphone is available on this device."
      : event.error === "aborted" ? "Listening cancelled."
      : event.error === "network" ? "Speech recognition could not connect. Check your internet connection."
      : "I could not understand the speech. Please try again or type the name.");
    recognition.onend = () => finish(undefined, "No speech received. Please try again.");
    try { recognition.start(); } catch { finish(undefined, "The browser microphone could not start. Please try again."); }
  });
}
