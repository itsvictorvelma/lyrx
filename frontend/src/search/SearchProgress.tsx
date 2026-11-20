// While the server works: kana rain behind a terminal-style card with the steps, their marks, and the seconds.
import { useEffect, useState } from "react";
import { prefersReducedMotion } from "../browser";
import { KanaRain } from "./KanaRain";

const FINDING_TEXT = "Finding the song";
const OPENING_TEXT = "Getting the lyrics and translating";

// The terminal spinner's frames, and how often it moves.
const SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏";
const SPINNER_MS = 80;

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
    <section className="search-progress" aria-label="Getting your song ready">
      <KanaRain />
      <div className="progress-card">
        <div className="terminal-bar" aria-hidden="true">
          <span className="terminal-dots">
            <span />
            <span />
            <span />
          </span>
          lyrx@歌詞 ~ translate
        </div>
        <div className="progress-head">
          <p role="status" aria-live="polite">
            <span className="prompt" aria-hidden="true">
              &gt;{" "}
            </span>
            {active === undefined ? null : `${active.label}…`}
            {/* Remounted per step, so the count restarts at 0 for each request. */}
            <ElapsedSeconds key={stage} />
            <span className="cursor" aria-hidden="true">
              █
            </span>
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
      </div>
    </section>
  );
}

// "[ OK ]", a spinning "[ ⠹ ]", or "[ -- ]"; decorative, since the step says its state in words.
function StepMark({ state }: { state: Step["state"] }) {
  const inside =
    state === "done" ? "OK" : state === "active" ? <Spinner /> : "--";
  return (
    <span className="step-mark" aria-hidden="true">
      [ {inside} ]
    </span>
  );
}

function Spinner() {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion()) {
      return;
    }
    const timer = setInterval(() => {
      setFrame((count) => (count + 1) % SPINNER_FRAMES.length);
    }, SPINNER_MS);
    return () => {
      clearInterval(timer);
    };
  }, []);

  return <>{SPINNER_FRAMES[frame]}</>;
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
