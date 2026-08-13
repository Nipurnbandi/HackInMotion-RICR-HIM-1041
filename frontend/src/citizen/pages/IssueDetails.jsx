import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import IssueLocationMap from "../components/IssueLocationMap";
import StatusBadge from "../../shared/components/StatusBadge";
import StatusTimeline from "../components/StatusTimeline";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { categoryIcon, categoryLabel } from "../../shared/constants";
import { formatCoordinates } from "../services/geocoding";
import { citizenService } from "../services/citizenService";

function formatDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function IssueDetails() {
  const { issueId } = useParams();
  const [issue, setIssue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setNotFound(false);
    try {
      setIssue(await citizenService.getIssue(issueId));
    } catch (err) {
      if (err.status === 404) setNotFound(true);
      else setError(err.message || "We couldn't load this report.");
    } finally {
      setLoading(false);
    }
  }, [issueId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="page page--narrow">
        <LoadingState label="Loading report…" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="page page--narrow">
        <EmptyState
          icon="🔎"
          title="Report not found"
          message="This report doesn't exist, or it isn't one of yours."
          action={
            <Link to="/citizen/issues" className="button button--primary">
              Back to my reports
            </Link>
          }
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page page--narrow">
        <ErrorState title="We couldn't load this report" message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="page page--narrow">
      <Link to="/citizen/issues" className="back-link">
        ← Back to my reports
      </Link>

      <div className="page-heading page-heading--row">
        <div>
          <p className="muted">Issue</p>
          <h1 className="tracking-heading">{issue.tracking_id}</h1>
        </div>
        <StatusBadge status={issue.status} />
      </div>

      <div className="detail-grid">
        <section className="card" aria-labelledby="progress-heading">
          <h2 className="card__title" id="progress-heading">
            Progress
          </h2>
          <StatusTimeline status={issue.status} />
        </section>

        <section className="card" aria-labelledby="details-heading">
          <h2 className="card__title" id="details-heading">
            Report details
          </h2>

          <dl className="detail-list">
            <div>
              <dt>Category</dt>
              <dd>
                <span aria-hidden="true">{categoryIcon(issue.category)} </span>
                {categoryLabel(issue.category)}
              </dd>
            </div>
            <div>
              <dt>Reported</dt>
              <dd>{formatDateTime(issue.created_at)}</dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd>{formatDateTime(issue.updated_at)}</dd>
            </div>
            <div>
              <dt>Description</dt>
              <dd className="detail-description">{issue.description}</dd>
            </div>
          </dl>
        </section>

        <section className="card" aria-labelledby="location-heading">
          <h2 className="card__title" id="location-heading">
            Location
          </h2>

          <IssueLocationMap
            latitude={issue.latitude}
            longitude={issue.longitude}
            label={`Map showing the reported location${
              issue.address ? ` at ${issue.address}` : ""
            }`}
          />

          <dl className="detail-list detail-list--compact">
            <div>
              <dt>Address</dt>
              <dd>{issue.address || "Not available"}</dd>
            </div>
            <div>
              <dt>Coordinates</dt>
              <dd className="mono">
                {formatCoordinates(issue.latitude, issue.longitude) || "Not recorded"}
              </dd>
            </div>
          </dl>
        </section>

        <section className="card" aria-labelledby="evidence-heading">
          <h2 className="card__title" id="evidence-heading">
            Photo evidence
          </h2>

          {issue.photo_url ? (
            <a href={issue.photo_url} target="_blank" rel="noreferrer" className="evidence">
              <img
                src={issue.photo_url}
                alt={`Photo evidence submitted for ${categoryLabel(
                  issue.category
                )} report ${issue.tracking_id}`}
              />
              <span className="evidence__hint">Open full size</span>
            </a>
          ) : (
            <p className="muted">No photo was attached to this report.</p>
          )}
        </section>
      </div>
    </div>
  );
}
