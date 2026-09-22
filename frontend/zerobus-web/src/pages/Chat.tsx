import { useEffect, useRef, useState, type FormEvent } from "react";
import { PageHeader, SignInPrompt } from "../components/UI";
import { BusArt } from "../components/BusArt";
import { api, type BusCard, type BookingCreated, type FareComparison, type SavedPassenger, type Warning } from "../api";
import { useAuth } from "../auth";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

interface SpeechRecognitionLike {
  lang: string;
  onresult: ((e: { results: { transcript: string }[][] }) => void) | null;
  start: () => void;
}

// One shared checkout.js loader; a failed load is removed so the next
// attempt re-inserts it instead of polling forever.
let razorpayLoader: Promise<void> | null = null;

function loadRazorpay(timeoutMs = 8000): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  if (razorpayLoader) return razorpayLoader;
  razorpayLoader = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector("script[data-zb-razorpay]");
    const script = existing instanceof HTMLScriptElement ? existing : document.createElement("script");
    const cleanup = () => {
      window.clearTimeout(timeout);
      script.removeEventListener("load", onLoad);
      script.removeEventListener("error", onError);
    };
    const fail = (message: string) => {
      cleanup();
      script.remove();
      razorpayLoader = null;
      reject(new Error(message));
    };
    const onLoad = () => {
      if (!window.Razorpay) {
        fail("Razorpay checkout is unavailable after loading checkout.js");
        return;
      }
      cleanup();
      resolve();
    };
    const onError = () => fail("checkout.js failed to load");
    const timeout = window.setTimeout(() => fail("checkout.js load timed out"), timeoutMs);
    script.addEventListener("load", onLoad);
    script.addEventListener("error", onError);
    if (!existing) {
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.dataset.zbRazorpay = "1";
      document.body.appendChild(script);
    }
  });
  return razorpayLoader;
}

interface ChatMessage { role: string; content: string }
interface DemoOrder { order_id: string; amount: number; booking_ref: string }

function crowdBand(level: number | undefined | null): string {
  if (level == null) return "—";
  if (level >= 0.75) return "HIGH";
  if (level >= 0.35) return "MODERATE";
  return "LOW";
}
interface CaptureForm { name: string; age: string; gender: string; phone: string; done?: boolean }

function BusCardView({ bus, onSelect }: { bus: BusCard; onSelect: (bus: BusCard) => void }) {
  return (
    <div className="zb-bus-card zb-enter">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-slate-900">{bus.operator}</span>
        <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800">
          {bus.bus_type.replaceAll("_", " ")}
        </span>
      </div>
      <div className="zb-bus-times">
        <span className="zb-bus-time">{bus.departure}</span>
        <span className="zb-bus-line" aria-hidden="true"><i /></span>
        <span className="zb-bus-time">{bus.arrival}{bus.arrival_day_offset > 0 && <em className="text-sm font-normal not-italic text-slate-500"> +1</em>}</span>
      </div>
      <div className="mt-1 flex items-center justify-between text-sm">
        <p className="text-xl font-bold tabular-nums text-indigo-950">₹{bus.fare}</p>
        <p className="text-slate-600 tabular-nums">{Math.floor(bus.duration_minutes / 60)}h {bus.duration_minutes % 60}m</p>
      </div>
      <div className="mt-1 flex flex-wrap gap-2 text-xs">
        <span className={`rounded-full px-2 py-0.5 font-medium ${bus.seats_left < 6 ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>
          {bus.seats_left} seats left
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700">Crowd: {crowdBand(bus.crowd_level)}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700">Fare: {bus.fare_indicator ?? "NORMAL"}</span>
      </div>
      <button
        onClick={() => onSelect(bus)}
        className="zb-action mt-3 w-full rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white"
      >
        Select this bus
      </button>
    </div>
  );
}

function WarningCard({ warning, bookingRef, buses, onResolved, onSwitchBus }: {
  warning: Warning; bookingRef: string; buses: BusCard[];
  onResolved: () => void; onSwitchBus: (bus: BusCard) => void;
}) {
  async function resolve(outcome: string, switchTo?: number) {
    await api.warningOutcome({ booking_ref: bookingRef, detector: warning.code, outcome });
    if (outcome === "ACCEPTED" && switchTo) {
      const alt = buses.find((b) => b.id === switchTo);
      if (alt) {
        onSwitchBus(alt);
        return;
      }
    }
    onResolved();
  }
  const alt = warning.alternative_bus_id
    ? buses.find((b) => b.id === warning.alternative_bus_id)
    : undefined;
  return (
    <div className="zb-warning zb-enter" role="alert">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-amber-700"><span className="zb-warn-dot" aria-hidden="true" />Warning: {warning.code.replaceAll("_", " ")}</p>
      <p className="mt-1 text-sm text-slate-800">{warning.message}</p>
      {alt && (
        <p className="mt-2 rounded-lg bg-white/70 px-3 py-2 text-sm text-slate-700 tabular-nums">
          Safer option: <strong>{alt.operator}</strong> · departs {alt.departure}, arrives {alt.arrival} · ₹{alt.fare}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <button onClick={() => resolve("OVERRIDDEN")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-white">
          Keep anyway
        </button>
        {warning.alternative_bus_id && (
          <button onClick={() => resolve("ACCEPTED", warning.alternative_bus_id)} className="rounded-lg bg-amber-400 px-3 py-1.5 text-sm font-semibold text-indigo-950 hover:bg-amber-300">
            Switch to safer bus
          </button>
        )}
      </div>
    </div>
  );
}

const CAPTURE_STEPS = [
  { key: "name", prompt: "Who is travelling? Please type their full name." },
  { key: "age", prompt: "What is their age?" },
  { key: "gender", prompt: "What is their gender? (female / male / other)" },
  { key: "phone", prompt: "What is their phone number?" },
] as const;

function CaptureSteps({ capture, setCapture, sessionId, setMessages }: {
  capture: CaptureForm;
  setCapture: (c: CaptureForm | null) => void;
  sessionId: string;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}) {
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState("");

  if (capture.done) {
    return (
      <div className="flex gap-2 rounded-xl border border-slate-200 bg-white p-4">
        <button onClick={async () => { await api.consentPassenger({ session_id: sessionId, remember: true, label: capture.name }); setCapture(null); setMessages((m) => [...m, { role: "assistant", content: "Remembered. I will reuse these details next time." }]); }} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white">Yes, remember</button>
        <button onClick={async () => { await api.consentPassenger({ session_id: sessionId, remember: false }); setCapture(null); setMessages((m) => [...m, { role: "assistant", content: "Understood. Using these details just this once." }]); }} className="rounded-lg border px-3 py-1.5 text-sm">Just this once</button>
      </div>
    );
  }

  const current = CAPTURE_STEPS[Math.min(step, CAPTURE_STEPS.length - 1)];

  async function answer(e: FormEvent) {
    e.preventDefault();
    const value = draft.trim();
    if (!value) return;
    setMessages((m) => [...m, { role: "user", content: value }]);
    const next = { ...capture, [current.key]: value };
    setDraft("");
    if (step < CAPTURE_STEPS.length - 1) {
      const nxt = CAPTURE_STEPS[step + 1];
      setMessages((m) => [...m, { role: "assistant", content: nxt.prompt }]);
      setCapture(next);
      setStep(step + 1);
    } else {
      const res = await api.capturePassenger({
        session_id: sessionId, name: next.name,
        age: Number(next.age), gender: next.gender, phone: next.phone,
      });
      setMessages((m) => [...m, { role: "assistant", content: `Saved details for ${(res.passenger as Record<string, string>).name}. Remember for next time?` }]);
      setCapture({ ...next, done: true });
    }
  }

  return (
    <form onSubmit={answer} className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-800">{step === 0 ? CAPTURE_STEPS[0].prompt : current.prompt}</p>
      <div className="mt-2 flex gap-2">
        <label htmlFor={`zb-capture-${current.key}`} className="sr-only">Answer</label>
        <input id={`zb-capture-${current.key}`} className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type your answer in chat" />
        <button className="rounded-lg bg-indigo-900 px-3 py-1.5 text-sm font-semibold text-white">Send</button>
      </div>
    </form>
  );
}

function FareCard({ comparison }: { comparison: FareComparison }) {
  const day = (iso: string) => {
    const d = new Date(`${iso}T00:00:00`);
    return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
  };
  return (
    <div className="zb-fare zb-enter" aria-label="Fare comparison by date">
      {comparison.options.map((o) => {
        const isBest = comparison.cheapest?.date === o.date;
        return (
          <div key={o.date} className={`zb-fare-row${isBest ? " zb-fare-best" : ""}`}>
            <span className="text-sm font-medium text-slate-800">{day(o.date)}</span>
            {o.min_fare === null ? (
              <span className="text-sm text-slate-400">No buses</span>
            ) : (
              <span className="text-sm font-bold tabular-nums text-indigo-950">₹{o.min_fare}</span>
            )}
            {isBest && <span className="zb-fare-pill">Cheapest</span>}
          </div>
        );
      })}
    </div>
  );
}

const storeKey = (userId: number) => `zb-chat-${userId}`;

const GREETING: ChatMessage = { role: "assistant", content: "Hi! Tell me your trip, e.g. 'AC sleeper from Bangalore to Chennai tomorrow'. Any arrival deadline I should watch for?" };

function loadStored(userId: number) {
  try {
    const raw = localStorage.getItem(storeKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Never show another account's conversation, even if a key collides.
    if (!parsed || parsed.ownerId !== userId) return null;
    return parsed;
  } catch { /* fresh session */ }
  return null;
}

const EXAMPLE_PROMPTS = [
  "AC sleeper from Bangalore to Chennai tomorrow",
  "Bangalore to Hyderabad on Friday, 2 seats",
  "Which day is cheapest to Chennai?",
  "Same as last time",
  "Undo my last change",
];

export default function Chat() {
  const { user } = useAuth();
  // Remounted per account (route key), so the initializer below always runs
  // for the signed-in user — one account can never see another's thread.
  const [stored] = useState(() => (user ? loadStored(user.id) : null));
  const [ownerId] = useState<number | null>(() => stored?.ownerId ?? user?.id ?? null);
  const [sessionId] = useState(() => stored?.sessionId || `web-${user?.id ?? "guest"}-${Date.now()}`);
  const [messages, setMessages] = useState<ChatMessage[]>(stored?.messages || [GREETING]);
  const [slots, setSlots] = useState<Record<string, string | number | null>>(stored?.slots || {});
  const [buses, setBuses] = useState<BusCard[]>(stored?.buses || []);
  const [fareComparison, setFareComparison] = useState<FareComparison | null>(null);
  const [negotiation, setNegotiation] = useState<{ dropped: string[] } | null>(null);
  const [servedRoutes, setServedRoutes] = useState<string[] | null>(null);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [booking, setBooking] = useState<BookingCreated | null>(stored?.booking || null);
  // Track-to-book handoff: a "Book" tap on /track prefills the composer
  // once (never auto-sends); the traveller reviews before sending.
  const [input, setInput] = useState(() => {
    try {
      const raw = localStorage.getItem("zb-track-pick");
      if (!raw) return "";
      localStorage.removeItem("zb-track-pick");
      const pick = JSON.parse(raw) as { origin?: string; destination?: string };
      if (pick?.origin && pick?.destination) return `${pick.origin} to ${pick.destination}`;
    } catch { /* malformed pick or SSR: chat still works */ }
    return "";
  });
  const [busy, setBusy] = useState(false);
  const [paying, setPaying] = useState(false);
  const [demoPay, setDemoPay] = useState<DemoOrder | null>(null);
  const [capture, setCapture] = useState<CaptureForm | null>(null);
  const [savedProfiles, setSavedProfiles] = useState<SavedPassenger[]>([]);
  const [chosenProfile, setChosenProfile] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Respect prefers-reduced-motion: CSS alone can't override the explicit
  // scrollIntoView option, so pick the behavior here.
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    bottomRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  }, [messages, buses, warnings]);

  // T03: pre-payment state survives a page reload — scoped per account so
  // a second login never sees the first account's conversation.
  // (Chat remounts per account via route key, so ownerId always matches.)
  useEffect(() => {
    if (!user || ownerId !== user.id) return;
    try {
      localStorage.setItem(storeKey(user.id), JSON.stringify({ ownerId: user.id, sessionId, messages, slots, buses, booking }));
    } catch { /* storage full: chat still works */ }
  }, [user, ownerId, sessionId, messages, slots, buses, booking]);

  if (!user) {
    return (
      <SignInPrompt
        title="Log in to start booking"
        description="Your trip is planned in a simple conversation. Sign in so your passenger details and tickets are ready when you are."
      />
    );
  }

  async function send(text?: string) {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: message }]);
    setBusy(true);
    try {
      const reply = await api.chat(sessionId, message);
      setSlots(reply.slots || {});
      setBuses(reply.buses || []);
      setFareComparison(reply.fare_comparison || null);
      setNegotiation(reply.negotiation || null);
      setServedRoutes(reply.served_routes || null);
      setMessages((m) => [...m, { role: "assistant", content: reply.assistant_text }]);
      if ((reply.slots || {}).passenger_ref === "other") {
        try {
          const list = await api.passengers();
          setSavedProfiles(list.passengers);
          setChosenProfile(null);
        } catch { setSavedProfiles([]); }
        setCapture({ name: "", age: "", gender: "female", phone: "" });
      }
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `Hmm, that didn't go through (${(err as Error).message}). Please try again.` }]);
    } finally {
      setBusy(false);
    }
  }

  async function selectBus(bus: BusCard) {
    setBusy(true);
    try {
      const travelDate = slots.travel_date as string;
      const created = await api.select({
        session_id: sessionId,
        bus_id: bus.id,
        travel_date: travelDate,
        boarding_point: (slots.origin as string) || bus.origin,
        ...(chosenProfile ? { passenger_profile_id: chosenProfile } : {}),
      });
      setBooking(created);
      setWarnings(created.warnings || []);
      setMessages((m) => [...m, { role: "assistant", content: `Selected ${bus.operator} at ${bus.departure}, Rs.${created.fare}. Booking ${created.booking_ref} is ready for payment.` }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `Couldn't start that booking (${(err as Error).message}). Want to try another bus?` }]);
    } finally {
      setBusy(false);
    }
  }

  function pay() {
    if (!booking || paying) return;
    setPaying(true);
    const bookingRef = booking.booking_ref;
    const done = () => setPaying(false);
    const fail = (err: unknown) => {
      setMessages((m) => [...m, { role: "assistant", content: `Payment didn't go through (${(err as Error).message}). No money moved — please try again.` }]);
      done();
    };
    api.createOrder(bookingRef).then((order) => {
      if (order.checkout_mode === "demo") {
        setDemoPay({ order_id: order.order_id, amount: order.amount, booking_ref: order.booking_ref });
        done();
        return;
      }
      if (!order.key_id) {
        // A test-mode order must carry the public key; refuse instead of
        // opening checkout with a broken key.
        fail(new Error("gateway response is missing the checkout key"));
        return;
      }
      loadRazorpay().then(() => {
        if (!window.Razorpay) {
          fail(new Error("Razorpay checkout.js loaded without a checkout object"));
          return;
        }
        const rzp = new window.Razorpay({
          key: order.key_id,
          amount: order.amount * 100,
          currency: order.currency,
          name: "ZeroBus (TEST MODE)",
          description: `Booking ${bookingRef} - no real money`,
          order_id: order.order_id,
          handler: (resp: unknown) => {
            const r = resp as Record<string, string>;
            if (!r.razorpay_order_id || !r.razorpay_payment_id || !r.razorpay_signature) {
              setMessages((m) => [...m, { role: "assistant", content: "Payment response incomplete — nothing was verified. Please try Pay again." }]);
              return;
            }
            api.verifyPayment({
              booking_ref: bookingRef,
              razorpay_order_id: r.razorpay_order_id,
              razorpay_payment_id: r.razorpay_payment_id,
              razorpay_signature: r.razorpay_signature,
            }).then((verified) => {
              setBooking((b) => (b ? { ...b, status: verified.status } : b));
              setMessages((m) => [...m, { role: "assistant", content: "Payment successful. Ticket booked. View it under Tickets." }]);
            }).catch((err: Error) => {
              setMessages((m) => [...m, { role: "assistant", content: `Payment could not be verified: ${err.message}. Your booking stays payable from this card.` }]);
            });
          },
          modal: {
            ondismiss: () => {
              setMessages((m) => [
                ...m,
                { role: "assistant", content: "Checkout closed. Your booking is saved and still payable from this card." },
              ]);
            },
          },
        });
        rzp.open();
        done();
      }).catch(fail);
    }).catch(fail);
  }

  function voiceInput() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setMessages((m) => [...m, { role: "assistant", content: "Voice input is not supported in this browser. Please type instead." }]);
      return;
    }
    const rec = new SR();
    rec.lang = "en-IN";
    rec.onresult = (e) => send(e.results[0][0].transcript);
    rec.start();
  }

  return (
    <div className="zb-chat">
      <PageHeader
        icon="chat"
        eyebrow="Plan your trip"
        title="Book by chatting"
        description="Tell me where you’re going. I’ll pull up buses, flag anything risky, and keep your details out of repetitive forms."
        badge="Simulated inventory"
      />
      <div className="zb-chat-thread space-y-3" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`zb-msg-row flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${m.role === "user" ? "rounded-br-sm bg-indigo-900 text-white" : "rounded-bl-sm border border-slate-200 bg-white text-slate-800"}`}>
              {m.content}
            </div>
          </div>
        ))}
        {messages.length <= 1 && buses.length === 0 && !busy && (
          <div className="zb-prompts">
            <p className="zb-prompts-label">Try one of these</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <button key={p} onClick={() => send(p)} className="zb-prompt-chip">{p}</button>
              ))}
            </div>
          </div>
        )}
        {Object.keys(slots).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(slots).filter(([, v]) => v).map(([k, v]) => (
              <span key={k} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">{k}: {String(v)}</span>
            ))}
          </div>
        )}
        {servedRoutes && servedRoutes.length > 0 && (
          <div className="zb-prompts zb-enter" aria-label="Corridors we serve">
            <p className="zb-prompts-label">Corridors we serve</p>
            <div className="flex flex-wrap gap-2">
              {servedRoutes.map((r) => (
                <button key={r} onClick={() => send(r.split("↔").map((s) => s.trim()).join(" to "))} className="zb-prompt-chip">{r}</button>
              ))}
            </div>
          </div>
        )}
        {fareComparison && <FareCard comparison={fareComparison} />}
        {negotiation && (
          <p className="zb-negotiation zb-enter" aria-live="polite">
            Showing a compromise — relaxed your {negotiation.dropped.join(" and ")}. Pick any bus below to continue.
          </p>
        )}
        {buses.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {buses.map((b) => (
              <BusCardView key={b.id} bus={b} onSelect={selectBus} />
            ))}
          </div>
        )}
        {capture && savedProfiles.length > 0 && !capture.done && (
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-900">Book for a saved passenger, or add someone new:</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {savedProfiles.map((p) => (
                <button
                  key={p.id}
                  onClick={() => { setChosenProfile(p.id); setMessages((m) => [...m, { role: "assistant", content: `Using saved details for ${p.name}. Pick a bus above.` }]); }}
                  className={`rounded-full px-3 py-1.5 text-sm ${chosenProfile === p.id ? "bg-indigo-900 text-white" : "bg-slate-100 text-slate-800"}`}
                >
                  {p.label}: {p.name}
                </button>
              ))}
            </div>
          </div>
        )}
        {capture && (
          <CaptureSteps
            capture={capture}
            setCapture={setCapture}
            sessionId={sessionId}
            setMessages={setMessages}
          />
        )}
        {booking && warnings.map((w, i) => (
          <WarningCard
            key={i}
            warning={w}
            bookingRef={booking.booking_ref}
            buses={buses}
            onResolved={() => setWarnings((ws) => ws.filter((x) => x.code !== w.code))}
            onSwitchBus={(alt) => {
              setWarnings((ws) => ws.filter((x) => x.code !== w.code));
              selectBus(alt);
            }}
          />
        ))}
        {booking && booking.status === "PENDING_PAYMENT" && (
          <div className="zb-pay-card zb-enter">
            <p className="text-sm text-slate-800">Booking <strong>{booking.booking_ref}</strong> · <strong className="tabular-nums">Rs.{booking.fare}</strong> · TEST MODE, no real money.</p>
            <button onClick={pay} disabled={paying} className="mt-2 rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
              {paying ? "Starting checkout..." : "Pay now"}
            </button>
          </div>
        )}
        {demoPay && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4" role="dialog" aria-modal="true" aria-label="ZeroBus demo checkout">
            <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-900">ZeroBus demo checkout</span>
                <button aria-label="Close" onClick={() => setDemoPay(null)} className="text-slate-400 hover:text-slate-600">✕</button>
              </div>
              <p className="mt-3 text-3xl font-bold text-slate-900">₹{demoPay.amount}</p>
              <p className="mt-1 text-xs text-slate-500">Booking {demoPay.booking_ref} · order {demoPay.order_id}</p>
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Demo mode: no gateway is configured, so no money moves and no ticket is issued. Configure Razorpay test keys in backend .env for the real test checkout.
              </p>
              <button onClick={() => setDemoPay(null)} className="mt-4 w-full rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-300">
                Got it
              </button>
            </div>
          </div>
        )}
        {busy && (
          <div className="flex items-center gap-3" aria-live="polite">
            <BusArt width={72} />
            <div className="flex gap-1 rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="zb-composer">
        <button onClick={voiceInput} aria-label="Voice input" className="zb-action rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700">Mic</button>
        <label htmlFor="zb-chat-input" className="sr-only">Type your message</label>
        <input
          id="zb-chat-input"
          className="zb-control min-w-0 flex-1"
          placeholder="Type your trip, e.g. AC sleeper to Chennai tomorrow..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button onClick={() => send()} disabled={busy || !input.trim()} aria-label="Send message" className="zb-action rounded-xl bg-indigo-900 px-4 font-semibold text-white disabled:opacity-50">
          {busy ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
