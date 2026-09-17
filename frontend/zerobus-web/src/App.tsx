import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Landing from "./pages/Landing";
import { Register, Login } from "./pages/AuthPages";
import Chat from "./pages/Chat";
import Tickets, { Verify } from "./pages/Tickets";
import Track from "./pages/Track";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";

function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
        <Link to="/" className="text-lg font-bold text-indigo-950">ZeroBus</Link>
        <Link to="/chat" className="text-sm text-slate-700 hover:text-indigo-900">Book</Link>
        <Link to="/track" className="text-sm text-slate-700 hover:text-indigo-900">Track</Link>
        <Link to="/tickets" className="text-sm text-slate-700 hover:text-indigo-900">Tickets</Link>
        <Link to="/verify" className="text-sm text-slate-700 hover:text-indigo-900">Verify</Link>
        {user?.is_admin && <Link to="/dashboard" className="text-sm text-slate-700 hover:text-indigo-900">Dashboard</Link>}
        <span className="flex-1" />
        {user ? (
          <>
            <Link to="/profile" className="text-sm text-slate-700">{user.email}</Link>
            <button onClick={() => { logout(); nav("/"); }} className="text-sm text-slate-500 hover:text-slate-800">Log out</button>
          </>
        ) : (
          <Link to="/login" className="rounded-lg bg-indigo-900 px-3 py-1.5 text-sm font-semibold text-white">Log in</Link>
        )}
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-[100dvh] bg-slate-50 text-slate-900">
          <Nav />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/tickets" element={<Tickets />} />
            <Route path="/verify" element={<Verify />} />
            <Route path="/track" element={<Track />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
          <footer className="mx-auto max-w-6xl px-4 py-6 text-xs text-slate-500">
            ZeroBus research prototype. Simulated inventory and tracking. Razorpay test mode, no real money.
          </footer>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
