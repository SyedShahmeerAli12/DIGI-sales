"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { Paperclip, Mic, Square, Loader2, Send } from "lucide-react";
import { transcribeAudio } from "@/lib/api";

interface ChatInputProps {
  onSend: (text: string, audioUrl?: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const startRecording = async () => {
    setVoiceError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Voice input isn't supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stopStream();
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) return;

        const audioUrl = URL.createObjectURL(blob);

        setIsTranscribing(true);
        try {
          const text = await transcribeAudio(blob);
          const trimmed = text.trim();
          if (trimmed) {
            onSend(trimmed, audioUrl);
          } else {
            setVoiceError("Couldn't hear anything, please try again.");
          }
        } catch {
          setVoiceError("Voice transcription failed. Please try again.");
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setVoiceError("Microphone access was denied.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const handleMicClick = () => {
    if (disabled || isTranscribing) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="sticky bottom-0 z-20 border-t border-border bg-white px-3 py-3 sm:px-5">
      {voiceError && (
        <div className="mx-auto mb-2 w-full max-w-full text-center text-[11px] text-brand-red lg:max-w-4xl xl:max-w-5xl">
          {voiceError}
        </div>
      )}
      <div className="flex w-full max-w-full items-center gap-1 rounded-input border border-border bg-white px-2 py-1.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:max-w-4xl xl:max-w-5xl">
        <button
          type="button"
          aria-label="Attach file"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-bg-page hover:text-text-primary"
        >
          <Paperclip className="h-4 w-4" />
        </button>

        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isRecording
              ? "Listening..."
              : isTranscribing
              ? "Transcribing..."
              : "Ask anything..."
          }
          disabled={isRecording || isTranscribing}
          className="h-10 min-w-0 flex-1 bg-transparent text-sm text-text-primary placeholder-text-placeholder outline-none disabled:cursor-not-allowed"
        />

        <button
          type="button"
          onClick={handleMicClick}
          disabled={disabled || isTranscribing}
          aria-label={isRecording ? "Stop recording" : "Voice input"}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 sm:flex ${
            isRecording
              ? "animate-pulse bg-brand-red text-white"
              : "text-text-secondary hover:bg-bg-page hover:text-text-primary"
          }`}
        >
          {isTranscribing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isRecording ? (
            <Square className="h-3.5 w-3.5" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-red text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
