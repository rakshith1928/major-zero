import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { Html5Qrcode } from "html5-qrcode";
import { api, type Ticket, type VerifyResult } from "../api";
import { useAuth } from "../auth";
import { Icon, PageHeader, SignInPrompt } from "../components/UI";

interface HistoryEntry { booking_ref: string; status: string; travel_date: string; fare: number }

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
      <PageHeader icon="ticket" eyebrow="Ready to board" title="Your ticket" description="Find a booking, open your ticket, and show your QR when you board." />
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
          <h2 className="flex items-center justify-center gap-2 font-semibold text-slate-900"><Icon name="ticket" />No bookings yet</h2>
          <p className="mt-2 text-sm text-slate-600">Book your first trip and your tickets will collect here.</p>
          <Link to="/chat" className="zb-button zb-button-primary mt-4 inline-flex">Plan a trip</Link>
        </div>
      )}
      {history.length > 0 && (
        <div className="zb-panel mt-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="ticket" />Booking history</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {history.map((h) => (
              <li key={h.booking_ref}>
                <button className="zb-action text-indigo-700 underline" onClick={() => { setRef(h.booking_ref); }}>
                  {h.booking_ref}
                </button>{" "}
                <span className="text-slate-600">{h.travel_date} · Rs.{h.fare} · {h.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {ticket && (
        <div id="zb-qr" className="zb-panel mt-4">
          <p className="break-all text-3xl font-bold tracking-widest text-slate-900">{ticket.code}</p>
          <p className="mt-1 text-sm text-slate-600">Booking {ticket.booking_ref}</p>
          <div className="mt-3 flex justify-center rounded bg-white p-3">
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
          <p className="mt-2 text-xs text-slate-500">Show this QR to the conductor for scanning.</p>
        </div>
      )}
    </div>
  );
}

export function Verify() {
  const [code, setCode] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const scannerRef = useRef<Html5Qrcode | null>(null);

  async function check(override?: string) {
    setResult(await api.verifyTicket((override ?? code).trim()));
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
            setResult(await api.verifyTicket(found.code));
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
        <input id="zb-verify-code" className="zb-control min-w-0 flex-1 uppercase" placeholder="Ticket code" value={code} onChange={(e) => setCode(e.target.value)} />
        <button onClick={() => check()} className="zb-action shrink-0 rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white">Verify</button>
      </div>
      </div>
      {result && (
        <div className={`mt-4 rounded-xl border p-4 ${result.valid ? "border-emerald-300 bg-emerald-50" : "border-red-300 bg-red-50"}`}>
          {result.valid ? (
            <p className="text-sm text-slate-800">Valid ticket for <strong>{result.passenger_name}</strong>, travel {result.travel_date}.</p>
          ) : (
            <p className="text-sm text-slate-800">Invalid: {result.reason}</p>
          )}
        </div>
      )}
    </div>
  );
}
