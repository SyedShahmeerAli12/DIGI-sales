import type { ChatMessage } from "@/lib/types";
import UserBubble from "./UserBubble";
import AssistantBubble from "./AssistantBubble";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  return message.sender === "user" ? (
    <UserBubble message={message} />
  ) : (
    <AssistantBubble message={message} />
  );
}
