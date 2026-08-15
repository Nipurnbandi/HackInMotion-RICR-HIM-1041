export function LoadingState({ label = "Loading…" }) {
  return (
    <div className="state state--loading" role="status" aria-live="polite">
      <span className="skeleton__bar skeleton__bar--w40" aria-hidden="true" />
      <span className="skeleton__bar" aria-hidden="true" />
      <span className="skeleton__bar skeleton__bar--w70" aria-hidden="true" />
      <p className="visually-hidden">{label}</p>
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div className="state state--error" role="alert">
      <span className="state__icon" aria-hidden="true">
        ⚠️
      </span>
      <h2 className="state__title">{title}</h2>
      <p className="state__message">{message}</p>
      {onRetry && (
        <button type="button" className="button button--primary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon = "📋", title, message, action }) {
  return (
    <div className="state state--empty">
      <span className="state__icon" aria-hidden="true">
        {icon}
      </span>
      <h2 className="state__title">{title}</h2>
      <p className="state__message">{message}</p>
      {action}
    </div>
  );
}
