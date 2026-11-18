// A YouTube video in the page through the privacy-enhanced embed, reporting its time as a clock.
import { useEffect, useRef } from "react";
import type { AudioClock } from "./playback";

const API_URL = "https://www.youtube.com/iframe_api";
const EMBED_HOST = "https://www.youtube-nocookie.com";

// The few parts of YouTube's player script the page uses; its types are not a dependency.
export interface YouTubePlayerHandle {
  getCurrentTime?: () => number;
  seekTo?: (seconds: number, allowSeekAhead: boolean) => void;
  destroy: () => void;
}

interface YouTubeNamespace {
  Player: new (
    element: HTMLElement,
    options: {
      videoId: string;
      host: string;
      width: string;
      height: string;
      playerVars: Record<string, number>;
    },
  ) => YouTubePlayerHandle;
}

declare global {
  interface Window {
    YT?: YouTubeNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let loading: Promise<YouTubeNamespace> | null = null;

// YouTube's player script, added to the page once.
function loadYouTube(): Promise<YouTubeNamespace> {
  if (window.YT?.Player !== undefined) {
    return Promise.resolve(window.YT);
  }
  loading ??= new Promise((resolve, reject) => {
    window.onYouTubeIframeAPIReady = () => {
      if (window.YT !== undefined) {
        resolve(window.YT);
      }
    };
    const script = document.createElement("script");
    script.src = API_URL;
    // Offline or blocked: forget this attempt, so the next video tries again.
    script.onerror = () => {
      loading = null;
      script.remove();
      reject(new Error("YouTube player script did not load"));
    };
    document.head.append(script);
  });
  return loading;
}

interface YouTubePlayerProps {
  videoId: string;
  onClock: (clock: AudioClock | null) => void;
  onLoadError: () => void;
}

export function YouTubePlayer({
  videoId,
  onClock,
  onLoadError,
}: YouTubePlayerProps) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let player: YouTubePlayerHandle | null = null;
    let active = true;
    loadYouTube().then(
      (youTube) => {
        if (!active || container.current === null) {
          return;
        }
        // YouTube replaces this element with its iframe, so React never owns it.
        const target = document.createElement("div");
        container.current.replaceChildren(target);
        const created = new youTube.Player(target, {
          videoId,
          host: EMBED_HOST,
          width: "100%",
          height: "100%",
          playerVars: { playsinline: 1, rel: 0 },
        });
        player = created;
        onClock({
          timeMs: () =>
            created.getCurrentTime === undefined
              ? null
              : created.getCurrentTime() * 1000,
          seekMs: (milliseconds) => {
            created.seekTo?.(milliseconds / 1000, true);
          },
        });
      },
      () => {
        if (active) {
          onLoadError();
        }
      },
    );
    return () => {
      active = false;
      onClock(null);
      player?.destroy();
    };
  }, [videoId, onClock, onLoadError]);

  return <div className="video-frame" ref={container} />;
}
