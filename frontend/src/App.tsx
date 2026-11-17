// The Lyrx page: the paste form above, the four versions or an error below; holds the request state.
import { useEffect, useRef, useState } from "react";
import { getFourVersions } from "./lyrics/api";
import {
  errorMessageFor,
  FALLBACK_MESSAGE,
  SERVER_UNREACHABLE_MESSAGE,
} from "./lyrics/errorMessages";
import { FourVersions } from "./lyrics/FourVersions";
import { PasteForm } from "./lyrics/PasteForm";
import type { FourVersionsResult, Line } from "./lyrics/types";

type PageState =
  | { kind: "idle" }
  | { kind: "waiting" }
  | { kind: "result"; lines: Line[] }
  | { kind: "error"; message: string };

function toPageState(result: FourVersionsResult): PageState {
  switch (result.kind) {
    case "lines":
      return { kind: "result", lines: result.lines };
    case "error":
      return { kind: "error", message: errorMessageFor(result.code) };
    case "unreadable":
      return { kind: "error", message: FALLBACK_MESSAGE };
    case "unreachable":
      return { kind: "error", message: SERVER_UNREACHABLE_MESSAGE };
  }
}

function lineCountText(count: number): string {
  return count === 1 ? "1 line" : `${String(count)} lines`;
}

function ResultHeading({ lines }: { lines: Line[] }) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Focus tells keyboard and screen-reader users the result arrived, and keeps focus
  // from being lost when the disabled button lets go of it.
  useEffect(() => {
    headingRef.current?.focus();
  }, [lines]);

  return (
    <h2 ref={headingRef} tabIndex={-1}>
      Four versions ({lineCountText(lines.length)})
    </h2>
  );
}

export function App() {
  const [state, setState] = useState<PageState>({ kind: "idle" });
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  // Focus is lost when the button disables; on an error, return it to the paste box
  // so the learner fixes the text where they left off.
  useEffect(() => {
    if (state.kind === "error") {
      textAreaRef.current?.focus();
    }
  }, [state]);

  async function submit(lyrics: string) {
    setState({ kind: "waiting" });
    setState(toPageState(await getFourVersions(lyrics)));
  }

  return (
    <main>
      <h1>Lyrx</h1>
      <PasteForm
        waiting={state.kind === "waiting"}
        textAreaRef={textAreaRef}
        onSubmit={(lyrics) => {
          void submit(lyrics);
        }}
      />
      {state.kind === "result" && (
        <section>
          <ResultHeading lines={state.lines} />
          <FourVersions lines={state.lines} />
        </section>
      )}
      {state.kind === "error" && (
        <p role="alert" className="error">
          <strong>Error:</strong> {state.message}
        </p>
      )}
    </main>
  );
}
