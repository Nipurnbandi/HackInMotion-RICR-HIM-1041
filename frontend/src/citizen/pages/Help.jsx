import { Link } from "react-router-dom";
import { CATEGORIES, STATUSES } from "../constants";

export default function Help() {
  return (
    <div className="page page--narrow">
      <div className="page-heading">
        <h1>How reporting works</h1>
        <p className="muted">
          A short guide to filing a report the city can act on quickly.
        </p>
      </div>

      <section className="card" aria-labelledby="what-heading">
        <h2 className="card__title" id="what-heading">
          What can I report?
        </h2>
        <ul className="help-categories">
          {CATEGORIES.map((category) => (
            <li key={category.value}>
              <span aria-hidden="true">{category.icon}</span>
              <div>
                <strong>{category.label}</strong>
                <p className="muted">{category.hint}</p>
              </div>
            </li>
          ))}
        </ul>
        <p className="callout">
          This portal is for non-urgent civic maintenance. For emergencies — fire, medical,
          crime, or an immediate danger to life — contact the emergency services directly.
        </p>
      </section>

      <section className="card" aria-labelledby="how-heading">
        <h2 className="card__title" id="how-heading">
          How do I file a good report?
        </h2>
        <ol className="help-steps">
          <li>
            <strong>Pick the right category.</strong> It decides which city team receives
            your report.
          </li>
          <li>
            <strong>Pin the exact location.</strong> Use your device location, then drag
            the marker to the precise spot. Crews are dispatched to these coordinates.
          </li>
          <li>
            <strong>Attach a photo.</strong> A clear picture of the problem speeds up
            verification. JPEG, PNG or WEBP up to 5 MB.
          </li>
          <li>
            <strong>Describe what's wrong.</strong> Mention how long it has been there and
            whether anyone is at risk.
          </li>
          <li>
            <strong>Review and submit.</strong> You'll get a tracking ID immediately.
          </li>
        </ol>
      </section>

      <section className="card" aria-labelledby="status-heading">
        <h2 className="card__title" id="status-heading">
          What happens after I submit?
        </h2>
        <dl className="help-statuses">
          {STATUSES.map((status) => (
            <div key={status.value}>
              <dt>
                <span className={`status-badge status-badge--${status.tone} status-badge--sm`}>
                  <span className="status-badge__dot" aria-hidden="true" />
                  {status.label}
                </span>
              </dt>
              <dd className="muted">{status.description}</dd>
            </div>
          ))}
        </dl>
        <p className="muted">
          You can follow every status change from <Link to="/citizen/issues">My Reports</Link>
          , and quote your tracking ID when contacting the city.
        </p>
      </section>

      <div className="help-cta">
        <Link to="/citizen/report" className="button button--primary button--lg">
          + Report an Issue
        </Link>
      </div>
    </div>
  );
}
