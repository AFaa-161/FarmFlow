import { useState } from "react";
import "./Login.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function Login({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = mode === "signup" ? "/api/auth/signup" : "/api/auth/login";
      const body = mode === "signup"
        ? { full_name: fullName.trim(), email: email.trim().toLowerCase(), password }
        : { email: email.trim().toLowerCase(), password };
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Authentication failed. Please try again.");
      onAuthenticated(data);
    } catch (err) {
      setError(err.message || "Could not connect to FarmFlow. Check that the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand-mark" aria-hidden="true">🌾</div>
        <p className="eyebrow">SMART POST-HARVEST ASSISTANT</p>
        <h1>Welcome to FarmFlow</h1>
        <p className="auth-subtitle">Smarter crop decisions. Less waste. Better returns.</p>
        <div className="auth-tabs" role="tablist" aria-label="Authentication options">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(""); }}>Log in</button>
          <button type="button" className={mode === "signup" ? "active" : ""} onClick={() => { setMode("signup"); setError(""); }}>Create account</button>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "signup" && (
            <label>Full name<input autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} required maxLength={100} placeholder="Your name" /></label>
          )}
          <label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} placeholder="you@example.com" /></label>
          <label>Password
            <span className="password-field">
              <input type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} maxLength={128} placeholder="At least 8 characters" />
              <button type="button" className="show-password" onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Hide" : "Show"}</button>
            </span>
          </label>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <button className="auth-submit" type="submit" disabled={loading}>{loading ? "Please wait…" : mode === "signup" ? "Create account" : "Log in to FarmFlow"}</button>
        </form>
        <p className="auth-footnote">Your account lets you access FarmFlow's crop analysis and local weather dashboard.</p>
      </section>
    </main>
  );
}
