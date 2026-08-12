import { CATEGORIES } from "../constants";

/**
 * Single-choice category picker rendered as a real radio group so keyboard
 * and screen-reader users get native selection semantics.
 */
export default function CategorySelector({ value, onChange, error, describedBy }) {
  const errorId = error ? "category-error" : undefined;

  return (
    <fieldset
      className="category-selector"
      aria-describedby={[describedBy, errorId].filter(Boolean).join(" ") || undefined}
    >
      <legend className="visually-hidden">Issue category</legend>

      <div className="category-grid">
        {CATEGORIES.map((category) => {
          const selected = value === category.value;
          return (
            <label
              key={category.value}
              className={`category-option${selected ? " category-option--selected" : ""}`}
            >
              <input
                type="radio"
                name="category"
                value={category.value}
                checked={selected}
                onChange={() => onChange(category.value)}
                className="visually-hidden"
              />
              <span className="category-option__icon" aria-hidden="true">
                {category.icon}
              </span>
              <span className="category-option__body">
                <span className="category-option__label">{category.label}</span>
                <span className="category-option__hint">{category.hint}</span>
              </span>
              <span className="category-option__check" aria-hidden="true">
                {selected ? "✓" : ""}
              </span>
            </label>
          );
        })}
      </div>

      {error && (
        <p className="field-error" id={errorId} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
