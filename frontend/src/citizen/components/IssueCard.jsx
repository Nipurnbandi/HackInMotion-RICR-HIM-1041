import { Link } from "react-router-dom";
import { categoryIcon, categoryLabel } from "../../shared/constants";
import StatusBadge from "../../shared/components/StatusBadge";

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function IssueCard({ issue }) {
  const location =
    issue.address ||
    (issue.latitude != null
      ? `${issue.latitude.toFixed(4)}, ${issue.longitude.toFixed(4)}`
      : "Location not recorded");

  return (
    <li className="issue-card">
      <Link to={`/citizen/issues/${issue.id}`} className="issue-card__link">
        <span className="issue-card__icon" aria-hidden="true">
          {categoryIcon(issue.category)}
        </span>

        <span className="issue-card__body">
          <span className="issue-card__title">{categoryLabel(issue.category)}</span>
          <span className="issue-card__location">{location}</span>
          <span className="issue-card__description">{issue.description}</span>
        </span>

        <span className="issue-card__aside">
          <StatusBadge status={issue.status} size="sm" />
          <span className="issue-card__tracking">{issue.tracking_id}</span>
          <span className="issue-card__date">{formatDate(issue.created_at)}</span>
        </span>
      </Link>
    </li>
  );
}
