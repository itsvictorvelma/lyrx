// While the server works: the steps with done / in progress / waiting marks, seconds, placeholder rows.
import { useEffect, useState } from "react";

export const FINDING_TEXT = "Finding the song";
export const OPENING_TEXT = "Getting the lyrics and translating";
const PLACEHOLDER_ROWS = 8;

export type Stage = "finding" | "opening" | "opening-found";

interface Step {
  label: string;
  state: "done" | "active" | "waiting";
}

// A search shows both steps; opening a song directly shows only the second.
function stepsFor(stage: Stage): Step[] {
  if (stage === "opening") {
    return [{ label: OPENING_TEXT, state: "active" }];
  }
  const found = stage === "opening-found";
  return [
    { label: FINDING_TEXT, state: found ? "done" : "active" },
    { label: OPENING_TEXT, state: found ? "active" : "waiting" },
  ];
}

export function SearchProgress({ stage }: { stage: Stage }) {
  const steps = stepsFor(stage);
  const active = steps.find((step) => step.state === "active");

  return (
    <section
      className="page search-progress"
      aria-label="Getting your song ready"
    >
      <div className="progress-head">
        <p role="status" aria-live="polite">
          {active === undefined ? null : `${active.label}…`}
          {/* Remounted per step, so the count restarts at 0 for each request. */}
          <ElapsedSeconds key={stage} />
        </p>
      </div>
      <ol className="steps" aria-label="Steps">
        {steps.map((step) => (
          <li key={step.label} className={`step step-${step.state}`}>
            <StepMark state={step.state} />
            {step.label}
            <span className="visually-hidden">
              {step.state === "done"
                ? " (done)"
                : step.state === "active"
                  ? " (in progress)"
                  : " (waiting)"}
            </span>
          </li>
        ))}
      </ol>
      <div className="placeholder-rows" aria-hidden="true">
        {Array.from({ length: PLACEHOLDER_ROWS }, (_, row) => (
          <div key={row} className="placeholder-row">
            <span className="shimmer shimmer-wide" />
            <span className="shimmer" />
            <span className="shimmer" />
            <span className="shimmer" />
          </div>
        ))}
      </div>
    </section>
  );
}

function StepMark({ state }: { state: Step["state"] }) {
  if (state === "done") {
    return (
      <svg viewBox="0 0 24 24" className="icon step-mark" aria-hidden="true">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 24 24"
      className={state === "active" ? "icon step-mark spin" : "icon step-mark"}
      aria-hidden="true"
    >
      {state === "active" ? (
        <path d="M21 12a9 9 0 1 1-6.2-8.6" />
      ) : (
        <circle cx="12" cy="12" r="8" />
      )}
    </svg>
  );
}

function ElapsedSeconds() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((count) => count + 1);
    }, 1000);
    return () => {
      clearInterval(timer);
    };
  }, []);

  // Hidden from screen readers, so the live region does not announce every second.
  return <span aria-hidden="true"> {seconds} s</span>;
}
