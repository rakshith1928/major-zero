import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { api } from "../api";
import { useAuth } from "../auth";

import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker from "leaflet/dist/images/marker-icon.png";
import shadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl: marker2x, iconUrl: marker, shadowUrl: shadow });

interface Overview {
  totals: Record<string, number>;
  warnings: Record<string, { fired: number; accepted: number; overridden: number }>;
  demand: { origin: string; destination: string; active_bookings: number }[];
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [curve, setCurve] = useState<{ departure: string; predicted_occupancy: number; is_peak: boolean }[]>([]);
  const [liveBuses, setLiveBuses] = useState<{ bus_id: number; lat: number; lon: number; status: string }[]>([]);

  useEffect(() => {
    api.adminOverview()
      .then((b) => setData(b as unknown as Overview))
      .catch((e: Error) => setError(String(e.message)));
    const today = new Date().toISOString().slice(0, 10);
    api.demand("Bangalore", "Chennai", today).then((d) => setCurve(d.curve)).catch(() => {});
    api.positions().then((p) => setLiveBuses(p.buses)).catch(() => {});
  }, []);

  if (!user) return <p className="mx-auto max-w-md px-4 py-10 text-slate-700">Please log in.</p>;
  if (!user.is_admin) return <Navigate to="/login" replace />;
  if (error) return <p className="mx-auto max-w-md px-4 py-10 text-red-600">Admin only: {error}</p>;
  if (!data) return <p className="mx-auto max-w-md px-4 py-10 text-slate-600">Loading dashboard...</p>;

  const warningRows = Object.entries(data.warnings || {}).map(([detector, counts]) => ({ detector, ...counts }));
  const accepted = warningRows.reduce((s, r) => s + (r.accepted || 0), 0);
  const overridden = warningRows.reduce((s, r) => s + (r.overridden || 0), 0);
  const firedTotal = warningRows.reduce((s, r) => s + (r.fired || 0), 0);
  const pie = [
    { name: "Accepted", value: accepted },
    { name: "Overridden", value: overridden },
    { name: "Fired only", value: Math.max(0, firedTotal - accepted - overridden) },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-2xl font-bold text-slate-900">Admin dashboard</h1>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {Object.entries(data.totals).map(([k, v]) => (
          <div key={k} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{k.replaceAll("_", " ")}</p>
            <p className="text-2xl font-bold tabular-nums text-slate-900">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-900">Warning outcomes</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" label>
                {pie.map((_, i) => <Cell key={i} fill={["#059669", "#f59e0b", "#94a3b8"][i]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-900">Active bookings by route</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.demand || []}>
              <XAxis dataKey="destination" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Bar dataKey="active_bookings" fill="#312e81" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      {curve.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-900">Demand forecast — Bangalore to Chennai (today)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={curve}>
              <XAxis dataKey="departure" fontSize={12} />
              <YAxis fontSize={12} domain={[0, 1]} />
              <Tooltip />
              <Line type="monotone" dataKey="predicted_occupancy" stroke="#312e81" dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <p className="mt-1 text-xs text-slate-500">Peak departures: {curve.filter((c) => c.is_peak).map((c) => c.departure).join(", ") || "none"}</p>
        </div>
      )}
      <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
        <MapContainer center={[13.5, 78.8]} zoom={6} style={{ height: 300, width: "100%" }}>
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" />
          {liveBuses.map((b) => (
            <Marker key={b.bus_id} position={[b.lat, b.lon]}>
              <Popup>Bus #{b.bus_id} · {b.status}</Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      {warningRows.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-slate-900">Warnings by detector</h2>
          <table className="mt-2 w-full text-sm">
            <thead><tr className="text-left text-slate-500"><th>Detector</th><th>Fired</th><th>Accepted</th><th>Overridden</th></tr></thead>
            <tbody>
              {warningRows.map((r) => (
                <tr key={r.detector} className="border-t border-slate-100 tabular-nums">
                  <td className="py-1">{r.detector}</td><td>{r.fired}</td><td>{r.accepted}</td><td>{r.overridden}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
