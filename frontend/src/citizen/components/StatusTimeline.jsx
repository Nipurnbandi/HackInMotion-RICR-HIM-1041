import { STATUS_BY_VALUE, STATUS_FLOW } from "../../shared/constants";
import { useI18n } from "../../shared/i18n";

export default function StatusTimeline({ status }) {
  const { t } = useI18n();

  if (status === "REJECTED") {
    const meta = STATUS_BY_VALUE.REJECTED;
    return (
      <ol className="timeline" aria-label="Report progress">
        <li className="timeline__step timeline__step--done">
          <span className="timeline__marker" aria-hidden="true" />
          <div>
            <p className="timeline__label">
              {t("status.SUBMITTED.label", "Submitted")}
            </p>
            <p className="timeline__hint">
              {t("status.SUBMITTED.desc", "We have received your report.")}
            </p>
          </div>
        </li>
        <li className="timeline__step timeline__step--rejected timeline__step--current">
          <span className="timeline__marker" aria-hidden="true" />
          <div>
            <p className="timeline__label">
              {t("status.REJECTED.label", "Rejected")}{" "}
              <span className="timeline__current-tag">
                {t("timeline.current", "Current")}
              </span>
            </p>
            <p className="timeline__hint">
              {t("status.REJECTED.desc", meta.description)}
            </p>
          </div>
        </li>
      </ol>
    );
  }

  const currentIndex = STATUS_FLOW.indexOf(status);

  return (
    <ol className="timeline" aria-label="Report progress">
      {STATUS_FLOW.map((step, index) => {
        const meta = STATUS_BY_VALUE[step];
        const isDone = index < currentIndex;
        const isCurrent = index === currentIndex;
        const state = isCurrent ? "current" : isDone ? "done" : "upcoming";

        return (
          <li
            key={step}
            className={`timeline__step timeline__step--${state}`}
            aria-current={isCurrent ? "step" : undefined}
          >
            <span className="timeline__marker" aria-hidden="true" />
            <div>
              <p className="timeline__label">
                {t(`status.${step}.label`, meta.label)}
                {isCurrent && (
                  <span className="timeline__current-tag">
                    {t("timeline.current", "Current")}
                  </span>
                )}
              </p>
              <p className="timeline__hint">
                {t(`status.${step}.desc`, meta.description)}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
