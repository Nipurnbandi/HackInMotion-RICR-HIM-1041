import { STATUS_BY_VALUE } from "../constants";
import { useI18n } from "../i18n";

export default function StatusBadge({ status, size = "md" }) {
  const { t } = useI18n();
  const meta = STATUS_BY_VALUE[status];
  const tone = meta?.tone ?? "neutral";
  const label = t(`status.${status}.label`, meta?.label ?? status);

  return (
    <span className={`status-badge status-badge--${tone} status-badge--${size}`}>
      <span className="status-badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
