import { useCallback, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import CategorySelector from "../components/CategorySelector";
import ImageUploader from "../components/ImageUploader";
import LocationPicker from "../components/LocationPicker";
import StatusBadge from "../../shared/components/StatusBadge";
import {
  CATEGORY_BY_VALUE,
  DESCRIPTION_MAX_LENGTH,
  DESCRIPTION_MIN_LENGTH,
} from "../../shared/constants";
import { formatCoordinates } from "../services/geocoding";
import { citizenService } from "../services/citizenService";

const STEPS = [
  { id: "category", title: "What is the problem?" },
  { id: "location", title: "Where is the problem?" },
  { id: "photo", title: "Add photo evidence" },
  { id: "description", title: "Describe the problem" },
  { id: "review", title: "Review & submit" },
];

const EMPTY_LOCATION = { latitude: null, longitude: null, address: null };

export default function ReportIssue() {
  const navigate = useNavigate();
  const headingRef = useRef(null);

  const [stepIndex, setStepIndex] = useState(0);
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState(EMPTY_LOCATION);
  const [photo, setPhoto] = useState(null);
  const [description, setDescription] = useState("");

  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(null);
  const [submitError, setSubmitError] = useState("");
  const [created, setCreated] = useState(null);

  const step = STEPS[stepIndex];
  const trimmedDescription = description.trim();

  const stepErrors = useMemo(
    () => ({
      category: !category ? "Please choose the type of problem you're reporting." : "",
      location:
        location.latitude == null
          ? "Please select the location of the problem on the map."
          : "",
      description:
        trimmedDescription.length === 0
          ? "Please describe the problem."
          : trimmedDescription.length < DESCRIPTION_MIN_LENGTH
            ? `Please add a little more detail (at least ${DESCRIPTION_MIN_LENGTH} characters).`
            : trimmedDescription.length > DESCRIPTION_MAX_LENGTH
              ? `Please shorten your description to ${DESCRIPTION_MAX_LENGTH} characters or fewer.`
              : "",
    }),
    [category, location.latitude, trimmedDescription]
  );

  const focusHeading = useCallback(() => {
    requestAnimationFrame(() => headingRef.current?.focus());
  }, []);

  function goTo(index) {
    setStepIndex(index);
    setSubmitError("");
    focusHeading();
  }

  function next() {
    const error = stepErrors[step.id];
    if (error) {
      setErrors((current) => ({ ...current, [step.id]: error }));
      return;
    }
    setErrors((current) => ({ ...current, [step.id]: "" }));
    goTo(Math.min(stepIndex + 1, STEPS.length - 1));
  }

  function back() {
    goTo(Math.max(stepIndex - 1, 0));
  }

  async function handleSubmit(event) {
    event?.preventDefault();

    const blocking = Object.fromEntries(
      Object.entries(stepErrors).filter(([, message]) => message)
    );
    if (Object.keys(blocking).length > 0) {
      setErrors(blocking);
      const firstBrokenStep = STEPS.findIndex((item) => blocking[item.id]);
      goTo(firstBrokenStep);
      return;
    }

    setSubmitting(true);
    setSubmitError("");
    setErrors({});
    setProgress(photo ? 0 : null);

    try {
      const issue = await citizenService.createIssue(
        {
          category,
          description: trimmedDescription,
          latitude: location.latitude,
          longitude: location.longitude,
          address: location.address,
          photo,
        },
        { onProgress: setProgress }
      );
      setCreated(issue);
    } catch (err) {
      if (err.fieldErrors) {
        setErrors(err.fieldErrors);
        const firstBrokenStep = STEPS.findIndex((item) => err.fieldErrors[item.id]);
        if (firstBrokenStep >= 0) goTo(firstBrokenStep);
      }
      setSubmitError(err.message || "We couldn't submit your report. Please try again.");
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  }

  if (created) {
    return <SuccessScreen issue={created} />;
  }

  const selectedCategory = CATEGORY_BY_VALUE[category];

  return (
    <div className="page page--narrow">
      <div className="page-heading">
        <h1>Report an issue</h1>
        <p className="muted">
          Five short steps. Your report goes straight to the city administration with a
          tracking ID.
        </p>
      </div>

      <ol className="stepper" aria-label="Reporting steps">
        {STEPS.map((item, index) => {
          const state =
            index === stepIndex ? "current" : index < stepIndex ? "done" : "upcoming";
          return (
            <li key={item.id} className={`stepper__item stepper__item--${state}`}>
              <button
                type="button"
                className="stepper__button"
                onClick={() => index < stepIndex && goTo(index)}
                disabled={index > stepIndex}
                aria-current={index === stepIndex ? "step" : undefined}
              >
                <span className="stepper__index" aria-hidden="true">
                  {index < stepIndex ? "✓" : index + 1}
                </span>
                <span className="stepper__label">{item.title}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <form className="card form-card" onSubmit={handleSubmit} noValidate>
        <h2 className="form-card__title" tabIndex={-1} ref={headingRef}>
          <span className="form-card__step">
            Step {stepIndex + 1} of {STEPS.length}
          </span>
          {step.title}
        </h2>

        {step.id === "category" && (
          <CategorySelector
            value={category}
            onChange={(value) => {
              setCategory(value);
              setErrors((current) => ({ ...current, category: "" }));
            }}
            error={errors.category}
          />
        )}

        {step.id === "location" && (
          <LocationPicker
            value={location}
            onChange={(value) => {
              setLocation(value);
              setErrors((current) => ({ ...current, location: "" }));
            }}
            error={errors.location || errors.latitude || errors.longitude}
          />
        )}

        {step.id === "photo" && (
          <ImageUploader
            value={photo}
            onChange={setPhoto}
            progress={progress}
            error={errors.photo}
          />
        )}

        {step.id === "description" && (
          <div className="field">
            <label className="field__label" htmlFor="description">
              Describe the problem
            </label>
            <p className="field-hint" id="description-help">
              What is wrong, how long has it been like this, and is anyone at risk?
            </p>
            <textarea
              id="description"
              className={`textarea${errors.description ? " textarea--error" : ""}`}
              rows={7}
              value={description}
              maxLength={DESCRIPTION_MAX_LENGTH}
              onChange={(event) => {
                setDescription(event.target.value);
                setErrors((current) => ({ ...current, description: "" }));
              }}
              aria-describedby={
                errors.description ? "description-help description-error" : "description-help"
              }
              aria-invalid={errors.description ? "true" : undefined}
            />
            <div className="field__footer">
              <span className="field-hint">
                Minimum {DESCRIPTION_MIN_LENGTH} characters
              </span>
              <span className="field-hint">
                {trimmedDescription.length}/{DESCRIPTION_MAX_LENGTH}
              </span>
            </div>
            {errors.description && (
              <p className="field-error" id="description-error" role="alert">
                {errors.description}
              </p>
            )}
          </div>
        )}

        {step.id === "review" && (
          <div className="review">
            <ReviewRow
              label="Category"
              onEdit={() => goTo(0)}
              value={
                selectedCategory ? (
                  <span>
                    <span aria-hidden="true">{selectedCategory.icon} </span>
                    {selectedCategory.label}
                  </span>
                ) : (
                  "Not selected"
                )
              }
            />
            <ReviewRow
              label="Location"
              onEdit={() => goTo(1)}
              value={
                <>
                  <span className="review__strong">
                    {location.address || "Address not available"}
                  </span>
                  <span className="review__muted">
                    {formatCoordinates(location.latitude, location.longitude)}
                  </span>
                </>
              }
            />
            <ReviewRow
              label="Photo evidence"
              onEdit={() => goTo(2)}
              value={photo ? photo.name : "No photo attached"}
            />
            <ReviewRow
              label="Description"
              onEdit={() => goTo(3)}
              value={<span className="review__description">{trimmedDescription}</span>}
            />

            <p className="review__note">
              Your report will be filed under your account and given a tracking ID. City
              staff review each report before work is scheduled.
            </p>
          </div>
        )}

        {submitError && (
          <div className="alert alert--error" role="alert">
            <strong>We couldn't submit your report.</strong>
            <p>{submitError}</p>
          </div>
        )}

        {submitting && (
          <p className="submitting-note" role="status" aria-live="polite">
            <span className="spinner spinner--sm" aria-hidden="true" />
            {progress != null && progress < 100
              ? `Uploading photo… ${progress}%`
              : "Submitting your report…"}
          </p>
        )}

        <div className="form-card__actions">
          {stepIndex > 0 ? (
            <button
              type="button"
              className="button button--secondary"
              onClick={back}
              disabled={submitting}
            >
              Back
            </button>
          ) : (
            <Link to="/citizen" className="button button--secondary">
              Cancel
            </Link>
          )}

          {step.id === "review" ? (
            <button
              key="submit"
              type="button"
              className="button button--primary"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? "Submitting…" : "Submit report"}
            </button>
          ) : (
            <button
              key="next"
              type="button"
              className="button button--primary"
              onClick={next}
            >
              Continue
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function ReviewRow({ label, value, onEdit }) {
  return (
    <div className="review__row">
      <div className="review__label">{label}</div>
      <div className="review__value">{value}</div>
      <button type="button" className="link link--button" onClick={onEdit}>
        Edit<span className="visually-hidden"> {label}</span>
      </button>
    </div>
  );
}

function SuccessScreen({ issue }) {
  return (
    <div className="page page--narrow">
      <div className="card success-card" role="status">
        <span className="success-card__icon" aria-hidden="true">
          ✓
        </span>
        <h1>Issue reported successfully</h1>
        <p className="muted">
          Thank you for helping improve your city. Your report has been sent to the city
          administration.
        </p>

        <dl className="success-card__details">
          <div>
            <dt>Tracking ID</dt>
            <dd className="success-card__tracking">{issue.tracking_id}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={issue.status} />
            </dd>
          </div>
        </dl>

        <p className="success-card__hint">
          Keep this tracking ID. You can follow the progress of this report at any time
          from My Reports.
        </p>

        <div className="success-card__actions">
          <Link to="/citizen/issues" className="button button--primary">
            View my reports
          </Link>
          <Link to={`/citizen/issues/${issue.id}`} className="button button--secondary">
            View this report
          </Link>
        </div>
      </div>
    </div>
  );
}
