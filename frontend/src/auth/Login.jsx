import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import "./auth.css";

export default function Login() {
  const { login, isAuthenticated, role } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={role === "ADMIN" ? "/admin" : "/citizen"} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const path = await login(email, password);
      navigate(path, { replace: true });
    } catch (err) {
      setError(err.data?.detail || err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Login</h1>
        <p>Sign in to your account</p>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="auth-link">
          No account? <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
