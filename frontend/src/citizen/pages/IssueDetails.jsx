import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import IssueLocationMap from "../components/IssueLocationMap";
import StatusBadge from "../../shared/components/StatusBadge";
import StatusTimeline from "../components/StatusTimeline";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { categoryIcon, categoryLabel, statusLabel } from "../../shared/constants";
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

function historyLabel(entry) {
  if (entry.old_status == null) return "Report submitted";
  if (entry.old_status === entry.new_status) {
    return entry.new_status === "RESOLVED" && entry.photo_url
      ? "Proof of resolution added"
      : statusLabel(entry.new_status);
  }
  return `${statusLabel(entry.old_status)} → ${statusLabel(entry.new_status)}`;
}

export default function IssueDetails() {
  const { issueId } = useParams();
  const [issue, setIssue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [actionBusy, setActionBusy] = useState("");
  const [actionError, setActionError] = useState("");
  const [confirmed, setConfirmed] = useState(false);

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

  async function runAction(kind) {
    setActionBusy(kind);
    setActionError("");
    try {
      const updated =
        kind === "confirm"
          ? await citizenService.confirmIssue(issueId)
          : await citizenService.reopenIssue(issueId);
      setIssue(updated);
      if (kind === "confirm") setConfirmed(true);
    } catch (err) {
      setActionError(err.message || "We couldn't update this report.");
    } finally {
      setActionBusy("");
    }
  }

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

          {issue.status === "RESOLVED" && (
            <div className="resolution-actions">
              {confirmed ||
              issue.history?.some((entry) =>
                entry.note?.toLowerCase().includes("reporter confirmed")
              ) ? (
                <p className="resolution-actions__thanks">
                  ✅ You confirmed this fix. Thank you for closing the loop!
                </p>
              ) : (
                <>
                  <p className="resolution-actions__hint">
                    Marked as resolved — does it look fixed to you?
                  </p>
                  <div className="resolution-actions__buttons">
                    <button
                      type="button"
                      className="button button--primary"
                      disabled={Boolean(actionBusy)}
                      onClick={() => runAction("confirm")}
                    >
                      {actionBusy === "confirm" ? "Confirming…" : "Yes, it's fixed"}
                    </button>
                    <button
                      type="button"
                      className="button button--secondary"
                      disabled={Boolean(actionBusy)}
                      onClick={() => runAction("reopen")}
                    >
                      {actionBusy === "reopen" ? "Reopening…" : "No, reopen it"}
                    </button>
                  </div>
                </>
              )}
              {actionError && (
                <p className="field-error" role="alert">
                  {actionError}
                </p>
              )}
            </div>
          )}
        </section>

        {(issue.resolution_note || issue.resolution_photo_url) && (
          <section className="card" aria-labelledby="resolution-heading">
            <h2 className="card__title" id="resolution-heading">
              Resolution
            </h2>

            {issue.resolution_note && (
              <p className="detail-description">{issue.resolution_note}</p>
            )}

            {issue.resolution_photo_url && (
              <a
                href={issue.resolution_photo_url}
                target="_blank"
                rel="noreferrer"
                className="evidence evidence--resolution"
              >
                <img
                  src={issue.resolution_photo_url}
                  alt={`Proof of resolution for report ${issue.tracking_id}`}
                />
                <span className="evidence__hint">Open full size</span>
              </a>
            )}
          </section>
        )}

        {issue.history?.length > 0 && (
          <section className="card" aria-labelledby="history-heading">
            <h2 className="card__title" id="history-heading">
              Activity history
            </h2>
            <ol className="history-list">
              {issue.history.map((entry) => (
                <li key={entry.id} className="history-item">
                  <span className="history-item__meta">
                    {formatDateTime(entry.created_at)} ·{" "}
                    {entry.changed_by_role === "ADMIN"
                      ? "City administration"
                      : "Reporter"}
                  </span>
                  <span className="history-item__label">{historyLabel(entry)}</span>
                  {entry.note && (
                    <span className="history-item__note">{entry.note}</span>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}

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
