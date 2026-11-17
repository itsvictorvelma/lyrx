// The Lyrx page: the paste form above, the four versions or an error below; holds the request state.
import { useState } from "react";
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

export function App() {
  const [state, setState] = useState<PageState>({ kind: "idle" });

  async function submit(lyrics: string) {
    setState({ kind: "waiting" });
    setState(toPageState(await getFourVersions(lyrics)));
  }

  return (
    <main>
      <h1>Lyrx</h1>
      <PasteForm
        waiting={state.kind === "waiting"}
        onSubmit={(lyrics) => {
          void submit(lyrics);
        }}
      />
      {state.kind === "result" && <FourVersions lines={state.lines} />}
      {state.kind === "error" && (
        <p role="alert" className="error">
          <strong>Error:</strong> {state.message}
        </p>
      )}
    </main>
  );
}
