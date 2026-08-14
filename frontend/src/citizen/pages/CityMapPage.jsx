import { useCallback, useEffect, useState } from "react";
import CityMap from "../../shared/components/CityMap";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { citizenService } from "../services/citizenService";

export default function CityMapPage() {
  const [issues, setIssues] = useState(null);
  const [colorMode, setColorMode] = useState("status");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  return (
    <div className="page">
      <div className="page-heading">
        <h1>City Map</h1>
        <p className="muted">
          A live view of every issue reported across the city — see what your
          neighbours have already flagged before reporting it again.
        </p>
      </div>

      {loading && <LoadingState label="Loading the city map…" />}

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
            title="Nothing on the map yet"
            message="Be the first — report an issue and it will appear here for the whole city."
          />
        ) : (
          <CityMap
            issues={issues}
            colorMode={colorMode}
            onColorModeChange={setColorMode}
            theme="light"
          />
        )
      )}
    </div>
  );
}
