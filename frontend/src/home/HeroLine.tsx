// The home page's hero: one invented line, sung part by part, its readings appearing as it goes.
import { useEffect, useState } from "react";
import { prefersReducedMotion } from "../browser";
import {
  englishShownAt,
  HERO_ENGLISH,
  HERO_LABEL,
  HERO_LAST_TICK,
  HERO_PARTS,
  HERO_TICK_MS,
  partStateAt,
} from "./heroTiming";

export function HeroLine() {
  // With reduced motion the line starts, and stays, fully shown.
  const [tick, setTick] = useState(() =>
    prefersReducedMotion() ? HERO_LAST_TICK : 0,
  );
  const finished = tick >= HERO_LAST_TICK;

  useEffect(() => {
    if (finished) {
      return;
    }
    const timer = window.setTimeout(() => {
      setTick((current) => current + 1);
    }, HERO_TICK_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [tick, finished]);

  return (
    <figure className="hero-line" role="img" aria-label={HERO_LABEL}>
      <div className="hero-parts" lang="ja" aria-hidden="true">
        {HERO_PARTS.map((part, index) => (
          <div
            key={part.original}
            className="hero-part"
            data-state={partStateAt(tick, index)}
          >
            <span className="hero-original">{part.original}</span>
            <span className="hero-hiragana">{part.hiragana}</span>
            <span className="hero-romaji" lang="en">
              {part.romaji}
            </span>
          </div>
        ))}
      </div>
      <p
        className="hero-english"
        aria-hidden="true"
        data-shown={englishShownAt(tick)}
      >
        {HERO_ENGLISH}
      </p>
    </figure>
  );
}
