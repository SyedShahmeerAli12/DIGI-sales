"use client";

import { useRef, useState } from "react";
import { Mic, Play, Pause } from "lucide-react";
import type { ChatMessage } from "@/lib/types";

export default function UserBubble({ message }: { message: ChatMessage }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const togglePlayback = () => {
    if (!message.audioUrl) return;

    if (!audioRef.current) {
      audioRef.current = new Audio(message.audioUrl);
      audioRef.current.onended = () => setIsPlaying(false);
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  return (
    <div className="flex animate-fade-in flex-col items-end gap-1.5">
      <div className="max-w-[85%] rounded-bubble bg-brand-red px-4 py-2.5 text-sm leading-relaxed text-white sm:max-w-[560px]">
        {message.isVoice && message.audioUrl ? (
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={togglePlayback}
              aria-label={isPlaying ? "Pause voice message" : "Play voice message"}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/20 transition-colors hover:bg-white/30"
            >
              {isPlaying ? (
                <Pause className="h-3.5 w-3.5" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
            </button>
            <span className="flex flex-1 items-center gap-1">
              {Array.from({ length: 18 }).map((_, i) => (
                <span
                  key={i}
                  className="w-[3px] shrink-0 rounded-full bg-white/60"
                  style={{ height: `${6 + ((i * 7) % 14)}px` }}
                />
              ))}
            </span>
            <Mic className="h-3.5 w-3.5 shrink-0 text-white/80" />
          </div>
        ) : (
          message.text
        )}
      </div>
      <span className="pr-1 text-[11px] text-text-placeholder">
        {message.timestamp}
      </span>
    </div>
  );
}
