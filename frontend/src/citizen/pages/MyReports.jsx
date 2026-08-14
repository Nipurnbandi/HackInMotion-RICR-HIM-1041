import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IssueCard from "../components/IssueCard";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { useI18n } from "../../shared/i18n";
import { citizenService } from "../services/citizenService";

const FILTERS = [
  { value: "", key: "myreports.all", label: "All" },
  { value: "SUBMITTED", key: "status.SUBMITTED.label", label: "Submitted" },
  { value: "UNDER_REVIEW", key: "status.UNDER_REVIEW.label", label: "Under Review" },
  { value: "IN_PROGRESS", key: "status.IN_PROGRESS.label", label: "In Progress" },
  { value: "RESOLVED", key: "status.RESOLVED.label", label: "Resolved" },
];

const PAGE_SIZE = 10;

export default function MyReports() {
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(
        await citizenService.listIssues({
          status: status || undefined,
          search: debouncedSearch || undefined,
          page,
          pageSize: PAGE_SIZE,
        })
      );
    } catch (err) {
      setError(err.message || "We couldn't load your reports.");
    } finally {
      setLoading(false);
    }
  }, [status, debouncedSearch, page]);

  useEffect(() => {
    load();
  }, [load]);

  const isFiltered = Boolean(status || debouncedSearch);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="page">
      <div className="page-heading page-heading--row">
        <div>
          <h1>{t("myreports.title", "My reports")}</h1>
          <p className="muted">
            {t("myreports.subtitle", "Everything you have reported, and where it stands.")}
          </p>
        </div>
        <Link to="/citizen/report" className="button button--primary">
          {t("common.reportIssue", "+ Report an Issue")}
        </Link>
      </div>

      <div className="filters">
        <div className="search-field">
          <label className="visually-hidden" htmlFor="report-search">
            Search reports
          </label>
          <span className="search-field__icon" aria-hidden="true">
            🔍
          </span>
          <input
            id="report-search"
            type="search"
            className="input"
            placeholder={t(
              "myreports.search",
              "Search by description, address, or tracking ID…"
            )}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="filter-chips" role="group" aria-label="Filter by status">
          {FILTERS.map((filter) => (
            <button
              key={filter.value || "all"}
              type="button"
              className={`chip${status === filter.value ? " chip--active" : ""}`}
              aria-pressed={status === filter.value}
              onClick={() => {
                setStatus(filter.value);
                setPage(1);
              }}
            >
              {t(filter.key, filter.label)}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <LoadingState label={t("myreports.loading", "Loading your reports…")} />
      )}

      {!loading && error && (
        <ErrorState title="We couldn't load your reports" message={error} onRetry={load} />
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          icon={isFiltered ? "🔍" : "📋"}
          title={isFiltered ? "No reports match your filters" : "No reports yet"}
          message={
            isFiltered
              ? "Try a different search term or clear the status filter."
              : "When you report a civic issue it will appear here with its tracking ID and current status."
          }
          action={
            isFiltered ? (
              <button
                type="button"
                className="button button--secondary"
                onClick={() => {
                  setSearch("");
                  setStatus("");
                  setPage(1);
                }}
              >
                Clear filters
              </button>
            ) : (
              <Link to="/citizen/report" className="button button--primary">
                Report your first issue
              </Link>
            )
          }
        />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <p className="results-count" aria-live="polite">
            {data.total}{" "}
            {data.total === 1
              ? t("myreports.report", "report")
              : t("myreports.reports", "reports")}
          </p>

          <ul className="issue-list">
            {data.items.map((issue) => (
              <IssueCard key={issue.id} issue={issue} />
            ))}
          </ul>

          {totalPages > 1 && (
            <nav className="pagination" aria-label="Reports pagination">
              <button
                type="button"
                className="button button--secondary"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
              >
                {t("myreports.prev", "Previous")}
              </button>
              <span className="pagination__status">
                {t("myreports.page", "Page")} {page} {t("myreports.of", "of")}{" "}
                {totalPages}
              </span>
              <button
                type="button"
                className="button button--secondary"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages}
              >
                {t("myreports.next", "Next")}
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
