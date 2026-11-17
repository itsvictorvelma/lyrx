// The result: one group per line with four labeled rows (Original, Hiragana, Romaji, English).
import type { ReactNode } from "react";
import type { Line } from "./types";

const NOT_VERIFIED_TEXT = "Reading not verified";

interface FourVersionsProps {
  lines: Line[];
}

export function FourVersions({ lines }: FourVersionsProps) {
  return (
    <ol className="four-versions">
      {lines.map((line) => (
        <LineGroup key={line.index} line={line} />
      ))}
    </ol>
  );
}

function LineGroup({ line }: { line: Line }) {
  if (line.original === "") {
    return <li className="blank-line" />;
  }
  return (
    <li>
      <VersionRow label="Original">
        <span lang="ja">{line.original}</span>
      </VersionRow>
      <VersionRow label="Hiragana">
        <span lang="ja">{line.hiragana}</span>
        {line.readingVerified ? null : (
          <span className="reading-note">{NOT_VERIFIED_TEXT}</span>
        )}
      </VersionRow>
      <VersionRow label="Romaji">{line.romaji}</VersionRow>
      <VersionRow label="English">{line.english}</VersionRow>
    </li>
  );
}

function VersionRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="version-row">
      <span className="version-label">{label}</span>
      <span>{children}</span>
    </div>
  );
}
