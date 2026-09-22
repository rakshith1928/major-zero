import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { Html5Qrcode } from "html5-qrcode";
import { api, type GuardianStatus, type HistoryEntry, type Ticket, type VerifyResult } from "../api";
import { useAuth } from "../auth";
import { BusArt } from "../components/BusArt";
import { Icon, PageHeader, SignInPrompt } from "../components/UI";

export default function Tickets() {
  const { user } = useAuth();
  const [ref, setRef] = useState("");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  useEffect(() => {
    api.history().then((b) => { setHistory(b.bookings); setHistoryLoaded(true); }).catch(() => {});
  }, []);

  const todayStr = new Date().toISOString().slice(0, 10);
  const upcoming = history.filter((h) => h.travel_date >= todayStr && h.status !== "SUPERSEDED");
  const past = history.filter((h) => !(h.travel_date >= todayStr && h.status !== "SUPERSEDED"));

  function countdown(iso: string): string {
    const days = Math.round(
      (new Date(`${iso}T00:00:00`).getTime() - new Date(`${todayStr}T00:00:00`).getTime()) / 86_400_000,
    );
    if (days <= 0) return "leaves today";
    if (days === 1) return "leaves tomorrow";
    return `leaves in ${days} days`;
  }

  function historyRow(h: HistoryEntry, showCountdown: boolean) {
    return (
      <li key={h.booking_ref} className="zb-history-row">
        <button className="zb-action font-semibold tabular-nums text-indigo-800 underline underline-offset-2" onClick={() => { setRef(h.booking_ref); }}>
          {h.booking_ref}
        </button>
        <span className="text-slate-800">{h.origin} → {h.destination}</span>
        <span className="text-slate-600 tabular-nums">{h.travel_date} · Rs.{h.fare}</span>
        {showCountdown && <span className="zb-countdown">{countdown(h.travel_date)}</span>}
        <span className={`zb-status ${/paid|confirmed|verified/i.test(h.status) ? "zb-status-paid" : "zb-status-pending"}`}>{h.status}</span>
      </li>
    );
  }

  async function load() {
    setError("");
    try {
      setTicket(await api.ticket(ref.trim()));
    } catch (err) {
      setError(String((err as Error).message));
    }
  }

  if (!user) return <SignInPrompt icon="ticket" title="Your tickets, all together" description="Log in to find your bookings and keep your boarding QR close at hand." />;

  return (
    <div className="zb-page zb-page-narrow">
      <PageHeader icon="ticket" eyebrow="Ready to board" title="Your ticket" art description="Find a booking, open your ticket, and show your QR when you board." />
      <div className="zb-panel mt-6">
      <h2 className="text-sm font-semibold text-slate-900">Find your booking</h2>
      <div className="mt-3 flex gap-2">
        <label htmlFor="zb-ticket-ref" className="sr-only">Booking reference</label>
        <input id="zb-ticket-ref" className="zb-control min-w-0 flex-1" placeholder="Booking ref, e.g. A1B2C3" value={ref} onChange={(e) => setRef(e.target.value)} />
        <button onClick={load} className="zb-action shrink-0 rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white">Show</button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>
      {historyLoaded && history.length === 0 && (
        <div className="zb-panel mt-4 text-center">
          <BusArt width={120} parked className="mx-auto" />
          <h2 className="mt-2 flex items-center justify-center gap-2 font-semibold text-slate-900"><Icon name="ticket" />No bookings yet</h2>
          <p className="mt-2 text-sm text-slate-600">Book your first trip and your tickets will collect here.</p>
          <Link to="/chat" className="zb-button zb-button-primary mt-4 inline-flex">Plan a trip</Link>
        </div>
      )}
      {upcoming.length > 0 && (
        <div className="zb-panel mt-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="ticket" />Upcoming trips</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {upcoming.map((h) => historyRow(h, true))}
          </ul>
        </div>
      )}
      {past.length > 0 && (
        <div className="zb-panel mt-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="ticket" />Past trips</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {past.map((h) => historyRow(h, false))}
          </ul>
        </div>
      )}
      {history.some((h) => h.deadline_time && h.status !== "SUPERSEDED") && (
        <section aria-label="Trip Guardian" className="mt-4 space-y-3">
          {history.filter((h) => h.deadline_time && h.status !== "SUPERSEDED").map((h) => (
            <GuardianPanel key={h.booking_ref} entry={h} />
          ))}
        </section>
      )}
      {ticket && (
        <div id="zb-qr" className="zb-ticket zb-enter">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Boarding pass</p>
          <p className="mt-1 break-all text-3xl font-bold tracking-widest tabular-nums text-indigo-950">{ticket.code}</p>
          <p className="mt-1 text-sm text-slate-600">Booking {ticket.booking_ref}</p>
          <div className="zb-ticket-qr">
            <QRCodeSVG value={ticket.qr_payload} size={200} />
          </div>
          <button
            onClick={() => {
              const svg = document.querySelector("#zb-qr svg");
              if (!svg) return;
              const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = `zerobus-${ticket.code}.svg`;
              a.click();
            }}
            className="zb-action mt-2 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700"
          >
            Download QR
          </button>
          <button
            onClick={() => window.print()}
            className="zb-action mt-2 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700"
          >
            Print ticket
          </button>
          <p className="mt-2 text-xs text-slate-500">Show this QR to the conductor for scanning.</p>
        </div>
      )}
    </div>
  );
}

function GuardianPanel({ entry }: { entry: HistoryEntry }) {
  const [status, setStatus] = useState<GuardianStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [rebooked, setRebooked] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  async function refresh() {
    try {
      setStatus(await api.guardianCheck(entry.booking_ref));
    } catch {
      /* offline: keep last state */
    }
  }

  useEffect(() => {
    let alive = true;
    api.guardianCheck(entry.booking_ref).then((s) => { if (alive) setStatus(s); }).catch(() => {});
    return () => { alive = false; };
  }, [entry.booking_ref]);

  async function rebook() {
    if (!status?.alternative_bus_id || busy) return;
    setBusy(true);
    setNotice("");
    try {
      const res = await api.guardianRebook(entry.booking_ref, status.alternative_bus_id);
      setRebooked(res.booking_ref);
      await refresh();
    } catch (err) {
      setNotice(`Rebook failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function demoDelay() {
    setNotice("");
    try {
      await api.guardianSimulateDelay(entry.bus_id, 60);
      await refresh();
    } catch (err) {
      setNotice(`Demo trigger failed: ${(err as Error).message}`);
    }
  }

  return (
    <div className={`zb-guardian zb-enter ${status?.status === "AT_RISK" ? "zb-guardian-risk" : "zb-guardian-ok"}`}>
      <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Icon name="shield" />Trip Guardian · {entry.booking_ref}
      </p>
      {!status && <p className="mt-1 text-sm text-slate-600">Watching your {entry.deadline_time} deadline…</p>}
      {status?.status === "OK" && (
        <p className="mt-1 text-sm text-slate-600">
          On track — predicted arrival {status.predicted_arrival?.slice(11, 16)}, deadline {status.deadline?.slice(11, 16)}.
        </p>
      )}
      {status?.status === "AT_RISK" && (
        <>
          <p className="mt-1 text-sm text-slate-800">
            Running late — predicted arrival {status.predicted_arrival?.slice(11, 16)} is past your {status.deadline?.slice(11, 16)} deadline.
          </p>
          {status.alternative_bus_id ? (
            <button onClick={rebook} disabled={busy} className="zb-action mt-2 rounded-lg bg-amber-400 px-4 py-2 text-sm font-semibold text-indigo-950 hover:bg-amber-300 disabled:opacity-50">
              {busy ? "Rebooking…" : "Rebook on an earlier bus"}
            </button>
          ) : (
            <p className="mt-1 text-sm text-slate-600">No earlier bus clears your deadline — consider another date.</p>
          )}
        </>
      )}
      {rebooked && (
        <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Rebooked as {rebooked} (pending payment). Find it above to complete payment.
        </p>
      )}
      {notice && <p className="mt-2 text-sm text-red-600">{notice}</p>}
      <button onClick={demoDelay} className="zb-action mt-2 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-white">
        Demo: simulate a 60-min delay
      </button>
    </div>
  );
}

interface RecentCheck { code: string; valid: boolean; at: string }

function loadRecent(): RecentCheck[] {
  try {
    const raw = localStorage.getItem("zb-verify-recent");
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
  } catch {
    return [];
  }
}

export function Verify() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [recent, setRecent] = useState<RecentCheck[]>(loadRecent);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  function record(codeUsed: string, valid: boolean) {
    setRecent((prev) => {
      const next = [{ code: codeUsed, valid, at: new Date().toISOString() }, ...prev.filter((r) => r.code !== codeUsed)].slice(0, 8);
      try {
        localStorage.setItem("zb-verify-recent", JSON.stringify(next));
      } catch { /* storage full: list just won't persist */ }
      return next;
    });
    inputRef.current?.focus();
  }

  async function check(override?: string) {
    const trimmed = (override ?? code).trim();
    if (!trimmed) return;
    try {
      const res = await api.verifyTicket(trimmed);
      setResult(res);
      record(trimmed, res.valid);
    } catch (err) {
      setResult({ valid: false, reason: String((err as Error).message) });
    }
  }

  useEffect(() => {
    return () => { scannerRef.current?.stop().catch(() => {}); };
  }, []);

  async function toggleScan() {
    setScanError("");
    if (scanning) {
      await scannerRef.current?.stop().catch(() => {});
      setScanning(false);
      return;
    }
    try {
      const scanner = new Html5Qrcode("zb-scanner");
      scannerRef.current = scanner;
      setScanning(true);
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 220 },
        async (decoded) => {
          // QR holds the signed payload envelope; resolve the ticket CODE
          // server-side by matching payload, falling back to manual entry.
          await scanner.stop().catch(() => {});
          setScanning(false);
          try {
            const found = await api.lookupByPayload(decoded);
            setCode(found.code);
            const res = await api.verifyTicket(found.code);
            setResult(res);
            record(found.code, res.valid);
          } catch {
            setScanError("QR scanned but ticket not found. Type the printed code instead.");
          }
        },
        () => {},
      );
    } catch (err) {
      setScanning(false);
      setScanError(`Camera unavailable: ${(err as Error).message}. Use manual code entry.`);
    }
  }

  return (
    <div className="zb-page zb-page-narrow">
      <PageHeader icon="shield" eyebrow="Conductor tools" title="Conductor verification" description="Scan a boarding QR or enter the printed ticket code to check its validity." />
      <div className="zb-panel mt-6">
      <button onClick={toggleScan} className="zb-action mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700">
        {scanning ? "Stop camera scan" : "Scan QR with camera"}
      </button>
      <div id="zb-scanner" className={scanning ? "mt-2 overflow-hidden rounded-xl border" : "hidden"} />
      {scanError && <p className="mt-2 text-sm text-amber-700">{scanError}</p>}
      <div className="mt-4 flex gap-2">
        <label htmlFor="zb-verify-code" className="sr-only">Ticket code</label>
        <input ref={inputRef} id="zb-verify-code" className="zb-control min-w-0 flex-1 uppercase" placeholder="Ticket code" value={code} onChange={(e) => setCode(e.target.value)} />
        <button onClick={() => check()} className="zb-action shrink-0 rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white">Verify</button>
      </div>
      </div>
      {result && (
        <div className={`zb-verify-result zb-verify-big zb-enter ${result.valid ? "zb-verify-valid" : "zb-verify-invalid"}`} aria-live="polite">
          {result.valid ? (
            <p className="flex items-start gap-2 text-slate-800"><Icon name="shield" /><span><strong className="block text-lg">Valid ticket</strong>for <strong>{result.passenger_name}</strong>, travel {result.travel_date}.</span></p>
          ) : (
            <p className="flex items-start gap-2 text-slate-800"><Icon name="lock" /><span><strong className="block text-lg">Not valid</strong>{result.reason}</span></p>
          )}
        </div>
      )}
      {recent.length > 0 && (
        <div className="zb-panel mt-4">
          <h2 className="font-semibold text-slate-900">Recently checked</h2>
          <ul className="mt-2 space-y-1.5">
            {recent.map((r) => (
              <li key={`${r.code}-${r.at}`}>
                <button
                  onClick={() => { setCode(r.code); void check(r.code); }}
                  className="zb-action flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm hover:bg-white"
                >
                  <span className={`zb-dot ${r.valid ? "zb-dot-ok" : "zb-dot-bad"}`} aria-hidden="true" />
                  <span className="font-semibold tabular-nums">{r.code}</span>
                  <span className="ml-auto text-xs text-slate-500">{r.valid ? "valid" : "invalid"}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
