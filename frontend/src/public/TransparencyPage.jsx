import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState } from "../shared/components/States";
import "../styles/tokens.css";
import "../styles/citizen.css";
import "../styles/transparency.css";

function gradeTone(grade) {
  if (grade === "A+" || grade === "A") return "good";
  if (grade === "B") return "ok";
  if (grade === "C") return "warn";
  return "bad";
}

function formatValue(value, suffix = "") {
  return value == null ? "—" : `${value}${suffix}`;
}

export default function TransparencyPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/public/transparency");
      if (!response.ok) throw new Error("The report is unavailable right now.");
      setReport(await response.json());
    } catch (err) {
      setError(err.message || "The report is unavailable right now.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="citizen-shell">
      <header className="citizen-header">
        <div className="citizen-header__inner">
          <span className="brand">
            <span className="brand__mark" aria-hidden="true">
              🏙
            </span>
            <span className="brand__text">
              SmartCity<span className="brand__sub">Public Transparency</span>
            </span>
          </span>
          <nav className="transparency-nav">
            <Link to="/login" className="button button--ghost">
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      <main className="citizen-main">
        <div className="page">
          <div className="page-heading">
            <h1>City report card</h1>
            <p className="muted">
              How well is your city fixing what citizens report? These scores are
              computed live from the public issue database — nobody curates them.
            </p>
          </div>

          {loading && <LoadingState label="Computing the latest scores…" />}

          {!loading && error && (
            <ErrorState
              title="We couldn't load the report card"
              message={error}
              onRetry={load}
            />
          )}

          {!loading && !error && report && (
            <>
              <section className="card score-hero" aria-label="City-wide score">
                <div
                  className={`score-ring score-ring--${gradeTone(report.city.grade)}`}
                >
                  <span className="score-ring__grade">
                    {report.city.grade ?? "—"}
                  </span>
                  <span className="score-ring__score">
                    {formatValue(report.city.score, "/100")}
                  </span>
                </div>
                <dl className="score-hero__stats">
                  <div>
                    <dt>Problems reported</dt>
                    <dd>{report.city.total_cases}</dd>
                  </div>
                  <div>
                    <dt>Resolved</dt>
                    <dd>{report.city.resolved_cases}</dd>
                  </div>
                  <div>
                    <dt>Resolution rate</dt>
                    <dd>{formatValue(report.city.resolution_rate, "%")}</dd>
                  </div>
                  <div>
                    <dt>Fixed within SLA</dt>
                    <dd>{formatValue(report.city.on_time_rate, "%")}</dd>
                  </div>
                  <div>
                    <dt>Avg. resolution time</dt>
                    <dd>
                      {report.city.avg_resolution_days == null
                        ? "—"
                        : `${report.city.avg_resolution_days} days`}
                    </dd>
                  </div>
                </dl>
              </section>

              <section aria-labelledby="departments-heading">
                <h2 className="section-title" id="departments-heading">
                  Department report cards
                </h2>
                <ul className="deptcard-grid">
                  {report.departments.map((department) => (
                    <li key={department.code} className="card deptcard">
                      <div className="deptcard__head">
                        <h3 className="deptcard__name">{department.name}</h3>
                        <span
                          className={`grade-badge grade-badge--${gradeTone(department.grade)}`}
                        >
                          {department.grade ?? "No data"}
                        </span>
                      </div>
                      <dl className="deptcard__stats">
                        <div>
                          <dt>Score</dt>
                          <dd>{formatValue(department.score, "/100")}</dd>
                        </div>
                        <div>
                          <dt>Cases</dt>
                          <dd>{department.total_cases}</dd>
                        </div>
                        <div>
                          <dt>Resolved</dt>
                          <dd>{formatValue(department.resolution_rate, "%")}</dd>
                        </div>
                        <div>
                          <dt>On time</dt>
                          <dd>{formatValue(department.on_time_rate, "%")}</dd>
                        </div>
                        <div>
                          <dt>Avg. days</dt>
                          <dd>{formatValue(department.avg_resolution_days)}</dd>
                        </div>
                        <div>
                          <dt>SLA breaches</dt>
                          <dd>{department.escalated_cases}</dd>
                        </div>
                      </dl>
                    </li>
                  ))}
                </ul>
              </section>

              <p className="muted transparency-methodology">
                <strong>How the score works: </strong>
                {report.methodology}
              </p>
            </>
          )}
        </div>
      </main>

      <footer className="citizen-footer">
        <p>
          SmartCity Civic Issue Reporting · Generated{" "}
          {report ? new Date(report.generated_at).toLocaleString() : "…"}
        </p>
      </footer>
    </div>
  );
}
