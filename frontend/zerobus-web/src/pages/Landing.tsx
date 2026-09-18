import { Link } from "react-router-dom";
import { Icon, type IconName } from "../components/UI";

const features: { icon: IconName; number: string; title: string; body: string }[] = [
  { icon: "lock", number: "01", title: "Your details. Just once.", body: "Sign in with a passkey. Saved passenger details stay encrypted, ready for your next booking." },
  { icon: "shield", number: "02", title: "A second look, built in.", body: "Arrival deadlines, dates, boarding points. Get a heads-up before a small mistake becomes a big detour." },
  { icon: "ticket", number: "03", title: "Less paper. More journey.", body: "Keep your QR ticket in one place, ready for conductor verification when it’s time to board." },
];
export default function Landing() {
  return (
    <div className="zb-landing">
      <header className="zb-hero">
        <div className="zb-hero-copy">
          <p className="zb-eyebrow text-amber-300"><span className="h-1.5 w-1.5 rounded-full bg-amber-300" />Zero-form bus booking</p>
          <h1>Your next trip<br />starts with <span>a chat.</span></h1>
          <p className="zb-hero-description">Skip the repetitive forms. Tell us where you’re headed, find your bus, and let ZeroBus help with the details.</p>
          <div className="mt-8 flex flex-wrap gap-3"><Link to="/chat" className="zb-button zb-button-amber">Start booking <Icon name="arrow" /></Link><Link to="/register" className="zb-button zb-button-hero">Create account</Link></div>
          <div className="zb-hero-note"><Icon name="shield" />Encrypted details <span aria-hidden="true">·</span> Thoughtful trip warnings</div>
        </div>
        <div className="zb-conversation">
          <div className="zb-conversation-top"><img src="/favicon.svg" alt="" width="36" height="36" /><div><p className="font-semibold text-indigo-950">Your travel companion</p><p className="text-xs text-slate-500">Illustrative conversation</p></div><Icon name="spark" className="ml-auto text-indigo-600" /></div>
          <div className="zb-conversation-body"><div className="zb-example-user">An AC sleeper from Bangalore to Chennai tomorrow.</div><div className="zb-example-assistant">Let’s find your ride. Is there a time you need to arrive by?</div><div className="zb-example-user zb-example-short">Before 8 in the morning.</div><div className="zb-example-assistant"><span className="mb-2 flex items-center gap-2 font-semibold text-indigo-900"><Icon name="shield" />A little planning goes a long way.</span>I’ll keep your arrival deadline in mind while helping you choose.</div></div>
          <div className="zb-route-strip"><span><span className="block text-[10px] uppercase tracking-widest text-slate-500">From</span>Bangalore</span><span className="zb-route-line"><Icon name="arrow" /></span><span><span className="block text-[10px] uppercase tracking-widest text-slate-500">To</span>Chennai</span></div>
        </div>
      </header>
      <section className="zb-features" aria-labelledby="features-title"><div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="zb-eyebrow">Built around your journey</p><h2 id="features-title" className="mt-2 text-2xl font-bold tracking-tight text-indigo-950">Less friction, from start to stop.</h2></div><p className="text-sm text-slate-500">Simple by design. Helpful by nature.</p></div><div className="grid gap-4 md:grid-cols-3">{features.map(({ icon, number, title, body }) => <article key={number} className="zb-feature-card"><div className="flex items-center justify-between"><span className="zb-icon-tile"><Icon name={icon} /></span><span className="text-xs font-medium tabular-nums text-slate-400">/{number}</span></div><h3 className="mt-5 font-semibold text-indigo-950">{title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p></article>)}</div></section>
      <aside className="zb-disclosure"><span className="zb-badge shrink-0">Research prototype</span><p>Bus inventory and tracking are simulated. Payments use Razorpay test mode — no real money. This is a student research project, not a live transport service.</p></aside>
    </div>
  );
}
