import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { api } from "../api";
import { useAuth } from "../auth";
import { Icon, PageHeader, SignInPrompt, type IconName } from "../components/UI";

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

  if (!user) return <SignInPrompt icon="chart" title="Your operations overview" description="Log in with an administrator account to view bookings, warning outcomes, and route demand." />;
  if (!user.is_admin) return <Navigate to="/login" replace />;
  if (error) return <div className="zb-page-narrow"><p className="zb-form-error mt-10" role="alert">Admin only: {error}</p></div>;
  if (!data) return <div className="zb-page"><div className="zb-panel mt-6 text-sm text-slate-600" aria-live="polite">Loading dashboard...</div></div>;

  const statIcon = (key: string): IconName => {
    if (/book|ticket/.test(key)) return "ticket";
    if (/warn|safety/.test(key)) return "shield";
    if (/user|passenger/.test(key)) return "user";
    return "chart";
  };

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
    <div className="zb-page">
      <PageHeader icon="chart" eyebrow="Operations workspace" title="Admin dashboard" description="An overview of bookings, passenger safety signals, and demand across your routes." />
      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {Object.entries(data.totals).map(([k, v]) => (
          <div key={k} className="zb-panel zb-stat min-w-0">
            <span className="zb-icon-tile zb-icon-tile-sm"><Icon name={statIcon(k)} /></span>
            <p className="mt-3 break-words text-xs uppercase tracking-wide text-slate-500">{k.replaceAll("_", " ")}</p>
            <p className="mt-1 text-3xl font-bold tabular-nums text-indigo-950">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="zb-panel min-w-0">
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
        <div className="zb-panel min-w-0">
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
        <div className="zb-panel mt-4 min-w-0">
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
      <section className="zb-panel mt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="pin" />Fleet map</h2>
          <span className="zb-badge">SIMULATION</span>
        </div>
        <p className="mt-2 text-sm text-slate-600">Prototype positions are simulated, not live GPS readings.</p>
      <div className="zb-map mt-4">
        <MapContainer center={[13.5, 78.8]} zoom={6} className="h-[260px] w-full sm:h-[300px]">
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" />
          {liveBuses.map((b) => (
            <Marker key={b.bus_id} position={[b.lat, b.lon]}>
              <Popup>Bus #{b.bus_id} · {b.status}</Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      </section>
      {warningRows.length > 0 && (
        <div className="zb-panel mt-4 min-w-0">
          <h2 className="font-semibold text-slate-900">Warnings by detector</h2>
          <div className="mt-3 overflow-x-auto">
          <table className="zb-table w-full min-w-[480px] text-sm">
            <thead><tr className="text-left text-slate-500"><th>Detector</th><th>Fired</th><th>Accepted</th><th>Overridden</th></tr></thead>
            <tbody>
              {warningRows.map((r) => (
                <tr key={r.detector} className="border-t border-slate-100 tabular-nums">
                  <td className="py-3 pr-4">{r.detector}</td><td>{r.fired}</td><td>{r.accepted}</td><td>{r.overridden}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  );
}
