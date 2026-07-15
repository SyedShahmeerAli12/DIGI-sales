"use client";

import { MessageCircle } from "lucide-react";
import VersionCard from "./VersionCard";

export default function Sidebar() {
  return (
    <aside className="hidden h-full w-[220px] shrink-0 flex-col border-r border-border bg-white p-4 md:flex">
      <h2 className="mb-3 text-base font-semibold text-text-heading">
        Agent Tools
      </h2>

      <button
        type="button"
        className="flex items-center gap-2.5 rounded-card bg-brand-red px-3.5 py-3 text-left text-white shadow-sm transition-opacity hover:opacity-95"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/15">
          <MessageCircle className="h-4 w-4" />
        </span>
        <span className="flex flex-col">
          <span className="text-sm font-semibold">Chat</span>
          <span className="text-[11px] font-medium text-white/85">
            Conversational AI Interface
          </span>
        </span>
      </button>

      <div className="mt-auto pt-4">
        <VersionCard />
      </div>
    </aside>
  );
}
