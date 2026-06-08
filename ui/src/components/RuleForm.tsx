import { useRef, useState } from "react";
import { BEARER_TOKEN } from "../config";
import { InterpretResponse } from "../App";

type MicState = "idle" | "recording" | "processing";

interface RuleFormProps {
  onResult: (response: InterpretResponse) => void;
  onError: (message: string) => void;
  onLoading: (loading: boolean) => void;
  isLoading: boolean;
}

/* Maximum recording duration in milliseconds before auto-stop */
const MAX_RECORDING_MS = 30_000;

function RuleForm({ onResult, onError, onLoading, isLoading }: RuleFormProps) {
  const [text, setText] = useState("");
  const [micState, setMicState] = useState<MicState>("idle");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const autoStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---- Parse error response from FastAPI ---- */
  async function parseErrorMessage(res: Response): Promise<string> {
    try {
      const body = await res.json();
      // FastAPI wraps errors as { detail: "..." } or { detail: [...] }
      if (body?.detail) {
        if (typeof body.detail === "string") return body.detail;
        if (Array.isArray(body.detail)) {
          return body.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(", ");
        }
        return JSON.stringify(body.detail);
      }
      // Spring-style errors { errors: [{ detail: "..." }] }
      if (Array.isArray(body?.errors) && body.errors[0]?.detail) {
        return body.errors[0].detail;
      }
      return JSON.stringify(body);
    } catch {
      return await res.text().catch(() => `HTTP ${res.status} ${res.statusText}`);
    }
  }

  /* ---- Text submit ---- */
  async function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    onLoading(true);
    try {
      const res = await fetch("/v1/nac-rules/interpret", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${BEARER_TOKEN}`,
        },
        body: JSON.stringify({ text: trimmed, dry_run: false }),
      });
      if (!res.ok) {
        const msg = await parseErrorMessage(res);
        throw new Error(msg);
      }
      const data: InterpretResponse = await res.json();
      onResult(data);
    } catch (err) {
      if (err instanceof TypeError && err.message.includes("fetch")) {
        onError("Cannot reach the RulesPilot server. Make sure it is running on port 8082.");
      } else {
        onError(err instanceof Error ? err.message : "An unexpected error occurred.");
      }
    }
  }

  /* ---- Voice: start recording ---- */
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        /* Stop all tracks to release the mic */
        stream.getTracks().forEach((t) => t.stop());

        if (autoStopTimerRef.current) {
          clearTimeout(autoStopTimerRef.current);
          autoStopTimerRef.current = null;
        }

        setMicState("processing");
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        await sendVoice(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setMicState("recording");

      /* Auto-stop after 30 seconds */
      autoStopTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
        }
      }, MAX_RECORDING_MS);
    } catch (err) {
      onError(
        err instanceof Error
          ? `Microphone access denied: ${err.message}`
          : "Could not access microphone."
      );
      setMicState("idle");
    }
  }

  /* ---- Voice: stop recording ---- */
  function stopRecording() {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }

  /* ---- Voice: send to API ---- */
  async function sendVoice(blob: Blob) {
    try {
      const formData = new FormData();
      formData.append("file", blob, "recording.webm");

      const res = await fetch("/v1/nac-rules/interpret/voice?dry_run=false", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${BEARER_TOKEN}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const msg = await parseErrorMessage(res);
        throw new Error(msg);
      }
      const data: InterpretResponse = await res.json();
      onResult(data);
    } catch (err) {
      if (err instanceof TypeError && err.message.includes("fetch")) {
        onError("Cannot reach the RulesPilot server. Make sure it is running on port 8082.");
      } else {
        onError(err instanceof Error ? err.message : "An unexpected error occurred.");
      }
    } finally {
      setMicState("idle");
    }
  }

  /* ---- Mic button click handler ---- */
  function handleMicClick() {
    if (micState === "idle") {
      startRecording();
    } else if (micState === "recording") {
      stopRecording();
    }
    /* 'processing' state: button is disabled, no action */
  }

  const isRecording = micState === "recording";
  const isProcessing = micState === "processing";
  const isBusy = isLoading || isRecording || isProcessing;

  return (
    <div className="card">
      <h1 className="rule-form__title">Describe your NAC rule</h1>
      <p className="rule-form__subtitle">
        Type in natural language or use your microphone
      </p>

      <textarea
        className="rule-form__textarea"
        rows={4}
        placeholder='e.g. "Block all Windows devices running Chrome that are not managed by our MDM from accessing the corporate network"'
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isBusy}
      />

      <div className="rule-form__actions">
        {/* Mic button */}
        <button
          type="button"
          className={[
            "mic-button",
            isRecording ? "mic-button--recording" : "",
            isProcessing ? "mic-button--processing" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={handleMicClick}
          disabled={isLoading || isProcessing}
          aria-label={isRecording ? "Stop recording" : "Start voice recording"}
        >
          {isRecording ? (
            <>
              <span className="mic-pulse-dot" aria-hidden="true" />
              <StopIcon />
              Recording…
            </>
          ) : isProcessing ? (
            <>
              <span className="spinner spinner--purple" aria-hidden="true" />
              Processing…
            </>
          ) : (
            <>
              <MicIcon />
              Voice input
            </>
          )}
        </button>

        {/* Submit button */}
        <button
          type="button"
          className="submit-button"
          onClick={handleSubmit}
          disabled={isBusy || !text.trim()}
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Analyzing…
            </>
          ) : (
            <>
              <SendIcon />
              Create Rule
            </>
          )}
        </button>
      </div>

      {isLoading && (
        <div className="loading-state" role="status" aria-live="polite">
          <span className="spinner spinner--purple" />
          Analyzing your request…
        </div>
      )}
    </div>
  );
}

/* ---- Inline SVG icons ---- */

function MicIcon() {
  return (
    <svg
      className="icon"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      className="icon"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      className="icon"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

export default RuleForm;
