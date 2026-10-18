import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowUpRight,
  ArrowRight,
  AudioLines,
  Bell,
  BookOpen,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Heart,
  HelpCircle,
  Home,
  ImagePlus,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  Mic,
  Pause,
  Play,
  Plus,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound,
  Volume2,
  Wifi,
  X,
} from "lucide-react";
import { api, dateTime, timeOnly, Memory, Person, Routine } from "./api";
import { browserMicrophoneAvailable, listenInBrowser, speakInBrowser, stopBrowserListening } from "./browser-audio";

const pages = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "ask", label: "Ask SAHAYAK", icon: AudioLines },
  { id: "people", label: "Familiar people", icon: UsersRound },
  { id: "memories", label: "Memory timeline", icon: BookOpen },
  { id: "routines", label: "Daily routines", icon: Clock3 },
  { id: "support", label: "Care & reassurance", icon: Heart },
];
const pageCopy: Record<string, string[]> = {
  overview: [
    "A little support. A more familiar day.",
    "Your memories, connected.",
  ],
  ask: ["A familiar answer, whenever you need it.", "Let’s remember together."],
  people: [
    "The people who make life feel like home.",
    "Familiar faces. Meaningful connections.",
  ],
  memories: ["Little moments, ready to remember.", "Your day, remembered."],
  routines: [
    "One manageable step at a time.",
    "A gentle rhythm for every day.",
  ],
  support: [
    "Comfort, connection and a helping hand.",
    "Care that stays close.",
  ],
  settings: [
    "Make SAHAYAK feel right for you.",
    "Your device. Your preferences.",
  ],
  patient: [
    "Take your time. We’re here to help.",
    "Hello. Let’s take today together.",
  ],
};
function Orbit() {
  return (
    <div className="orbit" aria-hidden="true">
      <div className="orbit-ring one" />
      <div className="orbit-ring two" />
      <div className="orb">
        <span>✳</span>
      </div>
      <span className="orb-dot" />
    </div>
  );
}
function Empty({
  icon: Icon = BookOpen,
  title,
  children,
}: {
  icon?: any;
  title: string;
  children?: any;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={25} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: any;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    const first = ref.current?.querySelector<HTMLElement>(
      "input,button,textarea,select",
    );
    first?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const els = [
          ...ref.current!.querySelectorAll<HTMLElement>(
            'button,input,select,textarea,[tabindex="0"]',
          ),
        ].filter((x) => !x.hasAttribute("disabled"));
        const a = els[0],
          b = els.at(-1);
        if (e.shiftKey && document.activeElement === a) {
          e.preventDefault();
          b?.focus();
        } else if (!e.shiftKey && document.activeElement === b) {
          e.preventDefault();
          a?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      before?.focus();
    };
  }, []);
  return (
    <div className="modal-backdrop" onClick={close}>
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="modal"
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="section-head">
          <h2>{title}</h2>
          <button className="icon-button" aria-label="Close" onClick={close}>
            <X />
          </button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState<any>(null),
    [password, setPassword] = useState(""),
    [page, setPage] = useState("overview");
  const [status, setStatus] = useState<any>(null),
    [settings, setSettings] = useState<any>(null),
    [people, setPeople] = useState<Person[]>([]),
    [events, setEvents] = useState<Memory[]>([]),
    [routines, setRoutines] = useState<Routine[]>([]),
    [answers, setAnswers] = useState<any[]>([]),
    [helps, setHelps] = useState<any[]>([]),
    [recap, setRecap] = useState<any>({ events: [], routines: [] }),
    [annotated, setAnnotated] = useState(false);
  const [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false),
    [sidebar, setSidebar] = useState(false),
    [search, setSearch] = useState("");
  const [modal, setModal] = useState<string | null>(null),
    [selected, setSelected] = useState<Person | null>(null),
    [selectedEvent, setSelectedEvent] = useState<Memory | null>(null);
  const [question, setQuestion] = useState(""),
    [chat, setChat] = useState<any[]>([]),
    [listening, setListening] = useState(false);
  const [form, setForm] = useState<any>({}),
    [draft, setDraft] = useState<any>(null),
    [token, setToken] = useState("");
  const [aiKey, setAiKey] = useState("");
  const [recordName, setRecordName] = useState(""),
    [recordRelationship, setRecordRelationship] = useState("");
  const recordingPrompt = useRef("");
  const chatEnd = useRef<HTMLDivElement>(null),
    reminder = useRef(new Set<string>()),
    refreshPending = useRef(false);
  const refresh = useCallback(async () => {
    if (refreshPending.current) return;
    refreshPending.current = true;
    try {
      const [s, p, e, r, a, h, summary] = await Promise.all([
        api("/status"),
        api<Person[]>("/people"),
        api<Memory[]>("/events"),
        api<Routine[]>("/routines"),
        api<any[]>("/answers"),
        api<any[]>("/help"),
        api("/recap"),
      ]);
      setStatus(s);
      setPeople(p);
      setEvents(e);
      setRoutines(r);
      setAnswers(a);
      setHelps(h);
      setRecap(summary);
    } finally {
      refreshPending.current = false;
    }
  }, []);
  const run = async (fn: () => Promise<any>, message?: string) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      if (message) setToast(message);
      await refresh();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    api("/auth")
      .then(setAuth)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!auth?.authenticated) return;
    refresh().catch((e) => setError(e.message));
    api("/settings").then((s) => {
      setSettings(s);
      setDraft(s);
    });
    const id = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      1000,
    );
    return () => clearInterval(id);
  }, [auth?.authenticated, refresh]);
  useEffect(() => {
    if (toast) {
      const id = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(id);
    }
  }, [toast]);
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [chat]);
  useEffect(() => {
    const recording = status?.recording;
    if (!recording || recording.state === "saved") return;
    setModal("record");
    if (recording.state === "awaiting_name" && recordingPrompt.current !== recording.id) {
      recordingPrompt.current = recording.id;
      speakFeedback("The photos are ready. What name should I give this person? You can type a name or press Say the name.")
        .catch((e) => setError(e.message));
    }
  }, [status?.recording?.id, status?.recording?.state]);
  useEffect(() => {
    const time = new Date().toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
    });
    for (const r of routines) {
      const key = new Date().toDateString() + r.id;
      if (
        r.enabled &&
        r.time === time &&
        r.step < r.steps.length &&
        !reminder.current.has(key)
      ) {
        reminder.current.add(key);
        setToast(`It’s time for ${r.title}. Open Daily routines for guidance.`);
      }
    }
  }, [routines]);
  const navigate = (id: string) => {
    setPage(id);
    setSidebar(false);
    setSearch("");
  };
  const browserAudio = !!status?.cloud;
  const microphoneAvailable = !!status?.local_audio || (browserAudio && browserMicrophoneAvailable());
  const storagePlace = status?.cloud ? "your private cloud server" : "this laptop";
  const speakFeedback = async (text: string) => {
    if (status?.local_audio) await api("/audio/speak", "POST", { text });
    else if (browserAudio) speakInBrowser(text, settings?.language || "en-IN");
  };
  const stopListening = () => {
    if (browserAudio) stopBrowserListening();
    else api("/audio/cancel", "POST", {}).catch((e) => setError(e.message));
  };
  const say = (text: string) => run(() => speakFeedback(text));
  const chatHistory = () => chat.slice(-12).map((m) => ({
    role: m.role,
    content: String(m.role === "assistant" ? m.response : m.text).slice(0, 2000),
  }));
  const startRecording = () => run(async () => {
    const recording = await api("/enrollment/start", "POST", {});
    setRecordName("");
    setRecordRelationship("");
    setStatus((s: any) => ({ ...s, recording }));
    setModal("record");
    await speakFeedback("Keep one person in the camera view. Slowly turn your face left and right. I will ask for a name after eight clear photos.");
  });
  const saveRecording = async (name: string) => {
    const result = await api(`/enrollment/${status.recording.id}/finish`, "POST", {
      name, relationship: recordRelationship,
    });
    setModal(null);
    setToast(`${result.name} saved with ${result.samples} photos on ${storagePlace}. Recognition is enabled.`);
    await speakFeedback(`${result.name} has been saved and is ready for recognition.`);
  };
  const sayRecordingName = async () => {
    if (busy || listening) return;
    setListening(true);
    await run(async () => {
      const result = browserAudio ? { text: await listenInBrowser(settings?.language || "en-IN") }
        : await api("/audio/listen", "POST", { purpose: "person_name" });
      const name = result.text.replace(/^(?:(?:his|her|their|the person's) name is|the name is|name is|call (?:him|her|them))\s+/i, "").replace(/[.!?]+$/, "").trim();
      setRecordName(name);
      await saveRecording(name);
    });
    setListening(false);
  };
  const ask = async (text = question) => {
    if (!text.trim() || busy || listening) return;
    setQuestion("");
    setChat((c) => [...c, { role: "user", text }]);
    await run(async () => {
      const result = await api("/query", "POST", { text, history: chatHistory() });
      if (result.recording) {
        setRecordName(""); setRecordRelationship("");
        setStatus((s: any) => ({ ...s, recording: result.recording }));
        setModal("record");
      }
      setChat((c) => [...c, { role: "assistant", ...result }]);
      await speakFeedback(result.response);
    });
  };
  const listen = async () => {
    if (busy) return;
    setListening(true);
    await run(async () => {
      let result;
      if (browserAudio) {
        const text = await listenInBrowser(settings?.language || "en-IN");
        result = { ...await api("/query", "POST", { text, history: chatHistory() }), text };
      } else result = await api("/audio/listen", "POST", { history: chatHistory() });
      if (result.recording) {
        setRecordName(""); setRecordRelationship("");
        setStatus((s: any) => ({ ...s, recording: result.recording }));
        setModal("record");
      } else if (page === "overview") {
        navigate("ask");
      }
      setChat((c) => [
        ...c,
        { role: "user", text: result.text },
        { role: "assistant", ...result },
      ]);
      await speakFeedback(result.response);
    });
    setListening(false);
  };
  const help = () =>
    run(async () => {
      const r = await api("/help", "POST", {
        message: "I need assistance. Please check on me.",
      });
      setToast(`Help request saved. Telegram: ${r.delivery}.`);
    });
  const sendPhoto = (event: Memory) =>
    run(
      () => api("/telegram", "POST", { event_id: event.id }),
      "Photo queued. Check delivery status in Settings.",
    );
  const device = status?.devices?.[0],
    online = status?.devices?.some((d: any) => d.online);
  const filtered = events.filter((e) =>
    [...e.objects, ...e.people.map((p) => p.name), e.location || ""]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const active = routines.filter((r) => r.enabled && r.step < r.steps.length),
    latest = events[0];
  const authSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/auth", "POST", { password });
      setPassword("");
      setAuth(await api("/auth"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (!auth?.authenticated)
    return (
      <div className="auth-shell">
        <div className="auth-art">
          <div className="brand">
            <span className="brand-symbol">✳</span> sahayak
            <span className="brand-period">.</span>
          </div>
          <div>
            <span className="eyebrow">A LITTLE SUPPORT, EVERY DAY</span>
            <h1>
              For the moments
              <br />
              that matter.
            </h1>
            <p>
              A familiar face. A remembered object.
              <br />A helping hand, always close.
            </p>
            <Orbit />
          </div>
          <small>Personal memory & daily assistance</small>
        </div>
        <main className="auth-form">
          <span className="badge">
            <ShieldCheck size={14} /> Stored on {auth?.cloud ? "your private cloud server" : "your laptop"}
          </span>
          <h2>
            {auth?.configured
              ? "Welcome back."
              : "Make a little space for care."}
          </h2>
          <p>
            {auth?.configured
              ? "Sign in to your SAHAYAK caretaker dashboard."
              : "Create a caretaker password to keep personal memories private."}
          </p>
          <form onSubmit={authSubmit}>
            <label>
              Caretaker password
              <input
                autoFocus
                type="password"
                minLength={auth?.configured ? 1 : 10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={
                  auth?.configured ? "current-password" : "new-password"
                }
                placeholder={
                  auth?.configured
                    ? "Enter your password"
                    : "At least 10 characters"
                }
              />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button className="primary wide" disabled={busy || !auth}>
              {busy
                ? "Please wait…"
                : auth?.configured
                  ? "Open my dashboard"
                  : "Create my care space"}
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="fine">
            {auth?.cloud
              ? "Recognition and primary storage run on your private cloud server. The dashboard uses this device’s microphone and speaker. Gemini, speech recognition and Telegram use external services."
              : "Recognition and primary storage run on your laptop. When using the hosted dashboard, requested photos and data pass through Cloudflare and Vercel. Speech recognition and Telegram use external services."}
          </p>
        </main>
      </div>
    );

  return (
    <div className={"app " + (page === "patient" ? "patient-mode" : "")}>
      <aside className={"sidebar " + (sidebar ? "open" : "")}>
        <a
          className="brand"
          href="#overview"
          onClick={() => navigate("overview")}
        >
          <span className="brand-symbol">✳</span> sahayak
          <span className="brand-period">.</span>
        </a>
        <span className="nav-label">YOUR CARE SPACE</span>
        <nav>
          {pages.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => navigate(id)}
              className={page === id ? "active" : ""}
            >
              <Icon size={18} />
              {label}
              {id === "support" &&
                helps.some((h) => h.status === "requested") && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Heart size={21} />
          <p>
            A little help remembering.
            <br />
            More room for living.
          </p>
          <span>Your memories stay on {storagePlace}.</span>
        </div>
        <div className="sidebar-bottom">
          <button
            className={page === "settings" ? "active" : ""}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={18} />
            Device & settings
          </button>
          <button
            onClick={() =>
              navigate(page === "patient" ? "overview" : "patient")
            }
          >
            <UserRound size={18} />
            {page === "patient" ? "Caretaker dashboard" : "Open patient view"}
            <ArrowUpRight size={15} />
          </button>
          <div className="profile">
            <span>{(settings?.patient_name || "S")[0]}</span>
            <div>
              <b>{settings?.patient_name || "SAHAYAK"}</b>
              <small>Personal care space</small>
            </div>
            <button
              aria-label="Sign out"
              onClick={async () => {
                await api("/auth", "DELETE");
                setAuth(await api("/auth"));
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile"
              aria-label="Toggle navigation"
              onClick={() => setSidebar(!sidebar)}
            >
              <Menu size={20} />
            </button>
            <span>My care space</span>
            <span>/</span>
            <b>
              {page === "settings"
                ? "Device & settings"
                : page === "patient"
                  ? "Patient view"
                  : pages.find((p) => p.id === page)?.label}
            </b>
          </div>
          <div className="top-actions">
            <span className={"connection " + (online ? "connected" : "")}>
              <i />
              {online ? "Camera connected" : "Camera not connected"}
            </span>
            <button className="primary small" onClick={() => navigate("ask")}>
              <Mic size={15} />
              Ask SAHAYAK
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {page === "overview"
                  ? "YOUR DAILY COMPANION"
                  : "PERSONAL MEMORY & CARE"}
              </span>
              <h1>{pageCopy[page][1]}</h1>
              <p>{pageCopy[page][0]}</p>
            </div>
            <span className="date-chip">
              {new Date().toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
          <div className="context-line">
            <span>
              <i />
              Personal memories. Grounded in what was recorded.
            </span>
            <span className="badge">
              <ShieldCheck size={12} />
              {status?.cloud ? "Cloud processing" : "Laptop processing"}
            </span>
          </div>
          {error && (
            <div className="error inline" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <AnimatePresence mode="wait">
            <motion.div
              key={page}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.23 }}
            >
              {page === "overview" && (
                <>
                  <section className="card record-home">
                    <div>
                      <h3>Remember someone new</h3>
                      <p>Capture eight clear face photos, then give the person a name. Everything is saved on {storagePlace}.</p>
                    </div>
                    <div className="modal-actions">
                      <button className="primary" disabled={busy || !!status?.recording && status.recording.state !== "saved"}
                        onClick={startRecording}><Camera size={17} /> Record a person</button>
                      <button className="secondary" disabled={busy || listening || !microphoneAvailable}
                        onClick={listen}><Mic size={17} /> {listening ? "Listening…" : "Say “Record a person”"}</button>
                      {status?.recording && status.recording.state !== "saved" &&
                        <button className="text-button" onClick={() => setModal("record")}>Continue recording</button>}
                    </div>
                    <p className="fine">Press the microphone button before speaking. Keep one consenting person in view and slowly vary their face angle.</p>
                  </section>
                  <div className="hero-grid">
                    <section className="hero card">
                      <div className="hero-copy">
                        <span className="eyebrow">
                          A FAMILIAR WORLD, A LITTLE CLOSER
                        </span>
                        <h2>
                          A moment seen.
                          <br />A memory kept.
                        </h2>
                        <p>
                          Find familiar faces, everyday belongings
                          <br className="desktop" /> and a little guidance for
                          what’s next.
                        </p>
                        <button
                          className="dark"
                          onClick={() => navigate("ask")}
                        >
                          Let’s remember together
                          <ArrowUpRight size={17} />
                        </button>
                        <span className="hero-foot">
                          <Sparkles size={14} />
                          Small moments. Meaningful support.
                        </span>
                      </div>
                      <Orbit />
                    </section>
                    <section className="camera-card card">
                      <div className="section-head">
                        <span className="eyebrow">
                          <Camera size={14} />
                          YOUR CAMERA
                        </span>
                        <span
                          className={"status-dot " + (online ? "green" : "")}
                        />
                      </div>
                      {device?.image_url ? (
                        <div className="camera-preview">
                          <img
                            loading="lazy"
                            src={device.image_url + "?t=" + device.last_seen}
                            alt="Latest ESP32 camera capture"
                          />
                          {!online && (
                            <span className="image-label">
                              Last received image · offline
                            </span>
                          )}
                        </div>
                      ) : (
                        <div className="camera-placeholder">
                          <Camera size={36} />
                          <span>Ready when you are</span>
                        </div>
                      )}
                      <h3>
                        {online
                          ? "Your surroundings, connected."
                          : "Waiting for your ESP32."}
                      </h3>
                      <p>
                        {device
                          ? `Last received ${dateTime(device.last_seen)}`
                          : "Connect your camera over Wi-Fi to start recording moments."}
                      </p>
                      <button
                        className="text-button"
                        onClick={() => navigate("settings")}
                      >
                        View device settings
                        <ArrowUpRight size={15} />
                      </button>
                    </section>
                  </div>
                  <div className="stats-grid">
                    {[
                      {
                        title: "Familiar people",
                        value: status?.people_count ?? "—",
                        unit: "people enrolled",
                        icon: UsersRound,
                        sub: "The faces that feel like home",
                        go: "people",
                        color: "peach",
                      },
                      {
                        title: "Moments remembered",
                        value: status?.event_count ?? "—",
                        unit: "saved observations",
                        icon: BookOpen,
                        sub: `${status?.today_events ?? 0} moments recorded today`,
                        go: "memories",
                        color: "lavender",
                      },
                      {
                        title: "A gentle daily rhythm",
                        value: active.length,
                        unit: "routines remaining",
                        icon: Clock3,
                        sub: "One manageable step at a time",
                        go: "routines",
                        color: "mint",
                      },
                    ].map((s) => (
                      <button
                        className={"stat card " + s.color}
                        key={s.title}
                        onClick={() => navigate(s.go)}
                      >
                        <div className="section-head">
                          <h3>{s.title}</h3>
                          <s.icon size={21} />
                        </div>
                        <div className="stat-number">
                          {s.value}
                          <span>{s.unit}</span>
                        </div>
                        <p>{s.sub}</p>
                        <ArrowUpRight className="stat-arrow" size={17} />
                      </button>
                    ))}
                  </div>
                  <div className="lower-grid">
                    <section className="card moments">
                      <div className="section-head">
                        <div>
                          <h3>Little moments from your day</h3>
                          <p>A record to come back to.</p>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => navigate("memories")}
                        >
                          View all
                          <ArrowUpRight size={16} />
                        </button>
                      </div>
                      {events.length ? (
                        <div className="moment-list">
                          {events.slice(0, 4).map((e) => (
                            <button
                              className="moment"
                              onClick={() => setSelectedEvent(e)}
                              key={e.id}
                            >
                              <span className="moment-icon">
                                {e.people.length ? (
                                  <UsersRound size={18} />
                                ) : (
                                  <Camera size={18} />
                                )}
                              </span>
                              <span>
                                <b>
                                  {[
                                    ...e.people.map((p) => p.name),
                                    ...e.objects.slice(0, 3),
                                  ].join(", ") || "Saved observation"}
                                </b>
                                <small>
                                  {e.location || "Place unconfirmed"} ·{" "}
                                  {e.source === "legacy import"
                                    ? "Imported memory"
                                    : "Camera observation"}
                                </small>
                              </span>
                              <time>{dateTime(e.last_seen)}</time>
                              <ChevronRight size={16} />
                            </button>
                          ))}
                        </div>
                      ) : (
                        <Empty title="Your story starts with a moment.">
                          Camera sightings will appear here once your device is
                          connected.
                        </Empty>
                      )}
                    </section>
                    <section className="care-card card">
                      <span className="eyebrow">ONE STEP AT A TIME</span>
                      <h2>
                        A little guidance.
                        <br />A familiar rhythm.
                      </h2>
                      <p>
                        {active[0]
                          ? `Next: ${active[0].title} at ${active[0].time}`
                          : "Build a routine around the little things that make a day feel familiar."}
                      </p>
                      <button
                        className="dark"
                        onClick={() => navigate("routines")}
                      >
                        {active.length
                          ? "See my next step"
                          : "Create a daily routine"}
                        <ArrowUpRight size={16} />
                      </button>
                      <span className="care-flower" aria-hidden="true">
                        ✺
                      </span>
                    </section>
                  </div>
                  <section className="card quick-ask">
                    <span className="quick-icon">
                      <Mic size={24} />
                    </span>
                    <div>
                      <h3>A question on your mind?</h3>
                      <p>
                        “Have you seen my phone?” or “Where was Tanish last
                        seen?”
                      </p>
                    </div>
                    <button className="primary" onClick={() => navigate("ask")}>
                      Ask away
                      <ArrowRight size={17} />
                    </button>
                  </section>
                </>
              )}
              {(page === "ask" || page === "patient") && (
                <>
                  {page === "patient" && (
                    <>
                      <div className="orientation card">
                        <Home size={30} />
                        <div>
                          <span className="eyebrow">RIGHT HERE, RIGHT NOW</span>
                          <h2>
                            {new Date().toLocaleDateString("en-IN", {
                              weekday: "long",
                              day: "numeric",
                              month: "long",
                            })}
                          </h2>
                          <p>
                            {settings?.room
                              ? `Camera location: ${settings.room}`
                              : "Your caretaker can help you confirm where you are."}
                          </p>
                        </div>
                      </div>
                      <div className="patient-actions">
                        <button
                          className="card"
                          onClick={() => ask("Who is this?")}
                        >
                          <UsersRound />
                          Who is this?
                        </button>
                        <button
                          className="card"
                          onClick={() => ask("Have you seen my phone?")}
                        >
                          <Search />
                          Find my phone
                        </button>
                        <button
                          className="card"
                          onClick={() => ask("What should I do next?")}
                        >
                          <Clock3 />
                          My next activity
                        </button>
                        <button
                          className="card help-action"
                          disabled={busy}
                          onClick={help}
                        >
                          <Heart />I need help
                        </button>
                      </div>
                    </>
                  )}
                  <section className="card assistant">
                    <div className="assistant-header">
                      <span className="assistant-logo">✳</span>
                      <div>
                        <h3>Your memory companion</h3>
                        <p>
                          <i />
                          Answers from recorded memories and approved
                          information
                        </p>
                      </div>
                      <span className="badge">Laptop mic & speaker</span>
                    </div>
                    <div className="conversation" aria-live="polite">
                      {!chat.length ? (
                        <div className="assistant-welcome">
                          <span>✳</span>
                          <h2>What would you like to remember?</h2>
                          <p>
                            Ask about a familiar person, an everyday object,
                            <br />
                            or your next activity. Take your time.
                          </p>
                          <div className="suggestions">
                            {[
                              "Have you seen my phone?",
                              "Who is this?",
                              "What should I do next?",
                            ].map((q) => (
                              <button
                                key={q}
                                disabled={busy}
                                onClick={() => ask(q)}
                              >
                                {q}
                                <ArrowUpRight size={14} />
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : (
                        chat.map((m, i) => (
                          <div className={"message " + m.role} key={i}>
                            <span className="message-avatar">
                              {m.role === "user" ? (
                                <UserRound size={17} />
                              ) : (
                                "✳"
                              )}
                            </span>
                            <div>
                              <p>{m.role === "assistant" ? m.response : m.text}</p>
                              {m.ai_notice && <small className="fine">{m.ai_notice} Using local assistance.</small>}
                              {m.event && (
                                <div className="answer-evidence">
                                  {m.event.image_url && (
                                    <img
                                      loading="lazy"
                                      src={m.event.image_url}
                                      alt="Evidence for the recorded sighting"
                                    />
                                  )}
                                  <small>
                                    {dateTime(m.event.last_seen)} ·{" "}
                                    {m.event.location || "Place unconfirmed"}
                                  </small>
                                  <div>
                                    <button
                                      className="text-button"
                                      disabled={busy}
                                      onClick={() => setSelectedEvent(m.event)}
                                    >
                                      View memory
                                      <ArrowUpRight size={14} />
                                    </button>
                                    <button
                                      className="text-button"
                                      disabled={busy}
                                      onClick={() => sendPhoto(m.event)}
                                    >
                                      Send photo
                                      <Send size={14} />
                                    </button>
                                  </div>
                                </div>
                              )}
                              {m.routine && (
                                <div className="answer-routine">
                                  <b>{m.routine.title}</b>
                                  <button
                                    className="primary small"
                                    onClick={() => navigate("routines")}
                                  >
                                    Open routine
                                    <ArrowRight size={14} />
                                  </button>
                                </div>
                              )}
                              {m.role === "assistant" && (
                                <button
                                  className="text-button"
                                  disabled={busy}
                                  onClick={() => say(m.response)}
                                >
                                  <Volume2 size={14} />
                                  Repeat aloud
                                </button>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                      {listening && (
                        <div className="listening">
                          <AudioLines className="pulse" />
                          Listening through your microphone…
                        </div>
                      )}
                      <div ref={chatEnd} />
                    </div>
                    <form
                      className="composer"
                      onSubmit={(e) => {
                        e.preventDefault();
                        ask();
                      }}
                    >
                      <button
                        type="button"
                        className={"mic-button " + (listening ? "pulse" : "")}
                        disabled={(busy && !listening) || !microphoneAvailable}
                        onClick={() =>
                          listening
                            ? stopListening()
                            : listen()
                        }
                        aria-label={
                          listening
                            ? "Stop microphone"
                            : "Listen using microphone"
                        }
                      >
                        {listening ? <X size={21} /> : <Mic size={21} />}
                      </button>
                      <input
                        aria-label="Your question"
                        placeholder="Ask Sahayak anything…"
                        maxLength={2000}
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        disabled={busy}
                      />
                      <button
                        className="send-button"
                        aria-label="Send question"
                        disabled={busy || !question.trim()}
                      >
                        <ArrowRight size={20} />
                      </button>
                    </form>
                    <p className="assistant-note">
                      {settings?.ai_enabled && settings?.ai_configured
                        ? "Gemini conversation is enabled. Relevant saved text records are shared with Google. "
                        : "Local assistance. Enable Gemini in Settings for open conversation. "}
                      {status?.local_audio
                        ? "The microphone and spoken feedback use your laptop. Speech recognition needs internet."
                        : browserAudio ? "The microphone and speaker use this browser. Allow microphone access when prompted. Speech recognition needs internet."
                        : "Open localhost on the laptop to use its microphone and speaker."}
                    </p>
                  </section>
                </>
              )}
              {page === "people" && (
                <>
                  <div className="toolbar">
                    <div>
                      <h3>Your circle of familiar faces</h3>
                      <p>
                        Enroll with photos, then review each sample before
                        recognition.
                      </p>
                    </div>
                    <button
                      className="primary"
                      onClick={() => {
                        setForm({
                          name: "",
                          relationship: "",
                          introduction: "",
                        });
                        setModal("person");
                      }}
                    >
                      <Plus size={17} />
                      Add a person
                    </button>
                  </div>
                  {people.length ? (
                    <div className="people-grid">
                      {people.map((p) => (
                        <button
                          className="person-card card"
                          key={p.id}
                          onClick={() => {
                            setSelected(p);
                            setModal("enroll");
                          }}
                        >
                          <div className="person-photo">
                            {p.photo_url ? (
                              <img src={p.photo_url} alt={p.name} />
                            ) : (
                              <UserRound size={42} />
                            )}
                          </div>
                          <span className="badge">
                            {p.approved_samples
                              ? `${p.approved_samples} approved samples`
                              : "Enrollment needed"}
                          </span>
                          <h2>{p.name}</h2>
                          <p>{p.relationship || "Relationship not set"}</p>
                          <div className="person-footer">
                            Manage profile & photos
                            <ArrowUpRight size={16} />
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <section className="card">
                      <Empty
                        icon={UsersRound}
                        title="Start with someone familiar."
                      >
                        Add a name, a relationship and clear photos. Caretaker
                        approval keeps enrollment intentional.
                      </Empty>
                    </section>
                  )}
                  <div className="info-note">
                    <ShieldCheck size={18} />
                    <p>
                      Only approved samples are used for matching. Recognition
                      scores are similarity measures, not probabilities. Unknown
                      faces stay unknown.
                    </p>
                  </div>
                </>
              )}
              {page === "memories" && (
                <>
                  <div className="toolbar">
                    <div>
                      <h3>Your personal memory vault</h3>
                      <p>
                        Past sightings with their original time and evidence.
                      </p>
                    </div>
                    <label className="search-box">
                      <Search size={17} />
                      <input
                        placeholder="Search people, objects, places"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                  </div>
                  {filtered.length ? (
                    <div className="memory-grid">
                      {filtered.map((e) => (
                        <button
                          className="memory-card card"
                          onClick={() => setSelectedEvent(e)}
                          key={e.id}
                        >
                          <div className="memory-photo">
                            {e.image_url ? (
                              <img
                                loading="lazy"
                                src={e.image_url}
                                alt="Recorded sighting"
                                onError={(ev) => {
                                  ev.currentTarget.style.visibility = "hidden";
                                }}
                              />
                            ) : (
                              <Camera size={35} />
                            )}
                            <span className="image-label">
                              {e.verified
                                ? "Caretaker confirmed"
                                : e.source === "legacy import"
                                  ? "Imported observation"
                                  : "Camera observation"}
                            </span>
                          </div>
                          <div className="memory-body">
                            <small>{dateTime(e.last_seen)}</small>
                            <h3>
                              {e.people.map((p) => p.name).join(", ") ||
                                "Everyday surroundings"}
                            </h3>
                            <div className="tags">
                              {e.objects.slice(0, 5).map((o) => (
                                <span key={o}>{o}</span>
                              ))}
                            </div>
                            <p>
                              <MapPin size={14} />
                              {e.location || "Place unconfirmed"}
                              <ArrowUpRight size={16} />
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <section className="card">
                      <Empty
                        icon={Search}
                        title={
                          search
                            ? "No matching memories."
                            : "A space for moments worth remembering."
                        }
                      >
                        {search
                          ? "Try another person or object."
                          : "Connect the ESP32 camera to begin."}
                      </Empty>
                    </section>
                  )}
                </>
              )}
              {page === "routines" && (
                <>
                  <div className="toolbar">
                    <div>
                      <h3>A day made of little steps</h3>
                      <p>Progress is confirmed by you or your caretaker.</p>
                    </div>
                    <button
                      className="primary"
                      onClick={() => {
                        setForm({ title: "", time: "09:00", steps: "" });
                        setModal("routine");
                      }}
                    >
                      <Plus size={17} />
                      Create routine
                    </button>
                  </div>
                  {routines.length ? (
                    <div className="routine-grid">
                      {routines.map((r) => (
                        <section className="card routine-card" key={r.id}>
                          <div className="section-head">
                            <span className="badge">
                              <Clock3 size={13} />
                              {r.time}
                            </span>
                            <button
                              className="icon-button"
                              aria-label={"Edit " + r.title}
                              onClick={() => {
                                setForm({ ...r, steps: r.steps.join("\n") });
                                setModal("routine");
                              }}
                            >
                              <Settings2 size={16} />
                            </button>
                            <button
                              className="icon-button"
                              aria-label={"Remove " + r.title}
                              onClick={() =>
                                run(
                                  () => api("/routines/" + r.id, "DELETE"),
                                  "Routine removed.",
                                )
                              }
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                          <h2>{r.title}</h2>
                          <p>
                            {r.step >= r.steps.length
                              ? "All steps confirmed for today."
                              : `Step ${r.step + 1} of ${r.steps.length}`}
                          </p>
                          <div className="progress-track">
                            <i
                              style={{
                                width: `${(r.step / r.steps.length) * 100}%`,
                              }}
                            />
                          </div>
                          <div className="routine-step">
                            {r.step >= r.steps.length ? (
                              <>
                                <CheckCircle2 size={30} />
                                <h3>All done. Take your time.</h3>
                              </>
                            ) : (
                              <>
                                <span className="step-number">
                                  {r.step + 1}
                                </span>
                                <h3>{r.steps[r.step]}</h3>
                              </>
                            )}
                          </div>
                          <div className="routine-controls">
                            {r.step < r.steps.length ? (
                              <>
                                <button
                                  className="primary"
                                  disabled={busy}
                                  onClick={() =>
                                    run(() =>
                                      api("/routines/" + r.id, "PATCH", {
                                        action: "done",
                                      }),
                                    )
                                  }
                                >
                                  <Check size={16} />
                                  Done
                                </button>
                                <button
                                  className="secondary"
                                  disabled={busy}
                                  onClick={() => say(r.steps[r.step])}
                                >
                                  <Volume2 size={16} />
                                  Repeat
                                </button>
                                <button
                                  className="icon-button"
                                  aria-label="Get help"
                                  disabled={busy}
                                  onClick={help}
                                >
                                  <HelpCircle size={20} />
                                </button>
                              </>
                            ) : (
                              <button
                                className="secondary"
                                disabled={busy}
                                onClick={() =>
                                  run(() =>
                                    api("/routines/" + r.id, "PATCH", {
                                      action: "reset",
                                    }),
                                  )
                                }
                              >
                                Start again
                              </button>
                            )}
                          </div>
                        </section>
                      ))}
                    </div>
                  ) : (
                    <section className="card">
                      <Empty icon={Clock3} title="Create a familiar rhythm.">
                        Add breakfast, getting ready or another approved
                        activity as a sequence of simple steps.
                      </Empty>
                    </section>
                  )}
                  <div className="info-note">
                    <CheckCircle2 size={18} />
                    <p>
                      Camera observations do not confirm task completion or
                      medication ingestion. Reminders appear while the dashboard
                      is open.
                    </p>
                  </div>
                </>
              )}
              {page === "support" && (
                <>
                  <div className="support-grid">
                    <section className="card">
                      <div className="section-head">
                        <div>
                          <h3>Care, one request at a time</h3>
                          <p>Requests stay visible until acknowledged.</p>
                        </div>
                        <Heart size={23} />
                      </div>
                      <button
                        className="primary"
                        disabled={busy}
                        onClick={help}
                      >
                        Request caretaker help
                        <ArrowUpRight size={17} />
                      </button>
                      {helps.length ? (
                        helps.map((h) => (
                          <div className="help-row" key={h.id}>
                            <span
                              className={
                                "status-dot " +
                                (h.status === "acknowledged" ? "green" : "")
                              }
                            />
                            <div>
                              <b>{h.message}</b>
                              <small>
                                {dateTime(h.created)} · {h.status}
                              </small>
                              <small>
                                Telegram: {h.delivery || "Not configured"}
                              </small>
                              {h.delivery_error && (
                                <small>{h.delivery_error}</small>
                              )}
                            </div>
                            {h.status !== "acknowledged" && (
                              <button
                                className="secondary small"
                                disabled={busy}
                                onClick={() =>
                                  run(
                                    () => api("/help/" + h.id, "PATCH", {}),
                                    "Request acknowledged.",
                                  )
                                }
                              >
                                Acknowledge
                              </button>
                            )}
                          </div>
                        ))
                      ) : (
                        <Empty icon={Heart} title="No assistance requests.">
                          When help is requested, you’ll see its status here.
                        </Empty>
                      )}
                    </section>
                    <section className="card reassurance">
                      <div className="section-head">
                        <div>
                          <h3>A familiar, reassuring answer</h3>
                          <p>Caretaker-approved information.</p>
                        </div>
                        <button
                          className="icon-button"
                          aria-label="Add approved answer"
                          onClick={() => {
                            setForm({ question: "", answer: "", expires: "" });
                            setModal("answer");
                          }}
                        >
                          <Plus />
                        </button>
                      </div>
                      {answers.length ? (
                        answers.map((a) => (
                          <div className="answer-item" key={a.id}>
                            <b>{a.question}</b>
                            <p>{a.answer}</p>
                            <small>
                              {a.expires
                                ? "Valid until " + dateTime(a.expires)
                                : "No expiry set"}
                            </small>
                            <button
                              className="icon-button"
                              aria-label="Remove answer"
                              onClick={() =>
                                run(() => api("/answers/" + a.id, "DELETE"))
                              }
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        ))
                      ) : (
                        <Empty
                          icon={Heart}
                          title="Keep a reassuring answer close."
                        >
                          Add common questions and a calm, approved answer. Set
                          expiry for changing plans.
                        </Empty>
                      )}
                      <button
                        className="text-button"
                        onClick={() => {
                          setForm({ question: "", answer: "", expires: "" });
                          setModal("answer");
                        }}
                      >
                        Add an approved answer
                        <Plus size={15} />
                      </button>
                    </section>
                  </div>
                  <div className="info-note">
                    <Heart size={18} />
                    <p>
                      Repeated questions receive the same patient response.
                      Approved answers match the saved question; expired plans
                      are excluded.
                    </p>
                  </div>
                </>
              )}
              {page === "support" && (
                <section className="card recap-card">
                  <div className="section-head">
                    <div>
                      <h3>A little look back at today</h3>
                      <p>
                        Only caretaker-confirmed observations and explicitly
                        completed routines.
                      </p>
                    </div>
                    <BookOpen size={22} />
                  </div>
                  {!recap.events.length && !recap.routines.length ? (
                    <Empty title="Today’s story is still unfolding.">
                      Confirm a memory or finish a routine to include it in this
                      recap.
                    </Empty>
                  ) : (
                    <div className="moment-list">
                      {recap.routines.map((title: string) => (
                        <div className="moment" key={title}>
                          <CheckCircle2 size={18} />
                          <span>
                            <b>{title}</b>
                            <small>
                              All routine steps explicitly confirmed today.
                            </small>
                          </span>
                        </div>
                      ))}
                      {recap.events.map((event: Memory) => (
                        <button
                          className="moment"
                          key={event.id}
                          onClick={() => setSelectedEvent(event)}
                        >
                          <Camera size={18} />
                          <span>
                            <b>
                              {[
                                ...event.people.map((p) => p.name),
                                ...event.objects,
                              ].join(", ")}
                            </b>
                            <small>
                              {dateTime(event.last_seen)} ·{" "}
                              {event.location || "Place unconfirmed"}
                            </small>
                          </span>
                          <ArrowUpRight size={16} />
                        </button>
                      ))}
                    </div>
                  )}
                </section>
              )}
              {page === "settings" && draft && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    run(async () => {
                      const saved = await api("/settings", "PATCH", {
                        ...draft,
                        telegram_token: token,
                        gemini_api_key: aiKey,
                      });
                      setSettings(saved);
                      setDraft(saved);
                      setToken("");
                      setAiKey("");
                    }, "Preferences saved.");
                  }}
                >
                  <div className="settings-grid">
                    <section className="card settings-card">
                      <h3>Ask Sahayak AI</h3>
                      <p>Natural conversation, follow-up questions and answers using your saved memories.</p>
                      <label>
                        Conversation model
                        <select value={draft.ai_model || "gemini-3.8-flash"}
                          onChange={(e) => setDraft({ ...draft, ai_model: e.target.value })}>
                          <option value="gemini-3.8-flash">Gemini 3.8 Flash · balanced quality and speed</option>
                          <option value="gemini-3.5-flash-lite">Gemini 3.5 Flash-Lite · prioritize speed</option>
                        </select>
                      </label>
                      <label>
                        Gemini API key
                        <input type="password" autoComplete="off" value={aiKey}
                          onChange={(e) => setAiKey(e.target.value)}
                          placeholder={draft.ai_configured ? "Key saved; leave blank to keep" : "Paste your Google AI Studio API key"} />
                      </label>
                      <p className="fine">
                        The key is stored in the backend settings database and is never returned to the dashboard.
                        <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer"> Get a Gemini API key</a>.
                      </p>
                      <label className="switch-row">
                        <input type="checkbox" checked={!!draft.ai_enabled}
                          onChange={(e) => setDraft({ ...draft, ai_enabled: e.target.checked })} />
                        Enable AI conversation
                      </label>
                      <p className="fine">
                        Enabling AI sends your question, up to 12 recent chat messages and a limited text snapshot of enrolled people,
                        sightings, approved answers and routines to Google. Camera photos and face embeddings stay on {storagePlace}.
                        Provider terms and API charges apply. AI can make mistakes. Local assistance stays available during outages.
                      </p>
                      <button type="button" className="secondary" disabled={busy || !draft.ai_configured}
                        onClick={() => run(async () => {
                          const result = await api("/ai/test", "POST", {});
                          setToast(`Gemini connected · ${result.latency_ms} ms. ${result.response}`);
                        })}>
                        Test saved AI connection
                      </button>
                      <p className="fine">Save preferences before testing a new key or model.</p>
                    </section>
                    <section className="card settings-card">
                      <h3>Your personal space</h3>
                      <p>Make daily assistance feel familiar.</p>
                      <label>
                        Patient’s preferred name
                        <input
                          value={draft.patient_name}
                          onChange={(e) =>
                            setDraft({ ...draft, patient_name: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        Camera room label
                        <input
                          placeholder="Leave empty if location is unknown"
                          value={draft.room}
                          onChange={(e) =>
                            setDraft({ ...draft, room: e.target.value })
                          }
                        />
                      </label>
                      <p className="fine">
                        Use a room label only for a fixed camera. A wearable
                        camera cannot establish its room from this label.
                      </p>
                      <label>
                        Speech recognition language
                        <select
                          value={draft.language}
                          onChange={(e) =>
                            setDraft({ ...draft, language: e.target.value })
                          }
                        >
                          <option value="en-IN">English (India)</option>
                          <option value="hi-IN">Hindi (India)</option>
                        </select>
                      </label>
                      <label>
                        Personal introduction
                        <textarea
                          value={draft.patient_introduction}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              patient_introduction: e.target.value,
                            })
                          }
                          placeholder="A short, caretaker-approved personal introduction"
                        />
                      </label>
                    </section>
                    <section className="card settings-card">
                      <h3>Camera & recognition</h3>
                      <p>All recognition runs on {storagePlace}.</p>
                      <div className="answer-evidence">
                        <h4>Camera Wi-Fi setup</h4>
                        <p>
                          Change the camera network and laptop server address
                          without uploading firmware again.
                        </p>
                        {(status?.devices || []).filter((d: any) => d.wifi_setup_url).map((d: any) => (
                          <a className="text-button" href={d.wifi_setup_url} key={d.id} target="_blank" rel="noopener noreferrer">
                            <Wifi size={15} /> Open {d.id} Wi-Fi setup <ArrowUpRight size={14} />
                          </a>
                        ))}
                        <p className="fine">
                          Sign in as caretaker with your camera setup password.
                          If the camera cannot connect for 30 seconds, join its
                          SAHAYAK-Setup Wi-Fi network and open http://192.168.4.1.
                          Use the same setup password for the hotspot and page.
                          Your new Wi-Fi must support 2.4 GHz.
                        </p>
                      </div>
                      <label>
                        Camera orientation
                        <select
                          value={draft.camera_rotation ?? 180}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              camera_rotation: Number(e.target.value),
                            })
                          }
                        >
                          <option value={180}>
                            Rotate 180° · inverted camera
                          </option>
                          <option value={0}>Normal orientation</option>
                        </select>
                      </label>
                      <label>
                        Capture interval in seconds
                        <input
                          type="number"
                          min="1"
                          max="60"
                          value={draft.capture_interval}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              capture_interval: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      <label>
                        Retain camera events for days
                        <input
                          type="number"
                          min="1"
                          max="3650"
                          value={draft.retention_days}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              retention_days: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      <label>
                        Face similarity threshold
                        <input
                          type="number"
                          min="0.35"
                          max="0.9"
                          step="0.01"
                          value={draft.face_threshold}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              face_threshold: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      <label className="switch-row">
                        <input
                          type="checkbox"
                          checked={draft.capture_enabled}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              capture_enabled: e.target.checked,
                            })
                          }
                        />
                        Accept camera frames
                      </label>
                      <label className="switch-row">
                        <input
                          type="checkbox"
                          checked={draft.allow_legacy_upload}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              allow_legacy_upload: e.target.checked,
                            })
                          }
                        />
                        Allow original firmware without device token
                      </label>
                      <p className="fine">
                        Turn legacy compatibility off after installing the
                        updated firmware. Settings apply to the new firmware
                        through device-config polling.
                      </p>
                      <label>
                        Device token
                        <input
                          type="password"
                          value={draft.device_token}
                          readOnly
                          autoComplete="off"
                        />
                      </label>
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => {
                          navigator.clipboard
                            .writeText(draft.device_token)
                            .then(() => setToast("Device token copied."))
                            .catch(() => setError("Clipboard unavailable."));
                        }}
                      >
                        Copy token for firmware
                        <ArrowUpRight size={14} />
                      </button>
                    </section>
                    <section className="card settings-card">
                      <h3>Telegram connection</h3>
                      <p>
                        Selected photos and assistance requests leave the laptop
                        when shared.
                      </p>
                      <label>
                        Bot token
                        <input
                          type="password"
                          autoComplete="off"
                          value={token}
                          onChange={(e) => setToken(e.target.value)}
                          placeholder={
                            draft.telegram_configured
                              ? "Saved securely in local settings; leave blank to keep"
                              : "Token from Telegram BotFather"
                          }
                        />
                      </label>
                      <label>
                        Recipient chat ID
                        <input
                          value={draft.telegram_chat}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              telegram_chat: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label className="switch-row">
                        <input
                          type="checkbox"
                          checked={draft.telegram_enabled}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              telegram_enabled: e.target.checked,
                            })
                          }
                        />
                        Enable Telegram sharing
                      </label>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          run(
                            () => api("/telegram", "POST", {}),
                            "Connection test queued.",
                          )
                        }
                      >
                        <Send size={15} />
                        Send connection test
                      </button>
                      <div className="notification-list">
                        {status?.notifications?.map((n: any) => (
                          <p key={n.id}>
                            <span className="badge">{n.status}</span>{" "}
                            {dateTime(n.created)}
                            {n.error && <small>{n.error}</small>}
                          </p>
                        ))}
                      </div>
                    </section>
                    <section className="card settings-card">
                      <h3>System status</h3>
                      <div className="system-item">
                        <span>Recognition models</span>
                        <b>
                          {status?.vision?.ready
                            ? "Ready"
                            : "Loading / unavailable"}
                        </b>
                      </div>
                      <div className="system-item">
                        <span>Frames processed this session</span>
                        <b>{status?.processed ?? 0}</b>
                      </div>
                      <div className="system-item">
                        <span>Last processing time</span>
                        <b>{status?.last_processing_ms ?? 0} ms</b>
                      </div>
                      <div className="system-item">
                        <span>Frames waiting</span>
                        <b>{status?.queue ?? 0}</b>
                      </div>
                      <div className="system-item">
                        <span>Camera connection</span>
                        <b>
                          {online ? "Receiving frames" : "Waiting for device"}
                        </b>
                      </div>
                      {status?.vision?.error && (
                        <p className="error">{status.vision.error}</p>
                      )}
                      {status?.last_error && (
                        <p className="error">{status.last_error}</p>
                      )}
                      {status?.audio_error && (
                        <p className="error">{status.audio_error}</p>
                      )}
                      <p className="fine">
                        {status?.cloud ? "Microphone and spoken feedback run in this browser. The ESP32 sends photos directly to your configured HTTPS backend."
                          : "Use http://localhost:5000 on the laptop for microphone and speaker. The ESP32 upload address is the laptop’s Wi-Fi IP followed by :5000/upload."}
                      </p>
                      <h4>Supported objects</h4>
                      <div className="tags labels-list">
                        {status?.vision?.labels?.map((l: string) => (
                          <span key={l}>{l}</span>
                        ))}
                      </div>
                    </section>
                  </div>
                  <div className="save-bar">
                    <p>
                      <ShieldCheck size={16} />
                      Changes are stored on {storagePlace}.
                    </p>
                    <button className="primary" disabled={busy}>
                      Save preferences
                      <Check size={17} />
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </AnimatePresence>
          <footer>
            <span>
              <span className="footer-flower">✳</span> SAHAYAK
            </span>
            <p>More familiarity. At your own pace.</p>
            <span>Personal memory & care prototype</span>
          </footer>
        </main>
      </div>
      {error && (modal || selectedEvent) && (
        <div className="toast error-toast" role="alert">
          {error}
          <button
            className="icon-button"
            aria-label="Dismiss error"
            onClick={() => setError("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {toast}
        </div>
      )}
      {modal === "record" && status?.recording && (
        <Modal title="Record someone familiar" close={() => {
          run(async () => { await api(`/enrollment/${status.recording.id}`, "DELETE"); setModal(null); });
        }}>
          {error && <p className="error-banner" role="alert">{error}</p>}
          <p>{status.recording.guidance}</p>
          <p><strong>{status.recording.captured} / {status.recording.target} clear photos</strong></p>
          {status.devices?.find((d: any) => d.id === status.recording.device_id)?.image_url &&
            <div className="enrollment-preview"><img
              src={status.devices.find((d: any) => d.id === status.recording.device_id).image_url + "?t=" + status.devices.find((d: any) => d.id === status.recording.device_id).last_seen}
              alt="Camera view while recording a person" /></div>}
          <div className="record-photos">
            {Array.from({length: status.recording.captured}, (_, i) =>
              <img key={i} src={`/api/enrollment/${status.recording.id}/photos/${i}`} alt={`Selected face photo ${i + 1}`} />)}
          </div>
          {status.recording.state === "awaiting_name" && (
            <form onSubmit={(e) => { e.preventDefault(); run(() => saveRecording(recordName)); }}>
              <h3>What name should I give this person?</h3>
              <label>Name<input autoFocus required maxLength={80} value={recordName}
                onChange={(e) => setRecordName(e.target.value)} placeholder="Person’s name" /></label>
              <label>Relationship (optional)<input maxLength={120} value={recordRelationship}
                onChange={(e) => setRecordRelationship(e.target.value)} placeholder="Daughter, brother, friend…" /></label>
              <p className="fine">Saving the name approves these photos for recognition. You can edit the profile later in Familiar people.</p>
              <div className="modal-actions">
                <button className="primary" disabled={busy || !recordName.trim()}>Save person{status?.cloud ? "" : " on laptop"}</button>
                <button type="button" className="secondary" disabled={busy || listening || !microphoneAvailable}
                  onClick={sayRecordingName}><Mic size={16} /> {listening ? "Listening…" : "Say the name"}</button>
                {listening && <button type="button" className="secondary"
                  onClick={stopListening}>Stop listening</button>}
              </div>
              <p className="fine">Wait for the spoken prompt to finish. Then press “Say the name” and speak only the name into your microphone. If it fails, type the name to save.</p>
            </form>
          )}
          {status.recording.state === "capturing" && <p className="fine">Rejecting blurred, dark and near-duplicate face photos. Keep the same person in view. Capture runs for up to 150 seconds.</p>}
        </Modal>
      )}
      {modal === "person" && (
        <Modal title="Add someone familiar" close={() => setModal(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await api("/people", "POST", form);
                setModal(null);
              }, "Person added. Add and approve photos to enable recognition.");
            }}
          >
            <label>
              Name
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label>
              Relationship
              <input
                placeholder="Son, daughter, friend, caretaker…"
                value={form.relationship}
                onChange={(e) =>
                  setForm({ ...form, relationship: e.target.value })
                }
              />
            </label>
            <label>
              Approved introduction
              <textarea
                placeholder="This is Tanish, your son."
                value={form.introduction}
                onChange={(e) =>
                  setForm({ ...form, introduction: e.target.value })
                }
              />
            </label>
            <button className="primary wide" disabled={busy}>
              Create profile
              <Plus size={16} />
            </button>
          </form>
        </Modal>
      )}
      {modal === "enroll" && selected && (
        <Modal
          title={"Get to know " + selected.name}
          close={() => {
            setModal(null);
            setSelected(null);
          }}
        >
          <p>
            Use clear photos from different angles. Each sample needs your
            review before it is used for recognition.
          </p>
          {device?.image_url && (
            <div className="enrollment-preview">
              <img
                src={device.image_url + "?t=" + device.last_seen}
                alt="Live camera view for face enrollment"
              />
              <p>
                Latest received {timeOnly(device.last_seen)}. Face the camera
                directly and keep one clear face near the centre.
              </p>
            </div>
          )}
          <div className="enroll-actions">
            <label className="secondary file-button">
              <ImagePlus size={17} />
              Upload photo
              <input
                type="file"
                accept="image/jpeg,image/png"
                disabled={busy}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const fd = new FormData();
                  fd.append("image", file);
                  await run(
                    () =>
                      api("/people/" + selected.id + "/samples", "POST", fd),
                    "Sample captured. Review and approve it below.",
                  );
                  e.target.value = "";
                }}
              />
            </label>
            <button
              className="secondary"
              disabled={busy || !online}
              onClick={() =>
                run(
                  () =>
                    api("/people/" + selected.id + "/samples", "POST", {
                      device_id: device?.id,
                    }),
                  "Camera sample captured. Review it below.",
                )
              }
            >
              <Camera size={17} />
              Capture one frame
            </button>
          </div>
          <div className="guided-capture">
            <button
              className="text-button"
              disabled={busy || !online}
              onClick={() =>
                run(
                  () =>
                    api("/people/" + selected.id + "/capture", "POST", {
                      device_id: device?.id,
                    }),
                  "Guided capture started. Slowly turn your head; keep only this person in view.",
                )
              }
            >
              <Play size={15} />
              Start guided capture · 6 samples
            </button>
            {status?.enrollment?.person_id === selected.id && (
              <div>
                <p>
                  {status.enrollment.captured} / {status.enrollment.target}{" "}
                  samples captured. Review each photo below before approval.
                </p>
                <p>
                  {status.enrollment.state === "complete"
                    ? "Capture complete. Approve the correct samples below."
                    : status.enrollment.state === "waiting_for_face"
                      ? "Waiting for one clear face…"
                      : status.enrollment.state === "timed_out"
                        ? "Capture ended. Start again when ready."
                        : "Collecting fresh camera frames…"}
                </p>
                {status.enrollment.error && <p>{status.enrollment.error}</p>}
                <button
                  className="text-button"
                  onClick={() =>
                    run(() =>
                      api("/people/" + selected.id + "/capture", "POST", {
                        stop: true,
                      }),
                    )
                  }
                >
                  <Pause size={14} />
                  End capture session
                </button>
              </div>
            )}
          </div>
          <div className="sample-grid">
            {(people.find((p) => p.id === selected.id)?.samples || []).map(
              (s) => (
                <div className="sample" key={s.id}>
                  <img
                    loading="lazy"
                    src={"/api/samples/" + s.id + "/image"}
                    alt="Face enrollment sample for caretaker review"
                  />
                  <div>
                    <button
                      className={s.approved ? "approved" : "text-button"}
                      disabled={busy}
                      onClick={() =>
                        run(() =>
                          api("/samples/" + s.id, "PATCH", {
                            approved: !s.approved,
                          }),
                        )
                      }
                    >
                      <Check size={14} />
                      {s.approved ? "Approved" : "Approve"}
                    </button>
                    <button
                      className="icon-button"
                      aria-label="Remove sample"
                      disabled={busy}
                      onClick={() =>
                        run(() => api("/samples/" + s.id, "DELETE"))
                      }
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ),
            )}
          </div>
          <div className="edit-profile">
            <label>
              Name
              <input
                defaultValue={selected.name}
                onBlur={(e) => {
                  if (e.target.value !== selected.name)
                    run(async () => {
                      await api("/people/" + selected.id, "PATCH", {
                        name: e.target.value,
                      });
                      setSelected({ ...selected, name: e.target.value });
                    });
                }}
              />
            </label>
            <label>
              Relationship
              <input
                defaultValue={selected.relationship}
                onBlur={(e) => {
                  if (e.target.value !== selected.relationship)
                    run(() =>
                      api("/people/" + selected.id, "PATCH", {
                        relationship: e.target.value,
                      }),
                    );
                }}
              />
            </label>
            <label>
              Introduction
              <textarea
                defaultValue={selected.introduction}
                onBlur={(e) => {
                  if (e.target.value !== selected.introduction)
                    run(() =>
                      api("/people/" + selected.id, "PATCH", {
                        introduction: e.target.value,
                      }),
                    );
                }}
              />
            </label>
            <button
              className="text-button danger"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  await api("/people/" + selected.id, "DELETE");
                  setModal(null);
                }, "Profile removed from recognition.")
              }
            >
              <Trash2 size={15} />
              Remove person from recognition
            </button>
          </div>
        </Modal>
      )}
      {modal === "routine" && (
        <Modal
          title={
            form.id ? "Edit a familiar routine" : "Create a familiar routine"
          }
          close={() => setModal(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await api(
                  form.id ? "/routines/" + form.id : "/routines",
                  form.id ? "PATCH" : "POST",
                  {
                    ...form,
                    steps: form.steps
                      .split("\n")
                      .map((s: string) => s.trim())
                      .filter(Boolean),
                  },
                );
                setModal(null);
              }, "Routine saved.");
            }}
          >
            <label>
              Routine name
              <input
                required
                placeholder="Morning breakfast"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </label>
            <label>
              Time
              <input
                type="time"
                required
                value={form.time}
                onChange={(e) => setForm({ ...form, time: e.target.value })}
              />
            </label>
            <label>
              Steps, one per line
              <textarea
                rows={5}
                required
                placeholder={
                  "Go to the dining table.\nSit comfortably.\nAsk your caretaker for breakfast."
                }
                value={form.steps}
                onChange={(e) => setForm({ ...form, steps: e.target.value })}
              />
            </label>
            <button className="primary wide" disabled={busy}>
              Save routine
              <Check size={16} />
            </button>
          </form>
        </Modal>
      )}
      {modal === "answer" && (
        <Modal title="Add a reassuring answer" close={() => setModal(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await api("/answers", "POST", {
                  ...form,
                  expires: form.expires
                    ? new Date(form.expires).toISOString()
                    : null,
                });
                setModal(null);
              }, "Approved answer saved.");
            }}
          >
            <label>
              Common question
              <input
                required
                placeholder="When will Tanish visit?"
                value={form.question}
                onChange={(e) => setForm({ ...form, question: e.target.value })}
              />
            </label>
            <label>
              Approved answer
              <textarea
                required
                value={form.answer}
                onChange={(e) => setForm({ ...form, answer: e.target.value })}
              />
            </label>
            <label>
              Expires at, optional
              <input
                type="datetime-local"
                value={form.expires}
                onChange={(e) => setForm({ ...form, expires: e.target.value })}
              />
            </label>
            <button className="primary wide" disabled={busy}>
              Save answer
              <Check size={16} />
            </button>
          </form>
        </Modal>
      )}
      {selectedEvent && (
        <Modal title="A recorded moment" close={() => setSelectedEvent(null)}>
          {selectedEvent.image_url && (
            <img
              loading="lazy"
              className="evidence-full"
              src={selectedEvent.image_url + (annotated ? "?annotated=1" : "")}
              alt="Original evidence image"
            />
          )}
          <label className="switch-row">
            <input
              type="checkbox"
              checked={annotated}
              onChange={(e) => setAnnotated(e.target.checked)}
            />
            Show detected object boxes where available
          </label>
          <p>
            <b>
              {selectedEvent.people.map((p) => p.name).join(", ") ||
                "No familiar person identified"}
            </b>
          </p>
          <p>{selectedEvent.objects.join(", ")}</p>
          <p>
            {dateTime(selectedEvent.last_seen)} ·{" "}
            {selectedEvent.location || "Place unconfirmed"}
          </p>
          <p className="fine">
            {selectedEvent.source} · {selectedEvent.frames} frame(s). A past
            observation does not establish current location, ownership or an
            action.
          </p>
          <label>
            Correct room label
            <input
              defaultValue={selectedEvent.location || ""}
              onBlur={(e) => {
                const value = e.target.value;
                if (value !== (selectedEvent.location || ""))
                  run(async () => {
                    await api("/events/" + selectedEvent.id, "PATCH", {
                      location: value,
                    });
                    setSelectedEvent({ ...selectedEvent, location: value });
                  });
              }}
            />
          </label>
          <label>
            Correct object labels, comma separated
            <input
              defaultValue={selectedEvent.objects.join(", ")}
              onBlur={(e) => {
                const value = e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean);
                if (
                  JSON.stringify(value) !==
                  JSON.stringify(selectedEvent.objects)
                )
                  run(async () => {
                    await api("/events/" + selectedEvent.id, "PATCH", {
                      objects: value,
                    });
                    setSelectedEvent({
                      ...selectedEvent,
                      objects: value,
                      verified: true,
                    });
                  });
              }}
            />
          </label>
          <label>
            Correct people
            <select
              multiple
              value={selectedEvent.people.map((p) => p.id).filter(Boolean)}
              onChange={(e) => {
                const ids = Array.from(e.target.selectedOptions).map(
                  (o) => o.value,
                );
                run(async () => {
                  await api("/events/" + selectedEvent.id, "PATCH", {
                    person_ids: ids,
                  });
                  setSelectedEvent({
                    ...selectedEvent,
                    people: people.filter((p) => ids.includes(p.id)),
                    verified: true,
                  });
                });
              }}
            >
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <div className="modal-actions">
            <button
              className="primary"
              disabled={busy}
              onClick={() => sendPhoto(selectedEvent)}
            >
              <Send size={15} />
              Send to Telegram
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  await api("/events/" + selectedEvent.id, "PATCH", {
                    verified: !selectedEvent.verified,
                  });
                  setSelectedEvent({
                    ...selectedEvent,
                    verified: !selectedEvent.verified,
                  });
                })
              }
            >
              <ShieldCheck size={15} />
              {selectedEvent.verified ? "Unconfirm" : "Confirm memory"}
            </button>
            <button
              className="icon-button danger"
              aria-label="Hide memory"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  await api("/events/" + selectedEvent.id, "DELETE");
                  setSelectedEvent(null);
                })
              }
            >
              <Trash2 size={17} />
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
