"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/");
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-page p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <Image
            src="/dt-logo.png"
            alt="DigiTrends"
            width={48}
            height={48}
            className="mb-3 h-12 w-12 rounded-full"
          />
          <h1 className="text-2xl font-bold text-text-heading">DigiTrends</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Intelligent Sales Supervisor · DIGI
          </p>
        </div>

        <div className="rounded-card border border-border bg-white p-8 shadow-sm">
          <h2 className="mb-6 text-base font-semibold text-text-primary">
            Sign in to continue
          </h2>

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
                placeholder="you@digitrends.ai"
                className="w-full rounded-btn border border-border bg-white px-3.5 py-2.5 text-sm text-text-primary placeholder-text-placeholder outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-brand-red"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="Enter password"
                className="w-full rounded-btn border border-border bg-white px-3.5 py-2.5 text-sm text-text-primary placeholder-text-placeholder outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-brand-red"
              />
            </div>

            {error && (
              <p className="rounded-btn border border-brand-red/20 bg-brand-red/5 px-3 py-2 text-xs text-brand-red">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 w-full rounded-btn bg-brand-red py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-text-placeholder">
          DigiTrends · Authorized Personnel Only
        </p>
      </div>
    </div>
  );
}
