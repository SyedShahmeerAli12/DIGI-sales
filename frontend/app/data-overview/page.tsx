"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Database, FileText, Loader2 } from "lucide-react";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import { getDataOverview, getToken } from "@/lib/api";
import type { DataOverview } from "@/lib/types";

// Sales-organization hierarchy is rendered as a tree (Region -> Sales Manager
// -> Territory -> Area -> Order Booker), since that's the actual data model;
// everything else (products/customers/transactions) is shown as stat groups.
const HIERARCHY_TABLES = [
  "dim_region",
  "dim_sales_manager",
  "dim_territory",
  "dim_area",
  "dim_order_booker",
];

export default function DataOverviewPage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [data, setData] = useState<DataOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setCheckingAuth(false);
  }, [router]);

  useEffect(() => {
    if (checkingAuth) return;
    getDataOverview()
      .then(setData)
      .catch(() => setError("Could not load the data overview."));
  }, [checkingAuth]);

  if (checkingAuth) {
    return <div className="flex h-dvh items-center justify-center bg-bg-page" />;
  }

  const hierarchy = data?.fmcg_database.groups
    .flatMap((g) => g.entities)
    .filter((e) => HIERARCHY_TABLES.includes(e.table))
    .sort((a, b) => HIERARCHY_TABLES.indexOf(a.table) - HIERARCHY_TABLES.indexOf(b.table));

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-bg-page">
      <Navbar onMenuClick={() => setMobileSidebarOpen(true)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          mobileOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-4xl">
            <h1 className="text-xl font-semibold text-text-heading">Data Overview</h1>
            <p className="mt-1 text-sm text-text-secondary">
              What data backs DIGI&apos;s answers, and how much of it there is.
            </p>

            {error && (
              <p className="mt-6 text-sm text-brand-red">{error}</p>
            )}

            {!data && !error && (
              <div className="mt-10 flex items-center gap-2 text-sm text-text-secondary">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </div>
            )}

            {data && (
              <div className="mt-6 flex flex-col gap-6">
                {/* FMCG Sales Database */}
                <section className="rounded-card border border-border bg-white p-5">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-brand-red" />
                    <h2 className="text-sm font-semibold text-text-heading">
                      {data.fmcg_database.label}
                    </h2>
                  </div>
                  <p className="mt-1 text-[12px] text-text-secondary">
                    Covers {data.fmcg_database.date_range.start} through{" "}
                    {data.fmcg_database.date_range.end}
                  </p>

                  {/* Sales organization hierarchy, as a tree */}
                  <div className="mt-5 flex flex-col items-center gap-2">
                    {hierarchy?.map((entity, i) => (
                      <div key={entity.table} className="flex flex-col items-center">
                        <div className="flex min-w-[180px] flex-col items-center rounded-btn border border-brand-red/30 bg-brand-red/5 px-4 py-2 text-center">
                          <span className="text-[11px] font-medium text-text-secondary">
                            {entity.label}
                          </span>
                          <span className="text-lg font-semibold text-brand-red">
                            {entity.count.toLocaleString()}
                          </span>
                        </div>
                        {i < hierarchy.length - 1 && (
                          <div className="h-5 w-px bg-border-divider" />
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Products/customers + transactions as stat grids */}
                  {data.fmcg_database.groups
                    .filter((g) => g.name !== "Sales Organization")
                    .map((group) => (
                      <div key={group.name} className="mt-6">
                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-text-placeholder">
                          {group.name}
                        </h3>
                        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
                          {group.entities.map((entity) => (
                            <div
                              key={entity.table}
                              className="rounded-btn border border-border bg-bg-page px-3.5 py-3"
                            >
                              <div className="text-[11px] text-text-secondary">
                                {entity.label}
                              </div>
                              <div className="text-base font-semibold text-text-heading">
                                {entity.count.toLocaleString()}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                </section>

                {/* FAQ knowledge base */}
                <section className="rounded-card border border-border bg-white p-5">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-brand-red" />
                    <h2 className="text-sm font-semibold text-text-heading">
                      {data.faq_knowledge_base.label}
                    </h2>
                  </div>
                  <p className="mt-1 text-[12px] text-text-secondary">
                    {data.faq_knowledge_base.total_questions} curated Q&amp;A pairs across{" "}
                    {data.faq_knowledge_base.personas.length} personas
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {data.faq_knowledge_base.personas.map((p) => (
                      <div
                        key={p.name}
                        className="rounded-btn border border-border bg-bg-page px-3.5 py-3"
                      >
                        <div className="text-[11px] text-text-secondary">{p.name}</div>
                        <div className="text-base font-semibold text-text-heading">
                          {p.count}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
