import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Html5Qrcode } from "html5-qrcode";
import { api, type Ticket, type VerifyResult } from "../api";
import { useAuth } from "../auth";

interface HistoryEntry { booking_ref: string; status: string; travel_date: string; fare: number }

export default function Tickets() {
  const { user } = useAuth();
  const [ref, setRef] = useState("");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  useEffect(() => {
    api.history().then((b) => setHistory(b.bookings)).catch(() => {});
  }, []);

  async function load() {
    setError("");
    try {
      setTicket(await api.ticket(ref.trim()));
    } catch (err) {
      setError(String((err as Error).message));
    }
  }

  if (!user) return <p className="mx-auto max-w-md px-4 py-10 text-slate-700">Please log in to view tickets.</p>;

  return (
    <div className="mx-auto max-w-md px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Your ticket</h1>
      <div className="mt-4 flex gap-2">
        <label htmlFor="zb-ticket-ref" className="sr-only">Booking reference</label>
        <input id="zb-ticket-ref" className="flex-1 rounded-lg border border-slate-300 px-3 py-2" placeholder="Booking ref, e.g. A1B2C3" value={ref} onChange={(e) => setRef(e.target.value)} />
        <button onClick={load} className="rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white">Show</button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {history.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-900">Booking history</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {history.map((h) => (
              <li key={h.booking_ref}>
                <button className="text-indigo-700 underline" onClick={() => { setRef(h.booking_ref); }}>
                  {h.booking_ref}
                </button>{" "}
                <span className="text-slate-600">{h.travel_date} · Rs.{h.fare} · {h.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {ticket && (
        <div id="zb-qr" className="mt-4 rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-3xl font-bold tracking-widest text-slate-900">{ticket.code}</p>
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
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700"
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
    <div className="mx-auto max-w-md px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Conductor verification</h1>
      <button onClick={toggleScan} className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700">
        {scanning ? "Stop camera scan" : "Scan QR with camera"}
      </button>
      <div id="zb-scanner" className={scanning ? "mt-2 overflow-hidden rounded-xl border" : "hidden"} />
      {scanError && <p className="mt-2 text-sm text-amber-700">{scanError}</p>}
      <div className="mt-4 flex gap-2">
        <label htmlFor="zb-verify-code" className="sr-only">Ticket code</label>
        <input id="zb-verify-code" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 uppercase" placeholder="Ticket code" value={code} onChange={(e) => setCode(e.target.value)} />
        <button onClick={() => check()} className="rounded-lg bg-indigo-900 px-4 py-2 font-semibold text-white">Verify</button>
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
