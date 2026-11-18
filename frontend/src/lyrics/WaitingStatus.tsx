// The status line while the server works: what it is doing, and the seconds elapsed.
import { useEffect, useState } from "react";

interface WaitingStatusProps {
  // What the server is doing, or null when nothing runs.
  text: string | null;
}

export function WaitingStatus({ text }: WaitingStatusProps) {
  return (
    <p role="status" aria-live="polite" className="muted">
      {text}
      {/* Remounted per step, so the count restarts at 0 for each request. */}
      {text !== null && <ElapsedSeconds key={text} />}
    </p>
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
