// An audio file from the learner's computer, played by the browser; never uploaded or stored.
import { useEffect, useRef } from "react";
import type { AudioClock } from "./playback";

interface AudioFilePlayerProps {
  file: File;
  onClock: (clock: AudioClock | null) => void;
}

export function AudioFilePlayer({ file, onClock }: AudioFilePlayerProps) {
  const audio = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const element = audio.current;
    if (element === null) {
      return;
    }
    const url = URL.createObjectURL(file);
    element.src = url;
    onClock({
      timeMs: () => element.currentTime * 1000,
      seekMs: (milliseconds) => {
        element.currentTime = milliseconds / 1000;
      },
    });
    return () => {
      onClock(null);
      element.removeAttribute("src");
      URL.revokeObjectURL(url);
    };
  }, [file, onClock]);

  return (
    <audio ref={audio} controls aria-label={`Playing ${file.name}`}>
      Your browser cannot play this file.
    </audio>
  );
}
