import { Link } from "react-router-dom";
import { Icon, type IconName } from "../components/UI";
import { useReveal } from "../hooks/useReveal";

const features: { icon: IconName; number: string; title: string; body: string }[] = [
  { icon: "lock", number: "01", title: "Your details. Just once.", body: "Sign in with a passkey. Saved passenger details stay encrypted, ready for your next booking." },
  { icon: "shield", number: "02", title: "A second look, built in.", body: "Arrival deadlines, dates, boarding points. Get a heads-up before a small mistake becomes a big detour." },
  { icon: "ticket", number: "03", title: "Less paper. More journey.", body: "Keep your QR ticket in one place, ready for conductor verification when it’s time to board." },
];

const steps: { icon: IconName; title: string; body: string }[] = [
  { icon: "chat", title: "Say the trip in words.", body: "Type naturally — origin, destination, date, bus type. ZeroBus pulls the details out of the sentence, no forms." },
  { icon: "ticket", title: "Compare real options.", body: "Buses with fares, timings, seats left and crowd levels. Risky picks get flagged before you pay, with a safer alternative." },
  { icon: "shield", title: "Board with a QR.", body: "Your ticket lives in one wallet with a verifiable QR, ready for the conductor when it’s time to board." },
];

const corridors: { from: string; to: string; note: string; operators: string[] }[] = [
  { from: "Bangalore", to: "Chennai", note: "Day and overnight sleepers, about 7 hrs on the road.", operators: ["SETC Express", "KPN Travels", "SRS Travels", "Orange Tours", "VRL Travels"] },
  { from: "Bangalore", to: "Hyderabad", note: "Day and overnight sleepers, about 8 hrs on the road.", operators: ["SETC Express", "KPN Travels", "SRS Travels", "Orange Tours", "VRL Travels"] },
  { from: "Bangalore", to: "Mysuru", note: "Frequent day buses, about 3.5 hrs on the road.", operators: ["SETC Express", "KPN Travels", "SRS Travels", "VRL Travels"] },
  { from: "Bangalore", to: "Coimbatore", note: "Day and overnight sleepers via Salem, about 7.5 hrs.", operators: ["SETC Express", "KPN Travels", "SRS Travels", "VRL Travels"] },
  { from: "Bangalore", to: "Vijayawada", note: "Overnight sleepers via Anantapur, about 12 hrs.", operators: ["SETC Express", "KPN Travels", "Orange Tours", "VRL Travels"] },
];

export default function Landing() {
  const rootRef = useReveal();
  return (
    <div className="zb-landing" ref={rootRef}>
      <header className="zb-hero">
        <div className="zb-hero-copy">
          <p className="zb-eyebrow text-amber-300"><span className="h-1.5 w-1.5 rounded-full bg-amber-300" />Zero-form bus booking</p>
          <h1>Your next trip<br />starts with <span>a chat.</span></h1>
          <p className="zb-hero-description">Skip the repetitive forms. Tell us where you’re headed, find your bus, and let ZeroBus help with the details.</p>
          <div className="mt-8 flex flex-wrap gap-3"><Link to="/chat" className="zb-button zb-button-amber">Start booking <Icon name="arrow" /></Link><Link to="/register" className="zb-button zb-button-hero">Create account</Link></div>
          <div className="zb-hero-note"><Icon name="shield" />Encrypted details <span aria-hidden="true">·</span> Thoughtful trip warnings</div>
          <dl className="zb-hero-stats">
            <div><dt className="sr-only">Buses in the demo inventory</dt><dd><strong>58</strong><span>buses</span></dd></div>
            <div><dt className="sr-only">Corridors served</dt><dd><strong>5</strong><span>corridors</span></dd></div>
            <div><dt className="sr-only">Mistake detectors watching each booking</dt><dd><strong>4</strong><span>mistake detectors</span></dd></div>
          </dl>
        </div>
        <div className="zb-conversation">
          <div className="zb-conversation-top"><img src="/favicon.svg" alt="" width="36" height="36" /><div><p className="font-semibold text-indigo-950">Your travel companion</p><p className="text-xs text-slate-500">Illustrative conversation</p></div><Icon name="spark" className="ml-auto text-indigo-600" /></div>
          <div className="zb-conversation-body"><div className="zb-example-user">An AC sleeper from Bangalore to Chennai tomorrow.</div><div className="zb-example-assistant">Let’s find your ride. Is there a time you need to arrive by?</div><div className="zb-example-user zb-example-short">Before 8 in the morning.</div><div className="zb-example-assistant"><span className="mb-2 flex items-center gap-2 font-semibold text-indigo-900"><Icon name="shield" />A little planning goes a long way.</span>I’ll keep your arrival deadline in mind while helping you choose.</div></div>
          <div className="zb-route-strip"><span><span className="block text-[10px] uppercase tracking-widest text-slate-500">From</span>Bangalore</span><span className="zb-route-line"><Icon name="arrow" /></span><span><span className="block text-[10px] uppercase tracking-widest text-slate-500">To</span>Chennai</span></div>
        </div>
      </header>
      <section className="zb-features zb-reveal" aria-labelledby="features-title"><div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="zb-eyebrow">Built around your journey</p><h2 id="features-title" className="mt-2 text-2xl font-bold tracking-tight text-indigo-950">Less friction, from start to stop.</h2></div><p className="text-sm text-slate-500">Simple by design. Helpful by nature.</p></div><div className="grid gap-4 md:grid-cols-3">{features.map(({ icon, number, title, body }) => <article key={number} className="zb-feature-card"><div className="flex items-center justify-between"><span className="zb-icon-tile"><Icon name={icon} /></span><span className="text-xs font-medium tabular-nums text-slate-400">/{number}</span></div><h3 className="mt-5 font-semibold text-indigo-950">{title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p></article>)}</div></section>
      <section className="zb-steps zb-reveal" aria-labelledby="how-title"><div><h2 id="how-title">How it works.</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">Three moves from an idea to a seat — the chat does the form-filling for you.</p></div><div className="zb-step-grid">{steps.map(({ icon, title, body }, i) => <article key={title} className="zb-step-card"><div className="flex items-center justify-between"><span className="zb-icon-tile"><Icon name={icon} /></span><span className="zb-step-num">0{i + 1}</span></div><h3>{title}</h3><p>{body}</p></article>)}</div></section>
      <section className="zb-corridors zb-reveal" aria-labelledby="corridors-title"><div><h2 id="corridors-title">Five corridors, covered daily.</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">Simulated timetables from operators you'll recognise. Pick a corridor to start chatting.</p></div><div className="zb-corridor-grid">{corridors.map(({ from, to, note, operators }) => <Link key={`${from}-${to}`} to="/chat" className="zb-corridor-card" aria-label={`${from} to ${to} — start booking`}><p className="zb-corridor-route"><Icon name="pin" />{from} <Icon name="arrow" aria-hidden="true" /> {to}</p><p className="zb-corridor-meta">{note}</p><div className="zb-corridor-ops">{operators.map((op) => <span key={op}>{op}</span>)}</div></Link>)}</div></section>
      <section className="zb-cta zb-reveal" aria-labelledby="cta-title"><h2 id="cta-title">Ready when <span>you are.</span></h2><p>Create an account once, then book every future trip in a single conversation.</p><Link to="/chat" className="zb-button zb-button-amber">Start booking <Icon name="arrow" /></Link></section>
      <aside className="zb-disclosure"><span className="zb-badge shrink-0">Research prototype</span><p>Bus inventory and tracking are simulated. Payments use Razorpay test mode — no real money. This is a student research project, not a live transport service.</p></aside>
    </div>
  );
}
