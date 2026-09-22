import { BrowserRouter, Routes, Route, Link, NavLink, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Brand, Icon, type IconName } from "./components/UI";
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
  const destinations: { to: string; label: string; icon: IconName }[] = [
    { to: "/chat", label: "Book", icon: "chat" },
    { to: "/track", label: "Track", icon: "pin" },
    { to: "/tickets", label: "Tickets", icon: "ticket" },
    { to: "/verify", label: "Verify", icon: "shield" },
    ...(user?.is_admin ? [{ to: "/dashboard", label: "Dashboard", icon: "chart" as const }] : []),
  ];
  return (
    <nav className="zb-nav" aria-label="Main navigation">
      <div className="zb-nav-inner">
        <Brand />
        <div className="zb-nav-links">
          {destinations.map(({ to, label, icon }) => <NavLink key={to} to={to} className={({ isActive }) => `zb-nav-link${isActive ? " is-active" : ""}`}><Icon name={icon} />{label}</NavLink>)}
        </div>
        <div className="zb-nav-account">
          {user ? <><NavLink to="/profile" className={({ isActive }) => `zb-nav-link${isActive ? " is-active" : ""}`}><Icon name="user" />Profile</NavLink><button onClick={() => { logout(); nav("/"); }} className="zb-logout">Log out</button></> : <Link to="/login" className="zb-button zb-button-primary">Log in <Icon name="arrow" /></Link>}
        </div>
      </div>
    </nav>
  );
}

function ChatRoute() {
  // Remount per account: one login can never see another's thread.
  const { user } = useAuth();
  return <Chat key={user?.id ?? "guest"} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="zb-app">
          <a href="#main-content" className="zb-skip">Skip to content</a>
          <Nav />
          <main id="main-content" tabIndex={-1} className="min-w-0 flex-1">
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
              <Route path="/chat" element={<ChatRoute />} />
              <Route path="/tickets" element={<Tickets />} />
              <Route path="/verify" element={<Verify />} />
              <Route path="/track" element={<Track />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/profile" element={<Profile />} />
            </Routes>
          </main>
          <footer className="zb-footer"><div><span className="font-semibold text-indigo-950">ZeroBus.</span><span>A little less effort. A better journey.</span></div><p>Research prototype · Simulated inventory and tracking · Razorpay test mode, no real money.</p></footer>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
