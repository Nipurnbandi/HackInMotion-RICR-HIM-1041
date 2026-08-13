import { STATUS_BY_VALUE } from "../constants";

export default function StatusBadge({ status, size = "md" }) {
  const meta = STATUS_BY_VALUE[status];
  const tone = meta?.tone ?? "neutral";
  const label = meta?.label ?? status;

  return (
    <span className={`status-badge status-badge--${tone} status-badge--${size}`}>
      <span className="status-badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
