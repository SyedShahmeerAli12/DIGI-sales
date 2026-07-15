"use client";

import { useState, type KeyboardEvent } from "react";
import { Paperclip, Mic, Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="sticky bottom-0 z-20 border-t border-border bg-white px-3 py-3 sm:px-5">
      <div className="flex w-full max-w-full items-center gap-1 rounded-input border border-border bg-white px-2 py-1.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:max-w-4xl xl:max-w-5xl">
        <button
          type="button"
          aria-label="Attach file"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-page hover:text-text-primary"
        >
          <Paperclip className="h-4 w-4" />
        </button>

        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          className="h-10 min-w-0 flex-1 bg-transparent text-sm text-text-primary placeholder-text-placeholder outline-none"
        />

        <button
          type="button"
          aria-label="Voice input"
          className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-page hover:text-text-primary sm:flex"
        >
          <Mic className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-red text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
