import { useCallback, useEffect, useState } from "react";
import CityMap from "../../shared/components/CityMap";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { useI18n } from "../../shared/i18n";
import { citizenService } from "../services/citizenService";

export default function CityMapPage() {
  const { t } = useI18n();
  const [issues, setIssues] = useState(null);
  const [colorMode, setColorMode] = useState("status");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [voteError, setVoteError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setIssues(await citizenService.getCityMap());
    } catch (err) {
      setError(err.message || "We couldn't load the city map.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleVote(issue) {
    setVoteError("");
    try {
      const result = await citizenService.voteIssue(issue.id);
      setIssues((current) =>
        (current ?? []).map((item) =>
          item.id === result.issue_id
            ? {
                ...item,
                vote_count: result.vote_count,
                has_voted: result.has_voted,
              }
            : item
        )
      );
    } catch (err) {
      setVoteError(err.message || t("map.voteError", "We couldn't record your vote."));
    }
  }

  return (
    <div className="page">
      <div className="page-heading">
        <h1>{t("map.title", "City Map")}</h1>
        <p className="muted">
          {t(
            "map.subtitle",
            "A live view of every issue reported across the city — see what your neighbours have already flagged before reporting it again."
          )}
        </p>
      </div>

      {voteError && (
        <div className="alert alert--error" role="alert">
          {voteError}
        </div>
      )}

      {loading && <LoadingState label={t("map.loading", "Loading the city map…")} />}

      {!loading && error && (
        <ErrorState
          title="We couldn't load the city map"
          message={error}
          onRetry={load}
        />
      )}

      {!loading && !error && issues && (
        issues.length === 0 ? (
          <EmptyState
            icon="🗺"
            title={t("map.empty.title", "Nothing on the map yet")}
            message="Be the first — report an issue and it will appear here for the whole city."
          />
        ) : (
          <CityMap
            issues={issues}
            colorMode={colorMode}
            onColorModeChange={setColorMode}
            onVote={handleVote}
            theme="light"
          />
        )
      )}
    </div>
  );
}
