"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import ChatHeader from "@/components/ChatHeader";
import ChatWindow from "@/components/ChatWindow";
import ChatInput from "@/components/ChatInput";
import { getToken, streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// crypto.randomUUID() requires a secure context (HTTPS or localhost) — this app
// is also served over plain HTTP on a VPS IP, so it needs a fallback.
function generateId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function Home() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setCheckingAuth(false);
  }, [router]);

  const handleSend = (text: string, audioUrl?: string) => {
    const userMessage: ChatMessage = {
      id: generateId(),
      sender: "user",
      text,
      timestamp: formatTime(),
      isVoice: !!audioUrl,
      audioUrl,
    };

    const assistantId = generateId();
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      sender: "assistant",
      text: "",
      timestamp: formatTime(),
      streaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsResponding(true);

    const updateAssistant = (updater: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? updater(m) : m))
      );
    };

    streamChat(text, {
      onSources: (sources) => {
        updateAssistant((m) => ({
          ...m,
          sources: sources.map((label) => ({ label })),
        }));
      },
      onToken: (chunk) => {
        updateAssistant((m) => ({ ...m, text: m.text + chunk }));
      },
      onDone: () => {
        updateAssistant((m) => ({ ...m, streaming: false }));
        setIsResponding(false);
      },
      onError: (message) => {
        updateAssistant((m) => ({
          ...m,
          text: message || "Something went wrong. Please try again.",
          streaming: false,
        }));
        setIsResponding(false);
      },
    });
  };

  if (checkingAuth) {
    return <div className="flex h-dvh items-center justify-center bg-bg-page" />;
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-bg-page">
      <Navbar onMenuClick={() => setMobileSidebarOpen(true)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          mobileOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />
        <main className="flex flex-1 flex-col overflow-hidden">
          <ChatHeader />
          <ChatWindow messages={messages} />
          <ChatInput onSend={handleSend} disabled={isResponding} />
        </main>
      </div>
    </div>
  );
}
