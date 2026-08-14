import { EmptyState } from "../../shared/components/States";
import {
  categoryColor,
  categoryIcon,
  statusColor,
  statusLabel,
} from "../../shared/constants";

const DONUT_RADIUS = 52;
const DONUT_SIZE = 120;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;
const DONUT_GAP = 2;

function formatDays(value) {
  if (value == null) return "—";
  return `${value} ${value === 1 ? "day" : "days"}`;
}

function StatusDonut({ byStatus, total }) {
  const segments = byStatus.filter((row) => row.count > 0);
  const gap = segments.length > 1 ? DONUT_GAP : 0;

  let start = 0;
  const arcs = segments.map((row) => {
    const length = (row.count / total) * DONUT_CIRCUMFERENCE;
    const arc = {
      key: row.status,
      color: statusColor(row.status),
      dash: Math.max(length - gap, 0.75),
      offset: -(start + gap / 2),
    };
    start += length;
    return arc;
  });

  return (
    <div className="donut">
      <svg
        className="donut__svg"
        viewBox={`0 0 ${DONUT_SIZE} ${DONUT_SIZE}`}
        role="img"
        aria-label={`Cases by status, ${total} total`}
      >
        <g transform={`rotate(-90 ${DONUT_SIZE / 2} ${DONUT_SIZE / 2})`}>
          <circle
            className="donut__track"
            cx={DONUT_SIZE / 2}
            cy={DONUT_SIZE / 2}
            r={DONUT_RADIUS}
            fill="none"
            strokeWidth="14"
          />
          {arcs.map((arc) => (
            <circle
              key={arc.key}
              cx={DONUT_SIZE / 2}
              cy={DONUT_SIZE / 2}
              r={DONUT_RADIUS}
              fill="none"
              stroke={arc.color}
              strokeWidth="14"
              strokeDasharray={`${arc.dash} ${DONUT_CIRCUMFERENCE - arc.dash}`}
              strokeDashoffset={arc.offset}
            />
          ))}
        </g>
        <text className="donut__value" x="50%" y="47%" textAnchor="middle">
          {total}
        </text>
        <text className="donut__caption" x="50%" y="62%" textAnchor="middle">
          cases
        </text>
      </svg>

      <ul className="donut__legend">
        {byStatus.map((row) => (
          <li key={row.status} className="donut__legend-item">
            <span
              className="donut__legend-dot"
              style={{ background: statusColor(row.status) }}
              aria-hidden="true"
            />
            <span className="donut__legend-label">{statusLabel(row.status)}</span>
            <span className="donut__legend-count">
              {row.count}
              <small>
                {total > 0 ? ` · ${Math.round((row.count / total) * 100)}%` : ""}
              </small>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CategoryBars({ byCategory }) {
  const max = Math.max(...byCategory.map((row) => row.count), 1);

  return (
    <ul className="barlist">
      {byCategory.map((row) => (
        <li key={row.category} className="barlist__row">
          <span className="barlist__label">
            <span aria-hidden="true">{categoryIcon(row.category)}</span> {row.label}
          </span>
          <span className="barlist__track">
            {row.count > 0 && (
              <span
                className="barlist__fill"
                style={{
                  width: `${(row.count / max) * 100}%`,
                  background: categoryColor(row.category),
                }}
              />
            )}
          </span>
          <span className="barlist__value">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

function DepartmentTable({ departments }) {
  const active = departments.filter((row) => row.total_cases > 0);
  const max = Math.max(...active.map((row) => row.total_cases), 1);

  if (active.length === 0) {
    return <p className="muted">No cases have been routed to a department yet.</p>;
  }

  return (
    <table className="dept-table">
      <thead>
        <tr>
          <th scope="col">Department</th>
          <th scope="col">Caseload</th>
          <th scope="col" className="dept-table__num">
            Open
          </th>
          <th scope="col" className="dept-table__num">
            Resolved
          </th>
          <th scope="col" className="dept-table__num">
            Avg. resolution
          </th>
        </tr>
      </thead>
      <tbody>
        {active.map((row) => (
          <tr key={row.code ?? row.name}>
            <th scope="row">{row.name}</th>
            <td>
              <span className="dept-table__track">
                <span
                  className="dept-table__fill"
                  style={{ width: `${(row.total_cases / max) * 100}%` }}
                />
              </span>
            </td>
            <td className="dept-table__num">{row.open_cases}</td>
            <td className="dept-table__num">{row.resolved_cases}</td>
            <td className="dept-table__num">{formatDays(row.avg_resolution_days)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function HotspotList({ hotspots }) {
  if (hotspots.length === 0) {
    return (
      <p className="muted">
        No recurring locations yet — hotspots appear when the same area collects
        multiple reports.
      </p>
    );
  }

  return (
    <ol className="hotspot-list">
      {hotspots.map((spot, index) => (
        <li
          key={`${spot.latitude},${spot.longitude}`}
          className="hotspot"
        >
          <span className="hotspot__rank" aria-hidden="true">
            {index + 1}
          </span>
          <span className="hotspot__body">
            <span className="hotspot__place">
              {spot.address ??
                `${spot.latitude.toFixed(3)}, ${spot.longitude.toFixed(3)}`}
            </span>
            <span className="hotspot__meta">
              <span aria-hidden="true">{categoryIcon(spot.top_category)}</span>{" "}
              Mostly {spot.top_category_label} · {spot.case_count}{" "}
              {spot.case_count === 1 ? "problem" : "problems"}
            </span>
          </span>
          <span className="hotspot__count">
            {spot.report_count}
            <small>reports</small>
          </span>
        </li>
      ))}
    </ol>
  );
}

export default function AnalyticsPanel({ analytics }) {
  if (analytics.total_reports === 0) {
    return (
      <EmptyState
        icon="📊"
        title="No data to analyse yet"
        message="City-wide analytics will light up as soon as citizens start reporting issues."
      />
    );
  }

  const resolvedCount =
    analytics.by_status.find((row) => row.status === "RESOLVED")?.count ?? 0;

  return (
    <div className="analytics">
      <ul className="stat-grid stat-grid--analytics">
        <li className="stat-card stat-card--primary">
          <span className="stat-card__value">{analytics.total_reports}</span>
          <span className="stat-card__label">Reports received</span>
        </li>
        <li className="stat-card stat-card--info">
          <span className="stat-card__value">{analytics.open_issues}</span>
          <span className="stat-card__label">Active cases</span>
        </li>
        <li className="stat-card stat-card--success">
          <span className="stat-card__value">{resolvedCount}</span>
          <span className="stat-card__label">Cases resolved</span>
        </li>
        <li className="stat-card stat-card--neutral">
          <span className="stat-card__value">
            {formatDays(analytics.avg_resolution_days)}
          </span>
          <span className="stat-card__label">Avg. time to resolve</span>
        </li>
        <li className="stat-card stat-card--neutral">
          <span className="stat-card__value">{analytics.total_citizens}</span>
          <span className="stat-card__label">Registered citizens</span>
        </li>
      </ul>

      <div className="analytics__grid">
        <section className="card chart-card" aria-label="Cases by status">
          <h3 className="chart-card__title">Cases by status</h3>
          <StatusDonut
            byStatus={analytics.by_status}
            total={analytics.total_issues}
          />
        </section>

        <section className="card chart-card" aria-label="Cases by category">
          <h3 className="chart-card__title">Cases by category</h3>
          <CategoryBars byCategory={analytics.by_category} />
        </section>

        <section
          className="card chart-card chart-card--wide"
          aria-label="Department performance"
        >
          <h3 className="chart-card__title">Department performance</h3>
          <DepartmentTable departments={analytics.departments} />
        </section>

        <section
          className="card chart-card chart-card--wide"
          aria-label="Problem hotspots"
        >
          <h3 className="chart-card__title">
            Problem hotspots
            <span className="chart-card__hint">
              locations where reports keep coming back
            </span>
          </h3>
          <HotspotList hotspots={analytics.hotspots} />
        </section>
      </div>
    </div>
  );
}
