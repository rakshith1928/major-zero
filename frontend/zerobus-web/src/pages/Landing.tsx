import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="rounded-2xl bg-indigo-950 px-8 py-12 text-white">
        <p className="text-xs font-semibold uppercase tracking-widest text-amber-300">
          Zero-form bus booking
        </p>
        <h1 className="mt-2 text-4xl font-bold leading-tight md:text-5xl">
          Book buses by chatting. No forms.
        </h1>
        <p className="mt-3 max-w-xl text-indigo-200">
          Log in with your fingerprint, say where you want to go, and ZeroBus
          fills in the rest. It warns you before costly mistakes.
        </p>
        <div className="mt-6 flex gap-3">
          <Link to="/chat" className="rounded-lg bg-amber-400 px-5 py-2.5 font-semibold text-indigo-950 hover:bg-amber-300">
            Start booking
          </Link>
          <Link to="/register" className="rounded-lg border border-indigo-400 px-5 py-2.5 font-semibold text-white hover:bg-indigo-900">
            Create account
          </Link>
        </div>
      </header>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          ["Fingerprint login", "WebAuthn passkeys. Your details are stored encrypted, once."],
          ["Mistake warnings", "Late arrival, wrong boarding point, date traps. Caught before you pay."],
          ["QR tickets", "Paperless tickets with conductor verification."],
        ].map(([title, body]) => (
          <div key={title} className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold text-slate-900">{title}</h2>
            <p className="mt-1 text-sm text-slate-600">{body}</p>
          </div>
        ))}
      </section>

      <p className="mt-8 rounded-lg bg-slate-100 p-4 text-xs text-slate-600">
        Research prototype: bus inventory and live tracking are simulated, payments run
        in Razorpay test mode (no real money). See the study protocol in the docs.
      </p>
    </div>
  );
}
