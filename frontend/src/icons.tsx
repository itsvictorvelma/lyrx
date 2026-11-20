// Every icon on the page: small line drawings in the text colour, hidden from screen readers.
import type { ReactNode } from "react";

function Icon({
  filled = false,
  children,
}: {
  filled?: boolean;
  children: ReactNode;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={filled ? "icon icon-filled" : "icon"}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function SearchIcon() {
  return (
    <Icon>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </Icon>
  );
}

export function SunIcon() {
  return (
    <Icon>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Icon>
  );
}

export function MoonIcon() {
  return (
    <Icon>
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </Icon>
  );
}

export function CloseIcon() {
  return (
    <Icon>
      <path d="M18 6 6 18M6 6l12 12" />
    </Icon>
  );
}

export function BackIcon() {
  return (
    <Icon>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </Icon>
  );
}

// Arrows out to enter Focus mode, arrows in to leave it.
export function FocusIcon({ exit = false }: { exit?: boolean }) {
  return (
    <Icon>
      <path
        d={
          exit
            ? "M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"
            : "M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"
        }
      />
    </Icon>
  );
}

export function BookmarkIcon({ filled }: { filled: boolean }) {
  return (
    <Icon filled={filled}>
      <path d="M6 3h12v18l-6-4-6 4z" />
    </Icon>
  );
}

export function PlayIcon() {
  return (
    <Icon filled>
      <path d="M8 5v14l11-7z" />
    </Icon>
  );
}

export function PauseIcon() {
  return (
    <Icon filled>
      <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
    </Icon>
  );
}

export function PreviousIcon() {
  return (
    <Icon>
      <path d="M19 20 9 12l10-8v16z" />
      <path d="M5 19V5" />
    </Icon>
  );
}

export function NextIcon() {
  return (
    <Icon>
      <path d="M5 4l10 8-10 8V4z" />
      <path d="M19 5v14" />
    </Icon>
  );
}

export function LoopIcon() {
  return (
    <Icon>
      <path d="M17 2l4 4-4 4" />
      <path d="M3 11V9a3 3 0 0 1 3-3h15" />
      <path d="M7 22l-4-4 4-4" />
      <path d="M21 13v2a3 3 0 0 1-3 3H3" />
    </Icon>
  );
}

// A speaker with sound waves, or crossed out when muted.
export function VolumeIcon({ muted }: { muted: boolean }) {
  return (
    <Icon>
      <path d="M11 5 6 9H3v6h3l5 4V5z" />
      {muted ? (
        <path d="m16 9 5 6M21 9l-5 6" />
      ) : (
        <path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />
      )}
    </Icon>
  );
}

export function VideoIcon() {
  return (
    <Icon>
      <rect x="2" y="5" width="15" height="14" rx="2" />
      <path d="m17 10 5-3v10l-5-3" />
    </Icon>
  );
}

export function LinkIcon() {
  return (
    <Icon>
      <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
    </Icon>
  );
}

export function MusicIcon() {
  return (
    <Icon>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </Icon>
  );
}

export function KeyboardIcon() {
  return (
    <Icon>
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8" />
    </Icon>
  );
}
