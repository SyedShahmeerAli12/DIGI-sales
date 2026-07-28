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

export interface DataEntity {
  table: string;
  label: string;
  count: number;
}

export interface DataOverview {
  faq_knowledge_base: {
    label: string;
    total_questions: number;
    personas: { name: string; count: number }[];
  };
  fmcg_database: {
    label: string;
    date_range: { start: string; end: string };
    groups: { name: string; entities: DataEntity[] }[];
  };
}
