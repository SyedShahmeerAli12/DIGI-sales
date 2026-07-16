"use client";

import { useRef, useState } from "react";
import { Bot, Volume2, Loader2, Square } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "@/lib/types";
import { speakText } from "@/lib/api";
import SourceChip from "./SourceChip";
import MessageToolbar from "./MessageToolbar";

export default function AssistantBubble({ message }: { message: ChatMessage }) {
  const [voiceState, setVoiceState] = useState<"idle" | "loading" | "playing">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleVoiceClick = async () => {
    if (voiceState === "playing") {
      audioRef.current?.pause();
      setVoiceState("idle");
      return;
    }
    if (voiceState === "loading" || !message.text.trim()) return;

    setVoiceState("loading");
    try {
      const url = await speakText(message.text);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setVoiceState("idle");
      audio.onerror = () => setVoiceState("idle");
      await audio.play();
      setVoiceState("playing");
    } catch {
      setVoiceState("idle");
    }
  };

  return (
    <div className="flex animate-fade-in items-start gap-2.5">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-red">
        <Bot className="h-3.5 w-3.5 text-white" />
      </span>

      <div className="flex max-w-[85%] flex-col gap-1.5 sm:max-w-[560px]">
        <div className="rounded-bubble border border-border bg-white px-4 py-3 text-sm leading-relaxed text-text-primary">
          <div className="flex flex-col gap-1.5">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="my-1">{children}</p>,
                ul: ({ children }) => (
                  <ul className="my-1 list-disc space-y-1 pl-5">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="my-1 list-decimal space-y-1 pl-5">{children}</ol>
                ),
                li: ({ children }) => <li className="pl-1">{children}</li>,
                strong: ({ children }) => (
                  <strong className="font-semibold text-text-heading">{children}</strong>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>

          {message.streaming && (
            <span className="mt-1 inline-flex gap-1 align-middle">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder [animation-delay:300ms]" />
            </span>
          )}

          {message.sources && message.sources.length > 0 && (
            <div className="mt-2.5 flex flex-col gap-1.5 border-t border-border-secondary pt-2.5">
              <span className="text-[11px] font-medium text-text-secondary">
                Sources
              </span>
              <div className="flex flex-wrap gap-1.5">
                {message.sources.map((s) => (
                  <SourceChip key={s.label} label={s.label} />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2.5 pl-1">
          <span className="text-[11px] text-text-placeholder">
            {message.timestamp}
          </span>
          <MessageToolbar text={message.text} />
          {!message.streaming && message.text.trim() && (
            <button
              type="button"
              onClick={handleVoiceClick}
              aria-label={voiceState === "playing" ? "Stop voice playback" : "Play as voice"}
              className="flex h-6 w-6 items-center justify-center rounded-btn text-text-secondary transition-colors hover:bg-bg-page hover:text-text-primary"
            >
              {voiceState === "loading" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : voiceState === "playing" ? (
                <Square className="h-3 w-3" />
              ) : (
                <Volume2 className="h-3 w-3" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
