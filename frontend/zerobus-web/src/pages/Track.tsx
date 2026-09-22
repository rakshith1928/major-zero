import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { api, type RouteAdvice } from "../api";
import { PageHeader } from "../components/UI";

import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker from "leaflet/dist/images/marker-icon.png";
import shadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: marker2x, iconUrl: marker, shadowUrl: shadow });

interface BusPosition { bus_id: number; lat: number; lon: number; progress: number; status: string; remaining_minutes: number; corridor: string[] }
interface EtaResult { eta_minutes: number; status: string; detail: string }

// Approximate corridor coordinates (same source as the backend sim).
const STOPS: Record<string, [number, number]> = {
  Bangalore: [12.9716, 77.5946],
  Vellore: [12.9165, 79.1325],
  Chennai: [13.0827, 80.2707],
  Kurnool: [15.8281, 78.0373],
  Hyderabad: [17.385, 78.4867],
  Mysuru: [12.2958, 76.6394],
  Salem: [11.6643, 78.146],
  Coimbatore: [11.0168, 76.9558],
  Anantapur: [14.6819, 77.6006],
  Vijayawada: [16.5062, 80.648],
};
const CORRIDORS: string[][] = [
  ["Bangalore", "Vellore", "Chennai"],
  ["Bangalore", "Kurnool", "Hyderabad"],
  ["Bangalore", "Mysuru"],
  ["Bangalore", "Salem", "Coimbatore"],
  ["Bangalore", "Anantapur", "Vijayawada"],
];
const CITIES = ["Bangalore", "Chennai", "Hyderabad", "Mysuru", "Coimbatore", "Vijayawada"];

export default function Track() {
  const nav = useNavigate();
  const trackerRef = useRef<HTMLDivElement>(null);
  const [buses, setBuses] = useState<BusPosition[]>([]);
  const [busId, setBusId] = useState<string>("");
  const [stop, setStop] = useState("Bangalore");
  const [eta, setEta] = useState<EtaResult | null>(null);
  const [adviceFrom, setAdviceFrom] = useState("Bangalore");
  const [adviceTo, setAdviceTo] = useState("Chennai");
  const [adviceDeadline, setAdviceDeadline] = useState("");
  const [advice, setAdvice] = useState<RouteAdvice | null>(null);
  const [adviceBusy, setAdviceBusy] = useState(false);

  const selectedBus = buses.find((b) => String(b.bus_id) === busId);
  const corridorStops = selectedBus?.corridor?.length ? selectedBus.corridor : [];

  async function checkEta(id: string, stopName: string) {
    const today = new Date().toISOString().slice(0, 10);
    try {
      setEta(await api.eta(Number(id), today, stopName));
    } catch { /* offline: keep last */ }
  }

  function trackBus(id: string, destination: string) {
    setBusId(id);
    setStop(destination);
    void checkEta(id, destination);
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    trackerRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  }

  function bookBus(origin: string, destination: string) {
    try {
      localStorage.setItem("zb-track-pick", JSON.stringify({ origin, destination }));
    } catch { /* storage full: chat still works */ }
    nav("/chat");
  }

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const body = await api.positions();
        if (alive) setBuses(body.buses);
      } catch { /* offline: keep last */ }
    }
    poll();
    const id = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div className="zb-page">
      <PageHeader icon="pin" eyebrow="Follow your journey" title="Live bus map" badge="SIMULATION" art description="Positions are simulated along route corridors for the prototype. Real GPS integration is future work." />
      <div className="zb-panel mt-6">
        <h2 className="font-semibold text-slate-900">Find my best bus</h2>
        <p className="mt-1 text-sm text-slate-600">Today's remaining buses on one corridor, ranked by earliest arrival — against your deadline if you set one.</p>
        <div className="mt-3 flex flex-wrap items-end gap-4">
          <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">From
            <select className="zb-control mt-2 block min-w-0 w-full" value={adviceFrom} onChange={(e) => setAdviceFrom(e.target.value)}>
              {CITIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">To
            <select className="zb-control mt-2 block min-w-0 w-full" value={adviceTo} onChange={(e) => setAdviceTo(e.target.value)}>
              {CITIES.filter((c) => c !== adviceFrom).map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">Must arrive by <span className="font-normal text-slate-500">(optional)</span>
            <input type="time" className="zb-control mt-2 block min-w-0 w-full" value={adviceDeadline} onChange={(e) => setAdviceDeadline(e.target.value)} />
          </label>
          <button
            disabled={adviceBusy}
            onClick={async () => {
              setAdviceBusy(true);
              try {
                setAdvice(await api.routes(adviceFrom, adviceTo, adviceDeadline || undefined));
              } catch { /* offline: keep last */ } finally {
                setAdviceBusy(false);
              }
            }}
            className="zb-action w-full rounded-lg bg-indigo-900 px-4 py-2.5 sm:w-auto text-sm font-semibold text-white disabled:opacity-50"
          >
            {adviceBusy ? "Ranking…" : "Rank buses"}
          </button>
        </div>
        {advice && (
          <div className="mt-4" aria-live="polite">
            <p className="text-sm text-slate-700"><strong>{advice.reason}</strong> <span className="text-slate-500">· simulated schedule</span></p>
            {advice.buses.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {advice.buses.slice(0, 5).map((b) => (
                  <li key={b.bus_id} className={`zb-advice-row zb-enter${b.bus_id === advice.recommended_bus_id ? " zb-advice-best" : ""}`}>
                    <button
                      onClick={() => trackBus(String(b.bus_id), advice.destination)}
                      className="zb-advice-track"
                      aria-label={`Track bus ${b.bus_id}, ${b.operator}`}
                    >
                      <span className="text-sm font-semibold text-slate-900">{b.departure} → {b.arrival}{b.arrival_day_offset > 0 && " +1"}</span>
                      <span className="text-sm text-slate-600">{b.operator} · ₹{b.fare} · {b.seats_left} seats left · {b.status}</span>
                      {b.bus_id === advice.recommended_bus_id && <span className="zb-best-pill">Best</span>}
                    </button>
                    <button
                      onClick={() => bookBus(advice.origin, advice.destination)}
                      className="zb-advice-book"
                      aria-label={`Book ${advice.origin} to ${advice.destination} in chat`}
                    >
                      Book
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="zb-empty">No buses left on this corridor today.</p>
            )}
          </div>
        )}
      </div>
      <div className="zb-panel mt-6" ref={trackerRef}>
        <h2 className="font-semibold text-slate-900">Find your bus</h2>
        <div className="mt-3 flex flex-wrap items-end gap-4">
        <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">Bus{buses.length > 0 && <span className="font-normal text-slate-500"> ({buses.length} reporting)</span>}
          <select className="zb-control mt-2 block min-w-0 w-full" value={busId} onChange={(e) => {
            const id = e.target.value;
            setBusId(id);
            const picked = buses.find((b) => String(b.bus_id) === id);
            if (picked?.corridor?.length) setStop(picked.corridor[picked.corridor.length - 1]);
          }}>
            <option value="">Pick a bus</option>
            {buses.map((b) => <option key={b.bus_id} value={b.bus_id}>Bus #{b.bus_id} ({b.status})</option>)}
          </select>
        </label>
        <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">Boarding point
          <select className="zb-control mt-2 block min-w-0 w-full" value={stop} onChange={(e) => setStop(e.target.value)}>
            {(corridorStops.length ? corridorStops : ["Bangalore", "Chennai", "Hyderabad", "Mysuru", "Coimbatore", "Vijayawada", "Vellore", "Kurnool", "Salem", "Anantapur"]).map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <button
          disabled={!busId}
          onClick={() => checkEta(busId, stop)}
          className="zb-action w-full rounded-lg bg-amber-400 px-4 py-2.5 sm:w-auto text-sm font-semibold text-indigo-950 hover:bg-amber-300 disabled:opacity-50"
        >
          Check ETA
        </button>
        </div>
        {eta && (
          <p className="zb-eta zb-enter" aria-live="polite">
            {eta.detail === "completed" && <>Bus #{busId} has <strong>completed</strong> this run.</>}
            {eta.detail === "departs_in" && <>Bus #{busId} departs {stop} in <strong className="tabular-nums">{eta.eta_minutes} min</strong>.</>}
            {eta.detail !== "completed" && eta.detail !== "departs_in" && <>ETA to {stop}: <strong className="tabular-nums">{eta.eta_minutes} min</strong> ({eta.status})</>}
          </p>
        )}
      </div>
      <div className="zb-map-wrap mt-5">
        <span className="zb-map-chip">SIMULATION</span>
        <div className="zb-map">
        <MapContainer center={[13.5, 78.8]} zoom={6} className="h-[340px] w-full sm:h-[480px]">
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" />
          {CORRIDORS.map((line) => (
            <Polyline key={line.join("-")} positions={line.map((s) => STOPS[s])} pathOptions={{ color: "#312e81", weight: 3, opacity: 0.55, dashArray: "8 6" }} />
          ))}
          {buses.map((b) => (
            <Marker key={b.bus_id} position={[b.lat, b.lon]}>
              <Popup>
                Bus #{b.bus_id} · {b.status}<br />
                {(b.progress * 100).toFixed(0)}% of route · {b.remaining_minutes} min left
              </Popup>
            </Marker>
          ))}
        </MapContainer>
        </div>
      </div>
    </div>
  );
}
