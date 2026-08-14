import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import StatusBadge from "../../shared/components/StatusBadge";
import CityMap from "../../shared/components/CityMap";
import { EmptyState, ErrorState, LoadingState } from "../../shared/components/States";
import { STATUSES, categoryIcon, categoryLabel } from "../../shared/constants";
import AnalyticsPanel from "../components/AnalyticsPanel";
import { adminService } from "../services/adminService";
import "../../styles/tokens.css";
import "../../styles/citizen.css";
import "../../styles/admin.css";

const VIEWS = [
  { id: "overview", label: "Command Center", icon: "🛰" },
  { id: "map", label: "Live City Map", icon: "🗺" },
  { id: "analytics", label: "Analytics", icon: "📊" },
];

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function priorityTone(score) {
  if (score >= 20) return "high";
  if (score >= 10) return "medium";
  return "low";
}

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [view, setView] = useState("overview");

  const [summary, setSummary] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [notifications, setNotifications] = useState({ items: [], unread: 0 });
  const [cases, setCases] = useState(null);
  const [department, setDepartment] = useState("");
  const [showInbox, setShowInbox] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [mapIssues, setMapIssues] = useState(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState("");
  const [colorMode, setColorMode] = useState("status");

  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [dashboard, departmentList, inbox, queue] = await Promise.all([
        adminService.getDashboard(),
        adminService.getDepartments(),
        adminService.getNotifications(),
        adminService.listCases(department || undefined),
      ]);
      setSummary(dashboard);
      setDepartments(departmentList);
      setNotifications(inbox);
      setCases(queue);
    } catch (err) {
      setError(err.message || "We couldn't load the city overview.");
    } finally {
      setLoading(false);
    }
  }, [department]);

  useEffect(() => {
    load();
  }, [load]);

  const loadMap = useCallback(async () => {
    setMapLoading(true);
    setMapError("");
    try {
      setMapIssues(await adminService.getMapIssues());
    } catch (err) {
      setMapError(err.message || "We couldn't load the city map.");
    } finally {
      setMapLoading(false);
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    setAnalyticsError("");
    try {
      setAnalytics(await adminService.getAnalytics());
    } catch (err) {
      setAnalyticsError(err.message || "We couldn't load the analytics.");
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view === "map" && mapIssues === null && !mapLoading) loadMap();
    if (view === "analytics" && analytics === null && !analyticsLoading) {
      loadAnalytics();
    }
  }, [view, mapIssues, mapLoading, loadMap, analytics, analyticsLoading, loadAnalytics]);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  async function openNotification(notification) {
    if (notification.is_read) return;
    try {
      await adminService.markNotificationRead(notification.id);
      setNotifications((current) => ({
        unread: Math.max(current.unread - 1, 0),
        items: current.items.map((item) =>
          item.id === notification.id ? { ...item, is_read: true } : item
        ),
      }));
    } catch {
      return;
    }
  }

  async function changeStatus(caseItem, newStatus) {
    if (newStatus === caseItem.status) return;
    try {
      await adminService.updateStatus(caseItem.id, newStatus);
      // Keep the lazily loaded views in sync with the new status.
      setMapIssues(null);
      setAnalytics(null);
      await load();
    } catch (err) {
      setError(err.message || "We couldn't update the status.");
    }
  }

  return (
    <div className="citizen-shell admin-dark">
      <div className="admin-aurora" aria-hidden="true" />
      <header className="citizen-header">
        <div className="citizen-header__inner">
          <span className="brand">
            <span className="brand__mark" aria-hidden="true">
              🏙
            </span>
            <span className="brand__text">
              SmartCity<span className="brand__sub">City Administration</span>
            </span>
          </span>
          <div className="admin-account">
            <button
              type="button"
              className="notif-bell"
              aria-expanded={showInbox}
              onClick={() => setShowInbox((open) => !open)}
            >
              🔔
              {notifications.unread > 0 && (
                <span className="notif-bell__count">{notifications.unread}</span>
              )}
              <span className="visually-hidden">
                {notifications.unread} unread notifications
              </span>
            </button>
            <span className="citizen-nav__email" title={user?.email}>
              {user?.email}
            </span>
            <button type="button" className="button button--ghost" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="citizen-main">
        <div className="page">
          <div className="page-heading">
            <h1>Admin Dashboard</h1>
            <p className="muted">
              Every real-world problem appears once, routed to its department and
              ordered by severity, people affected, and days ignored.
            </p>
          </div>

          <div className="admin-tabs" role="group" aria-label="Dashboard views">
            {VIEWS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`admin-tab${view === item.id ? " admin-tab--active" : ""}`}
                aria-pressed={view === item.id}
                onClick={() => setView(item.id)}
              >
                <span aria-hidden="true">{item.icon}</span> {item.label}
              </button>
            ))}
          </div>

          {showInbox && (
            <section className="card notif-panel" aria-label="Notifications">
              <h2 className="card__title">Notifications</h2>
              {notifications.items.length === 0 ? (
                <p className="muted">Nothing yet — new cases will appear here.</p>
              ) : (
                <ul className="notif-list">
                  {notifications.items.map((notification) => (
                    <li key={notification.id}>
                      <button
                        type="button"
                        className={`notif-item${
                          notification.is_read ? "" : " notif-item--unread"
                        }`}
                        onClick={() => openNotification(notification)}
                      >
                        <span className="notif-item__message">
                          {notification.message.split("\n")[0]}
                        </span>
                        <span className="notif-item__meta">
                          To {notification.department_name} &lt;
                          {notification.department_email}&gt;
                        </span>
                        <span className="notif-item__meta">
                          Created {formatDateTime(notification.created_at)}
                          {notification.sent_at
                            ? ` · Email delivered ${formatDateTime(notification.sent_at)}`
                            : " · Email pending — will retry"}
                          {notification.is_read ? "" : " · unread"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {view === "overview" && (
            <>
              {loading && <LoadingState label="Loading the city overview…" />}

              {!loading && error && (
                <ErrorState
                  title="We couldn't load the city overview"
                  message={error}
                  onRetry={load}
                />
              )}

              {!loading && !error && summary && cases && (
                <>
                  <ul className="stat-grid">
                    <li className="stat-card stat-card--primary">
                      <span className="stat-card__value">{summary.total_issues}</span>
                      <span className="stat-card__label">Open problems (cases)</span>
                    </li>
                    <li className="stat-card stat-card--info">
                      <span className="stat-card__value">
                        {cases.reduce((sum, c) => sum + c.citizen_count, 0)}
                      </span>
                      <span className="stat-card__label">Reports received</span>
                    </li>
                    <li className="stat-card stat-card--neutral">
                      <span className="stat-card__value">{summary.total_citizens}</span>
                      <span className="stat-card__label">Registered citizens</span>
                    </li>
                  </ul>

                  <div
                    className="filter-chips"
                    role="group"
                    aria-label="Filter by department"
                  >
                    <button
                      type="button"
                      className={`chip${department === "" ? " chip--active" : ""}`}
                      aria-pressed={department === ""}
                      onClick={() => setDepartment("")}
                    >
                      All departments
                    </button>
                    {departments.map((item) => (
                      <button
                        key={item.code}
                        type="button"
                        className={`chip${department === item.code ? " chip--active" : ""}`}
                        aria-pressed={department === item.code}
                        onClick={() => setDepartment(item.code)}
                      >
                        {item.name} ({item.open_cases})
                      </button>
                    ))}
                  </div>

                  <section aria-labelledby="queue-heading">
                    <h2 className="section-title" id="queue-heading">
                      Work queue — highest priority first
                    </h2>

                    {cases.length === 0 ? (
                      <EmptyState
                        icon="🏙"
                        title="No open problems"
                        message="When citizens report civic issues, they will appear here as prioritised cases."
                      />
                    ) : (
                      <ul className="issue-list">
                        {cases.map((item) => (
                          <li key={item.id} className="issue-card">
                            <div className="issue-card__link admin-case">
                              <span
                                className={`priority-badge priority-badge--${priorityTone(
                                  item.priority_score
                                )}`}
                                title="severity × citizens × age"
                              >
                                {item.priority_score.toFixed(1)}
                                <small>priority</small>
                              </span>

                              <span className="issue-card__icon" aria-hidden="true">
                                {categoryIcon(item.category)}
                              </span>

                              <span className="issue-card__body">
                                <span className="issue-card__title">
                                  {categoryLabel(item.category)}
                                </span>
                                <span className="issue-card__location">
                                  {item.address ||
                                    `${item.latitude?.toFixed(4)}, ${item.longitude?.toFixed(4)}`}
                                </span>
                                <span className="issue-card__description">
                                  {item.description}
                                </span>
                              </span>

                              <span className="issue-card__aside">
                                <StatusBadge status={item.status} size="sm" />
                                <span className="status-control">
                                  <label
                                    className="visually-hidden"
                                    htmlFor={`status-${item.id}`}
                                  >
                                    Update status for {categoryLabel(item.category)}{" "}
                                    {item.tracking_id}
                                  </label>
                                  <select
                                    id={`status-${item.id}`}
                                    className="status-select"
                                    value={item.status}
                                    onChange={(event) =>
                                      changeStatus(item, event.target.value)
                                    }
                                  >
                                    {STATUSES.map((option) => (
                                      <option key={option.value} value={option.value}>
                                        {option.label}
                                      </option>
                                    ))}
                                  </select>
                                </span>
                                {item.department_name && (
                                  <span className="dept-badge">{item.department_name}</span>
                                )}
                                <span className="case-meta">
                                  👥 {item.citizen_count}{" "}
                                  {item.citizen_count === 1 ? "citizen" : "citizens"}
                                </span>
                                <span className="case-meta case-meta--muted">
                                  {item.days_open === 0
                                    ? "reported today"
                                    : `open ${item.days_open} ${
                                        item.days_open === 1 ? "day" : "days"
                                      }`}
                                </span>
                                <span className="issue-card__date">
                                  {formatDate(item.created_at)}
                                </span>
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                </>
              )}
            </>
          )}

          {view === "map" && (
            <section aria-labelledby="map-heading">
              <h2 className="section-title" id="map-heading">
                Live city map — every open report at a glance
              </h2>

              {mapLoading && <LoadingState label="Loading the live city map…" />}

              {!mapLoading && mapError && (
                <ErrorState
                  title="We couldn't load the city map"
                  message={mapError}
                  onRetry={loadMap}
                />
              )}

              {!mapLoading && !mapError && mapIssues && (
                mapIssues.length === 0 ? (
                  <EmptyState
                    icon="🗺"
                    title="Nothing on the map yet"
                    message="Reported issues with a location will appear here as live markers."
                  />
                ) : (
                  <CityMap
                    issues={mapIssues}
                    colorMode={colorMode}
                    onColorModeChange={setColorMode}
                    theme="dark"
                  />
                )
              )}
            </section>
          )}

          {view === "analytics" && (
            <section aria-labelledby="analytics-heading">
              <h2 className="section-title" id="analytics-heading">
                City analytics — live from the reports database
              </h2>

              {analyticsLoading && <LoadingState label="Crunching the city data…" />}

              {!analyticsLoading && analyticsError && (
                <ErrorState
                  title="We couldn't load the analytics"
                  message={analyticsError}
                  onRetry={loadAnalytics}
                />
              )}

              {!analyticsLoading && !analyticsError && analytics && (
                <AnalyticsPanel analytics={analytics} />
              )}
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
