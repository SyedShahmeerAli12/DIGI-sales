"use client";

import { MessageCircle, X } from "lucide-react";
import VersionCard from "./VersionCard";

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const content = (
    <>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-heading">Agent Tools</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close menu"
          className="flex h-7 w-7 items-center justify-center rounded-full text-text-secondary hover:bg-bg-page md:hidden"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

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
    </>
  );

  return (
    <>
      {/* Desktop: static sidebar */}
      <aside className="hidden h-full w-[220px] shrink-0 flex-col border-r border-border bg-white p-4 md:flex">
        {content}
      </aside>

      {/* Mobile: overlay + slide-in drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/30"
            onClick={onClose}
            aria-hidden="true"
          />
          <aside className="absolute left-0 top-0 flex h-full w-[240px] flex-col bg-white p-4 shadow-xl">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
