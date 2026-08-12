import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { LoadingState } from "../components/States";
import { issueService } from "../services/issueService";

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    issueService
      .getStats()
      .then((result) => !cancelled && setStats(result))
      .catch(() => !cancelled && setStats(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="page page--narrow">
      <div className="page-heading">
        <h1>Profile</h1>
        <p className="muted">Your account details on the SmartCity citizen portal.</p>
      </div>

      <section className="card" aria-labelledby="account-heading">
        <h2 className="card__title" id="account-heading">
          Account
        </h2>
        <dl className="detail-list">
          <div>
            <dt>Email</dt>
            <dd>{user?.email}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>
              <span className="role-pill">Citizen</span>
            </dd>
          </div>
        </dl>
      </section>

      <section className="card" aria-labelledby="activity-heading">
        <h2 className="card__title" id="activity-heading">
          Reporting activity
        </h2>

        {loading ? (
          <LoadingState label="Loading your activity…" />
        ) : stats ? (
          <dl className="detail-list detail-list--compact">
            <div>
              <dt>Total reports</dt>
              <dd>{stats.total}</dd>
            </div>
            <div>
              <dt>Resolved</dt>
              <dd>{stats.resolved}</dd>
            </div>
            <div>
              <dt>Open</dt>
              <dd>{stats.submitted + stats.under_review + stats.in_progress}</dd>
            </div>
          </dl>
        ) : (
          <p className="muted">We couldn't load your reporting activity right now.</p>
        )}
      </section>

      <section className="card" aria-labelledby="session-heading">
        <h2 className="card__title" id="session-heading">
          Session
        </h2>
        <p className="muted">
          Signing out ends your session on this device. Your reports remain on file.
        </p>
        <button
          type="button"
          className="button button--secondary"
          onClick={handleLogout}
          style={{ marginTop: "var(--space-4)" }}
        >
          Log out
        </button>
      </section>
    </div>
  );
}
