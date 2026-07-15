export default function VersionCard() {
  return (
    <div className="rounded-card bg-bg-page p-3.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary">
          Model Version
        </span>
        <span className="rounded-pill bg-brand-red px-2 py-0.5 text-[11px] font-semibold text-white">
          v2.1.3
        </span>
      </div>
      <div className="my-2.5 h-px w-full bg-border-divider" />
      <div className="text-[11px] text-text-secondary">
        Last updated:
        <div className="mt-0.5 text-xs font-medium text-text-primary">
          15 July, 2026
        </div>
      </div>
    </div>
  );
}
