"use client";

import { useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";
import { openSourceDocument } from "@/lib/api";

export default function SourceChip({ label, page }: { label: string; page: number }) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      await openSourceDocument(page);
    } catch {
      // silently ignore — chip just won't open
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={`Open source document at page ${page}: ${label}`}
      className="inline-flex items-center gap-1 rounded-pill border border-brand-red/30 px-2.5 py-1 text-[11px] font-medium text-brand-red transition-colors hover:bg-brand-red/5"
    >
      {loading ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <ExternalLink className="h-3 w-3" />
      )}
      {label} (p.{page})
    </button>
  );
}
