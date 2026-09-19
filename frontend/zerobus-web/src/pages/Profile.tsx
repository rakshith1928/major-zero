import { useEffect, useState } from "react";
import { api, type SavedPassenger } from "../api";
import { useAuth } from "../auth";
import { Icon, PageHeader, SignInPrompt } from "../components/UI";

interface Notice { id: number; title: string; body: string }

export default function Profile() {
  const { user } = useAuth();
  const [passengers, setPassengers] = useState<SavedPassenger[]>([]);
  const [notifications, setNotifications] = useState<Notice[]>([]);

  useEffect(() => {
    api.passengers().then((b) => setPassengers(b.passengers)).catch(() => {});
    api.notifications().then((b) => setNotifications(b.notifications)).catch(() => {});
  }, []);

  if (!user) return <SignInPrompt icon="user" title="Make yourself at home" description="Log in to manage saved passengers and see your account notifications." />;

  return (
    <div className="zb-page">
      <PageHeader icon="user" eyebrow="Your account" title="Profile" description="Your passenger details and notifications, in one place." />
      <div className="zb-panel mt-6 flex items-start gap-3">
        <span className="zb-icon-tile shrink-0"><Icon name="lock" /></span>
        <div className="min-w-0">
          <p className="break-words font-semibold text-slate-900">{user.email}</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">Details stored encrypted, decrypted only for your bookings.</p>
        </div>
      </div>

      <section className="zb-panel mt-5">
      <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="user" />Saved passengers</h2>
      <p className="mt-2 text-sm text-slate-500">Book for someone and choose "remember" to save their details here.</p>
      {passengers.length === 0 && (
        <p className="zb-empty">No saved passengers yet — they’ll appear here after you book for someone.</p>
      )}
      <ul className="mt-2 space-y-2">
        {passengers.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <span className="zb-avatar" aria-hidden="true"><Icon name="user" /></span>
            <span className="min-w-0 flex-1 break-words text-sm text-slate-800">{p.label}: {p.name}, {p.age} ({p.phone})</span>
            <button
              onClick={async () => { await api.deletePassenger(p.id); setPassengers(passengers.filter((x) => x.id !== p.id)); }}
              className="zb-action shrink-0 rounded-lg border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>

      </section>
      <section className="zb-panel mt-5">
      <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Icon name="chat" />Notifications</h2>
      <p className="mt-2 text-sm text-slate-500">Updates connected to your account and journeys.</p>
      {notifications.length === 0 && (
        <p className="zb-empty">No notifications right now — booking updates will show up here.</p>
      )}
      <ul className="mt-2 space-y-2">
        {notifications.map((n) => (
          <li key={n.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
            <strong>{n.title}</strong>
            <p className="mt-1 break-words leading-relaxed text-slate-600">{n.body}</p>
          </li>
        ))}
      </ul>
      </section>
    </div>
  );
}
