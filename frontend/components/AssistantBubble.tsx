import { Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "@/lib/types";
import SourceChip from "./SourceChip";
import MessageToolbar from "./MessageToolbar";

export default function AssistantBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex animate-fade-in items-start gap-2.5">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-red">
        <Bot className="h-3.5 w-3.5 text-white" />
      </span>

      <div className="flex max-w-[85%] flex-col gap-1.5 sm:max-w-[560px]">
        <div className="rounded-bubble border border-border bg-white px-4 py-3 text-sm leading-relaxed text-text-primary">
          <div className="flex flex-col gap-1.5">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="my-1">{children}</p>,
                ul: ({ children }) => (
                  <ul className="my-1 list-disc space-y-1 pl-5">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="my-1 list-decimal space-y-1 pl-5">{children}</ol>
                ),
                li: ({ children }) => <li className="pl-1">{children}</li>,
                strong: ({ children }) => (
                  <strong className="font-semibold text-text-heading">{children}</strong>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>

          {message.streaming && (
            <span className="mt-1 inline-flex gap-1 align-middle">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-placeholder [animation-delay:300ms]" />
            </span>
          )}

          {message.sources && message.sources.length > 0 && (
            <div className="mt-2.5 flex flex-col gap-1.5 border-t border-border-secondary pt-2.5">
              <span className="text-[11px] font-medium text-text-secondary">
                Sources
              </span>
              <div className="flex flex-wrap gap-1.5">
                {message.sources.map((s) => (
                  <SourceChip key={s.label} label={s.label} />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2.5 pl-1">
          <span className="text-[11px] text-text-placeholder">
            {message.timestamp}
          </span>
          <MessageToolbar text={message.text} />
        </div>
      </div>
    </div>
  );
}
