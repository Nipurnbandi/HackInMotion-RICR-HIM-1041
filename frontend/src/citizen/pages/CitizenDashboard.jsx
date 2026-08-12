import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import IssueCard from "../components/IssueCard";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { issueService } from "../services/issueService";

function greeting(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

const STAT_CARDS = [
  { key: "total", label: "Total reports", tone: "neutral" },
  { key: "submitted", label: "Submitted", tone: "info" },
  { key: "in_progress", label: "In progress", tone: "primary" },
  { key: "resolved", label: "Resolved", tone: "success" },
];

export default function CitizenDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await issueService.getDashboard());
    } catch (err) {
      setError(err.message || "We couldn't load your dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const name = user?.email?.split("@")[0] ?? "there";

  return (
    <div className="page">
      <section className="hero">
        <div>
          <p className="hero__eyebrow">{greeting()}</p>
          <h1 className="hero__title">{name}</h1>
          <p className="hero__subtitle">
            Report a civic problem and help improve your city. Every report is given a
            tracking ID so you can follow it through to resolution.
          </p>
        </div>
        <Link to="/citizen/report" className="button button--primary button--lg">
          + Report an Issue
        </Link>
      </section>

      {loading && <LoadingState label="Loading your dashboard…" />}

      {!loading && error && (
        <ErrorState
          title="We couldn't load your dashboard"
          message={error}
          onRetry={load}
        />
      )}

      {!loading && !error && data && (
        <>
          <section aria-labelledby="stats-heading">
            <h2 className="section-title" id="stats-heading">
              My reports
            </h2>
            <ul className="stat-grid">
              {STAT_CARDS.map((card) => (
                <li key={card.key} className={`stat-card stat-card--${card.tone}`}>
                  <span className="stat-card__value">{data.stats[card.key]}</span>
                  <span className="stat-card__label">{card.label}</span>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="recent-heading">
            <div className="section-header">
              <h2 className="section-title" id="recent-heading">
                Recent reports
              </h2>
              {data.recent_issues.length > 0 && (
                <Link to="/citizen/issues" className="link">
                  View all reports
                </Link>
              )}
            </div>

            {data.recent_issues.length === 0 ? (
              <EmptyState
                icon="📍"
                title="You haven't reported anything yet"
                message="Spotted a pothole, a broken streetlight, or an overflowing bin? Report it and the city will take a look."
                action={
                  <Link to="/citizen/report" className="button button--primary">
                    Report your first issue
                  </Link>
                }
              />
            ) : (
              <ul className="issue-list">
                {data.recent_issues.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} />
                ))}
              </ul>
            )}
          </section>

          <section className="info-panel" aria-labelledby="civic-info-heading">
            <h2 className="section-title" id="civic-info-heading">
              Good to know
            </h2>
            <ul className="info-list">
              <li>
                <strong>Be precise about the location.</strong> Crews are dispatched using
                the exact coordinates you pin on the map.
              </li>
              <li>
                <strong>Add a photo.</strong> Reports with photo evidence are verified
                faster.
              </li>
              <li>
                <strong>For emergencies, call the city helpline.</strong> This portal is
                for non-urgent civic maintenance issues.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
