export type Sender = "user" | "assistant";

export interface SourceRef {
  label: string;
  // exactly one of these is set: page for the FAQ PDF, query for a SQL answer
  page?: number;
  query?: string;
}

export interface ChatMessage {
  id: string;
  sender: Sender;
  text: string;
  timestamp: string;
  sources?: SourceRef[];
  streaming?: boolean;
  isVoice?: boolean;
  audioUrl?: string;
}
