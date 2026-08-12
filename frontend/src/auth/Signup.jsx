import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import "./auth.css";

export default function Signup() {
  const { signup, isAuthenticated, role } = useAuth();
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
      const path = await signup(email, password);
      navigate(path, { replace: true });
    } catch (err) {
      setError(err.data?.detail || err.message || "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Sign up</h1>
        <p>Create a citizen account</p>
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
              minLength={8}
              required
            />
          </label>
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="auth-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
