"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import { clearToken } from "@/lib/api";

interface NavbarProps {
  onMenuClick?: () => void;
}

export default function Navbar({ onMenuClick }: NavbarProps) {
  const router = useRouter();

  const handleLogout = () => {
    clearToken();
    router.replace("/login");
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border bg-white px-3 sm:px-4">
      {/* Left */}
      <div className="flex min-w-0 items-center gap-2 sm:gap-2.5">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open menu"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-text-secondary hover:bg-bg-page md:hidden"
        >
          <Menu className="h-[18px] w-[18px]" />
        </button>
        <Image
          src="/dt-logo.png"
          alt="DigiTrends"
          width={28}
          height={28}
          className="h-7 w-7 shrink-0 rounded-full"
        />
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-bold text-text-heading">
            DigiTrends
          </span>
          <span className="hidden text-[11px] font-medium text-text-secondary sm:block">
            Investment AI Platform
          </span>
        </div>

        <span className="ml-1 hidden rounded-pill bg-brand-orange/15 px-2 py-0.5 text-[11px] font-semibold text-brand-orange sm:inline-flex sm:ml-1.5">
          Sandbox
        </span>

        <span className="ml-1.5 hidden items-center gap-1.5 text-xs text-text-secondary md:flex">
          <span className="text-border-divider">/</span>
          <span className="font-medium text-text-primary">
            Intelligent Sales Supervisor - DIGI
          </span>
        </span>
      </div>

      {/* Center intentionally empty */}

      {/* Right */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Logout"
          className="flex h-8 w-8 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-page hover:text-brand-red"
        >
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </div>
    </header>
  );
}
