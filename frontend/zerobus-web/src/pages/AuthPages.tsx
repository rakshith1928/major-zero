import { useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, Link } from "react-router-dom";
import { startRegistration, startAuthentication } from "@simplewebauthn/browser";
import { api } from "../api";
import { useAuth } from "../auth";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block min-w-0">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

const inputCls = "zb-control min-w-0 w-full";

export function Register() {
  const nav = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", name: "", age: "", gender: "female", phone: "" });
  const [error, setError] = useState("");
  const set = (k: keyof typeof form) => (e: FormEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: (e.target as HTMLInputElement).value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await register({ ...form, age: Number(form.age) });
      nav("/chat");
    } catch (err) {
      setError(String((err as Error).message));
    }
  }

  async function registerPasskey() {
    setError("");
    try {
      await register({ ...form, age: Number(form.age) });
      const options = await api.passkeyRegisterOptions();
      const attResp = await startRegistration({ optionsJSON: options.publicKey as never });
      await api.passkeyRegister({ challenge_token: options.challenge_token, ...(attResp as unknown as Record<string, unknown>) });
      nav("/chat");
    } catch (err) {
      setError(`Passkey registration failed: ${(err as Error).message}`);
    }
  }

  return (
    <div className="zb-auth">
      <div className="flex items-center gap-2">
        <img src="/favicon.svg" alt="ZeroBus logo" width={26} height={26} />
        <span className="zb-eyebrow">ZeroBus · Secure access</span>
      </div>
      <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">Create your account</h1>
      <p className="mt-1 text-sm leading-relaxed text-slate-600">Your details are entered once, stored encrypted, and never typed again.</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <Field label="Email"><input className={inputCls} type="email" required value={form.email} onChange={set("email")} /></Field>
        <Field label="Password (fallback for devices without fingerprint)"><input className={inputCls} type="password" required minLength={8} value={form.password} onChange={set("password")} /></Field>
        <Field label="Full name"><input className={inputCls} required value={form.name} onChange={set("name")} /></Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Age"><input className={inputCls} type="number" required min={1} max={120} value={form.age} onChange={set("age")} /></Field>
          <Field label="Gender">
            <select className={inputCls} value={form.gender} onChange={set("gender")}>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </Field>
        </div>
        <Field label="Phone"><input className={inputCls} required minLength={10} maxLength={15} value={form.phone} onChange={set("phone")} /></Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="zb-action w-full rounded-lg bg-indigo-900 px-4 py-2.5 font-semibold text-white hover:bg-indigo-800">Create account</button>
        <button type="button" onClick={registerPasskey} className="zb-action w-full rounded-lg bg-amber-400 px-4 py-2.5 font-semibold text-indigo-950 hover:bg-amber-300">
          Create account with fingerprint
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">Already registered? <Link className="text-indigo-700 underline" to="/login">Log in</Link></p>
    </div>
  );
}

export function Login() {
  const nav = useNavigate();
  const { login, setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function passwordLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login({ email, password });
      nav("/chat");
    } catch (err) {
      setError(String((err as Error).message));
    }
  }

  async function passkeyLogin() {
    setError("");
    try {
      const options = await api.passkeyLoginOptions(email);
      const attResp = await startAuthentication({ optionsJSON: options.publicKey as never });
      const body = await api.passkeyLogin({ email, challenge_token: options.challenge_token, ...(attResp as unknown as Record<string, unknown>) });
      localStorage.setItem("zb_token", body.access_token);
      const me = await api.me();
      setUser(me);
      nav("/chat");
    } catch (err) {
      setError(`Passkey login: type your email above first, then retry. (${(err as Error).message})`);
    }
  }

  return (
    <div className="zb-auth">
      <div className="flex items-center gap-2">
        <img src="/favicon.svg" alt="ZeroBus logo" width={26} height={26} />
        <span className="zb-eyebrow">ZeroBus · Welcome back</span>
      </div>
      <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">Log in</h1>
      <p className="mt-1 text-sm leading-relaxed text-slate-600">One tap with your fingerprint, or your password below.</p>
      <button onClick={passkeyLogin} className="zb-action mt-4 w-full rounded-lg bg-amber-400 px-4 py-2.5 font-semibold text-indigo-950 hover:bg-amber-300">
        Log in with fingerprint
      </button>
      <div className="my-4 border-t border-slate-200 pt-4">
        <p className="text-sm text-slate-600">Or use your password:</p>
        <form onSubmit={passwordLogin} className="mt-2 space-y-3">
          <Field label="Email"><input className={inputCls} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Password"><input className={inputCls} type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="zb-action w-full rounded-lg bg-indigo-900 px-4 py-2.5 font-semibold text-white hover:bg-indigo-800">Log in</button>
        </form>
      </div>
      <p className="text-sm text-slate-600">New here? <Link className="text-indigo-700 underline" to="/register">Create an account</Link></p>
    </div>
  );
}
