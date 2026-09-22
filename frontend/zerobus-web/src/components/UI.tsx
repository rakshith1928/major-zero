import { Link } from "react-router-dom";
import type { ReactNode } from "react";

export type IconName = "chat" | "pin" | "ticket" | "shield" | "chart" | "user" | "arrow" | "spark" | "lock";
const paths: Record<IconName, ReactNode> = {
  chat: <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0ZM7 10h10M7 14h6" />,
  pin: <><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  ticket: <><path d="M3 5h18v5a2 2 0 0 0 0 4v5H3v-5a2 2 0 0 0 0-4Z" /><path d="M15 5v3m0 3v2m0 3v3" /></>,
  shield: <><path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z" /><path d="m8 12 3 3 5-6" /></>,
  chart: <path d="M4 3v18h18M9 16v-5m5 5V7m5 9V4" />,
  user: <><circle cx="12" cy="7" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  spark: <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" />,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2" /></>,
};
export function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  return <svg className={`zb-icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
export function Brand() {
  return <Link to="/" className="zb-brand" aria-label="ZeroBus home"><img src="/favicon.svg" alt="" width="38" height="38" /><span>Zero<span className="font-normal">Bus</span><span className="zb-brand-dot">.</span></span></Link>;
}
export function PageHeader({ icon, eyebrow, title, description, badge }: { icon: IconName; eyebrow: string; title: string; description: string; badge?: string }) {
  return <header className="zb-page-header"><div className="zb-eyebrow"><Icon name={icon} />{eyebrow}</div><div className="mt-3 flex flex-wrap items-center gap-3"><h1>{title}</h1>{badge && <span className="zb-badge">{badge}</span>}</div><p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">{description}</p></header>;
}
export function SignInPrompt({ title, description, icon = "lock" }: { title: string; description: string; icon?: IconName }) {
  return <section className="zb-gate"><span className="zb-icon-tile"><Icon name={icon} /></span><p className="zb-eyebrow mt-6 justify-center">Your journey, simplified</p><h1 className="mt-3 text-3xl font-bold tracking-tight text-indigo-950">{title}</h1><p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-slate-600">{description}</p><Link to="/login" className="zb-button zb-button-primary mt-7">Log in to continue <Icon name="arrow" /></Link><p className="mt-5 text-sm text-slate-500">New to ZeroBus? <Link to="/register" className="font-semibold text-indigo-800 underline underline-offset-4">Create an account</Link></p></section>;
}
