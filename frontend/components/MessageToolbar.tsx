"use client";

import { useState } from "react";
import { Copy, ThumbsUp, ThumbsDown, Check } from "lucide-react";

export default function MessageToolbar({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — silently ignore for demo purposes
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={handleCopy}
        aria-label="Copy message"
        className="flex h-6 w-6 items-center justify-center rounded-btn text-text-secondary transition-colors hover:bg-bg-page hover:text-text-primary"
      >
        {copied ? (
          <Check className="h-3 w-3 text-brand-red" />
        ) : (
          <Copy className="h-3 w-3" />
        )}
      </button>
      <button
        type="button"
        onClick={() => setLiked(liked === "up" ? null : "up")}
        aria-label="Good response"
        className={`flex h-6 w-6 items-center justify-center rounded-btn transition-colors hover:bg-bg-page ${
          liked === "up" ? "text-brand-red" : "text-text-secondary hover:text-text-primary"
        }`}
      >
        <ThumbsUp className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={() => setLiked(liked === "down" ? null : "down")}
        aria-label="Bad response"
        className={`flex h-6 w-6 items-center justify-center rounded-btn transition-colors hover:bg-bg-page ${
          liked === "down" ? "text-brand-red" : "text-text-secondary hover:text-text-primary"
        }`}
      >
        <ThumbsDown className="h-3 w-3" />
      </button>
    </div>
  );
}
