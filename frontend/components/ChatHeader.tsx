import { Bot } from "lucide-react";

export default function ChatHeader() {
  return (
    <div className="sticky top-0 z-20 border-b border-border bg-white px-5 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-red">
            <Bot className="h-4 w-4 text-white" />
          </span>
          <div className="flex flex-col leading-tight">
            <span className="text-base font-semibold text-text-heading">
              DIGI Agent
            </span>
            <span className="text-xs text-text-secondary">AI Assistant</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="rounded-pill bg-brand-orange/15 px-2 py-0.5 text-[11px] font-semibold text-brand-orange">
            SANDBOX
          </span>
          <span className="rounded-pill bg-bg-page px-2 py-0.5 text-[11px] font-semibold text-text-secondary">
            v2.1.3
          </span>
        </div>
      </div>
    </div>
  );
}
