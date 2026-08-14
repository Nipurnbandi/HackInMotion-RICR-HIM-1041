import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import StatusBadge from "./StatusBadge";
import { useI18n } from "../i18n";
import {
  CATEGORIES,
  CLOSED_STATUSES,
  STATUSES,
  categoryColor,
  categoryIcon,
  categoryLabel,
  statusColor,
} from "../constants";

const LIGHT_TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ??
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const LIGHT_TILE_ATTRIBUTION =
  import.meta.env.VITE_MAP_TILE_ATTRIBUTION ??
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const DARK_TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL_DARK ??
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DARK_TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const DEFAULT_CENTER = [20.5937, 78.9629];
const DEFAULT_ZOOM = 5;

function FitToIssues({ issues }) {
  const map = useMap();

  useEffect(() => {
    const points = issues
      .filter((issue) => issue.latitude != null && issue.longitude != null)
      .map((issue) => [issue.latitude, issue.longitude]);
    if (points.length > 0) {
      map.fitBounds(L.latLngBounds(points).pad(0.2), { maxZoom: 16 });
    }
  }, [issues, map]);

  return null;
}

function pinIcon(issue, colorMode) {
  const color =
    colorMode === "category"
      ? categoryColor(issue.category)
      : statusColor(issue.status);
  const classes = ["map-pin"];
  if (CLOSED_STATUSES.includes(issue.status)) classes.push("map-pin--closed");
  if (issue.status === "REJECTED") classes.push("map-pin--rejected");

  return L.divIcon({
    className: "map-pin-anchor",
    html: `<span class="${classes.join(" ")}" style="--pin-color:${color}">${categoryIcon(issue.category)}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -20],
  });
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function CityMap({
  issues,
  colorMode = "status",
  onColorModeChange,
  onVote,
  theme = "light",
  label = "Live city map",
}) {
  const { t } = useI18n();
  const tileUrl = theme === "dark" ? DARK_TILE_URL : LIGHT_TILE_URL;
  const tileAttribution =
    theme === "dark" ? DARK_TILE_ATTRIBUTION : LIGHT_TILE_ATTRIBUTION;

  const legend = useMemo(() => {
    if (colorMode === "category") {
      return CATEGORIES.map((category) => ({
        key: category.value,
        label: `${category.icon} ${t(
          `category.${category.value}.label`,
          category.label
        )}`,
        color: categoryColor(category.value),
        count: issues.filter((issue) => issue.category === category.value).length,
      })).filter((entry) => entry.count > 0);
    }
    return STATUSES.map((status) => ({
      key: status.value,
      label: t(`status.${status.value}.label`, status.label),
      color: statusColor(status.value),
      count: issues.filter((issue) => issue.status === status.value).length,
    })).filter((entry) => entry.count > 0);
  }, [issues, colorMode, t]);

  return (
    <section className={`city-map city-map--${theme}`} aria-label={label}>
      <div className="city-map__toolbar">
        <span className="city-map__summary">
          📍 {issues.length}{" "}
          {issues.length === 1
            ? t("map.issueOnMap", "issue on the map")
            : t("map.issuesOnMap", "issues on the map")}
        </span>
        <div className="city-map__modes" role="group" aria-label="Color markers by">
          <span className="city-map__modes-label">{t("map.colorby", "Color by")}</span>
          <button
            type="button"
            className={`chip chip--sm${colorMode === "status" ? " chip--active" : ""}`}
            aria-pressed={colorMode === "status"}
            onClick={() => onColorModeChange?.("status")}
          >
            {t("map.status", "Status")}
          </button>
          <button
            type="button"
            className={`chip chip--sm${colorMode === "category" ? " chip--active" : ""}`}
            aria-pressed={colorMode === "category"}
            onClick={() => onColorModeChange?.("category")}
          >
            {t("map.category", "Category")}
          </button>
        </div>
      </div>

      <div className="city-map__frame">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url={tileUrl} attribution={tileAttribution} />
          <FitToIssues issues={issues} />
          {issues.map((issue) => (
            <Marker
              key={issue.id}
              position={[issue.latitude, issue.longitude]}
              icon={pinIcon(issue, colorMode)}
            >
              <Popup>
                <div className="map-popup">
                  <span className="map-popup__title">
                    {categoryIcon(issue.category)}{" "}
                    {t(
                      `category.${issue.category}.label`,
                      categoryLabel(issue.category)
                    )}
                  </span>
                  <span className="map-popup__badges">
                    <StatusBadge status={issue.status} size="sm" />
                    {issue.escalated && (
                      <span className="escalated-badge">
                        ⚠ {t("map.escalated", "Escalated")}
                      </span>
                    )}
                  </span>
                  {issue.address && (
                    <span className="map-popup__address">{issue.address}</span>
                  )}
                  <span className="map-popup__meta">
                    {issue.report_count}{" "}
                    {issue.report_count === 1
                      ? t("map.report", "report")
                      : t("map.reports", "reports")}
                    {issue.department_name ? ` · ${issue.department_name}` : ""}
                  </span>
                  <span className="map-popup__meta">
                    {issue.tracking_id ? `${issue.tracking_id} · ` : ""}
                    {formatDate(issue.created_at)}
                  </span>
                  {onVote ? (
                    <button
                      type="button"
                      className={`vote-button${issue.has_voted ? " vote-button--active" : ""}`}
                      onClick={() => onVote(issue)}
                    >
                      👍{" "}
                      {issue.has_voted
                        ? t("map.supported", "Supported")
                        : t("map.support", "Support")}{" "}
                      · {issue.vote_count ?? 0}
                    </button>
                  ) : (
                    (issue.vote_count ?? 0) > 0 && (
                      <span className="map-popup__meta">
                        👍 {issue.vote_count}{" "}
                        {t("map.supporters", "citizens support this")}
                      </span>
                    )
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <ul className="map-legend" aria-label="Map legend">
        {legend.map((entry) => (
          <li key={entry.key} className="map-legend__item">
            <span
              className="map-legend__dot"
              style={{ background: entry.color }}
              aria-hidden="true"
            />
            {entry.label}
            <span className="map-legend__count">{entry.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
