import { useEffect, useState } from "react";
import { api, type SavedPassenger } from "../api";
import { useAuth } from "../auth";

interface Notice { id: number; title: string; body: string }

export default function Profile() {
  const { user } = useAuth();
  const [passengers, setPassengers] = useState<SavedPassenger[]>([]);
  const [notifications, setNotifications] = useState<Notice[]>([]);

  useEffect(() => {
    api.passengers().then((b) => setPassengers(b.passengers)).catch(() => {});
    api.notifications().then((b) => setNotifications(b.notifications)).catch(() => {});
  }, []);

  if (!user) return <p className="mx-auto max-w-md px-4 py-10 text-slate-700">Please log in.</p>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <h1 className="text-2xl font-bold text-slate-900">Profile</h1>
      <p className="mt-1 text-sm text-slate-600">{user.email} · details stored encrypted, decrypted only for your bookings.</p>

      <h2 className="mt-6 font-semibold text-slate-900">Saved passengers</h2>
      {passengers.length === 0 && <p className="mt-1 text-sm text-slate-500">None yet. Book for someone and choose "remember".</p>}
      <ul className="mt-2 space-y-2">
        {passengers.map((p) => (
          <li key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3">
            <span className="text-sm text-slate-800">{p.label}: {p.name}, {p.age} ({p.phone})</span>
            <button
              onClick={async () => { await api.deletePassenger(p.id); setPassengers(passengers.filter((x) => x.id !== p.id)); }}
              className="rounded-lg border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>

      <h2 className="mt-6 font-semibold text-slate-900">Notifications</h2>
      <ul className="mt-2 space-y-2">
        {notifications.map((n) => (
          <li key={n.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-800">
            <strong>{n.title}</strong>
            <p className="text-slate-600">{n.body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
