import type { ChatMessage } from "@/lib/types";

export default function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex animate-fade-in flex-col items-end gap-1.5">
      <div className="max-w-[85%] rounded-bubble bg-brand-red px-4 py-2.5 text-sm leading-relaxed text-white sm:max-w-[560px]">
        {message.text}
      </div>
      <span className="pr-1 text-[11px] text-text-placeholder">
        {message.timestamp}
      </span>
    </div>
  );
}
