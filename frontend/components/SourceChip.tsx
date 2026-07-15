import { ExternalLink } from "lucide-react";

export default function SourceChip({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 rounded-pill border border-brand-red/30 px-2.5 py-1 text-[11px] font-medium text-brand-red transition-colors hover:bg-brand-red/5"
    >
      <ExternalLink className="h-3 w-3" />
      {label}
    </button>
  );
}
