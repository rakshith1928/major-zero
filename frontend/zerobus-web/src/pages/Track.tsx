import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { api } from "../api";
import { PageHeader } from "../components/UI";

import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker from "leaflet/dist/images/marker-icon.png";
import shadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: marker2x, iconUrl: marker, shadowUrl: shadow });

interface BusPosition { bus_id: number; lat: number; lon: number; progress: number; status: string; remaining_minutes: number }

export default function Track() {
  const [buses, setBuses] = useState<BusPosition[]>([]);
  const [busId, setBusId] = useState<string>("");
  const [stop, setStop] = useState("Bangalore");
  const [eta, setEta] = useState<{ eta_minutes: number; status: string } | null>(null);

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
      <PageHeader icon="pin" eyebrow="Follow your journey" title="Live bus map" badge="SIMULATION" description="Positions are simulated along route corridors for the prototype. Real GPS integration is future work." />
      <div className="zb-panel mt-6">
        <h2 className="font-semibold text-slate-900">Find your bus</h2>
        <div className="mt-3 flex flex-wrap items-end gap-4">
        <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">Bus{buses.length > 0 && <span className="font-normal text-slate-500"> ({buses.length} reporting)</span>}
          <select className="zb-control mt-2 block min-w-0 w-full" value={busId} onChange={(e) => setBusId(e.target.value)}>
            <option value="">Pick a bus</option>
            {buses.map((b) => <option key={b.bus_id} value={b.bus_id}>Bus #{b.bus_id} ({b.status})</option>)}
          </select>
        </label>
        <label className="min-w-0 w-full text-sm font-medium text-slate-700 sm:w-auto sm:flex-1">Boarding point
          <select className="zb-control mt-2 block min-w-0 w-full" value={stop} onChange={(e) => setStop(e.target.value)}>
            {["Bangalore", "Chennai", "Hyderabad", "Vellore", "Kurnool"].map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <button
          disabled={!busId}
          onClick={async () => {
            const today = new Date().toISOString().slice(0, 10);
            setEta(await api.eta(Number(busId), today, stop));
          }}
          className="zb-action w-full rounded-lg bg-amber-400 px-4 py-2.5 sm:w-auto text-sm font-semibold text-indigo-950 hover:bg-amber-300 disabled:opacity-50"
        >
          Check ETA
        </button>
        </div>
        {eta && <p className="zb-eta zb-enter" aria-live="polite">ETA to {stop}: <strong className="tabular-nums">{eta.eta_minutes} min</strong> ({eta.status})</p>}
      </div>
      <div className="zb-map-wrap mt-5">
        <span className="zb-map-chip">SIMULATION</span>
        <div className="zb-map">
        <MapContainer center={[13.5, 78.8]} zoom={6} className="h-[340px] w-full sm:h-[480px]">
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" />
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
