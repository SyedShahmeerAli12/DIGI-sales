export type Sender = "user" | "assistant";

export interface SourceRef {
  label: string;
}

export interface ChatMessage {
  id: string;
  sender: Sender;
  text: string;
  timestamp: string;
  sources?: SourceRef[];
  streaming?: boolean;
}
