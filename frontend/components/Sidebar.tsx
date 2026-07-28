"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, MessageCircle, X } from "lucide-react";
import VersionCard from "./VersionCard";

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    {
      href: "/",
      icon: MessageCircle,
      title: "Chat",
      subtitle: "Conversational AI Interface",
    },
    {
      href: "/data-overview",
      icon: Database,
      title: "Data Overview",
      subtitle: "What data backs the answers",
    },
  ];

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

      <div className="flex flex-col gap-2">
        {navItems.map(({ href, icon: Icon, title, subtitle }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 rounded-card px-3.5 py-3 text-left shadow-sm transition-opacity hover:opacity-95 ${
                active
                  ? "bg-brand-red text-white"
                  : "border border-border bg-white text-text-primary"
              }`}
            >
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full ${
                  active ? "bg-white/15" : "bg-bg-page"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "" : "text-brand-red"}`} />
              </span>
              <span className="flex flex-col">
                <span className="text-sm font-semibold">{title}</span>
                <span
                  className={`text-[11px] font-medium ${
                    active ? "text-white/85" : "text-text-secondary"
                  }`}
                >
                  {subtitle}
                </span>
              </span>
            </Link>
          );
        })}
      </div>

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
