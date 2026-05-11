"use client";

import { useRef, useState } from "react";
import dynamic from "next/dynamic";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type NextTier = { min_attempts: number; score_ratio: number } | null;

type Props = {
  allowedLanguages: string[];
  attemptCount: number;
  nextTier: NextTier;
  accepted: boolean;
  onSubmit: (code: string, language: string) => void;
};

const LANGUAGE_EXTENSIONS: Record<string, string> = {
  python3: ".py",
  java17: ".java",
  cpp17: ".cpp",
  c17: ".c",
};

const MONACO_LANGUAGE_MAP: Record<string, string> = {
  python3: "python",
  java17: "java",
  cpp17: "cpp",
  c17: "c",
};

export default function CodeEditor({ allowedLanguages, attemptCount, nextTier, accepted, onSubmit }: Props) {
  const [language, setLanguage] = useState(allowedLanguages[0] ?? "python3");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!code.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(code, language);
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => setCode(ev.target?.result as string);
    reader.readAsText(file);
  };

  return (
    <div style={{ padding: "8px 16px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <select
          value={language}
          onChange={e => setLanguage(e.target.value)}
          style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #ddd" }}
        >
          {allowedLanguages.map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <button
          onClick={() => fileInputRef.current?.click()}
          style={{ padding: "4px 10px", fontSize: 12, cursor: "pointer" }}
        >
          파일 업로드 ({LANGUAGE_EXTENSIONS[language] ?? ""})
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={LANGUAGE_EXTENSIONS[language]}
          onChange={handleFileUpload}
          style={{ display: "none" }}
        />
        <span style={{ fontSize: 12, color: "#666" }}>
          {accepted ? "✓ 이미 정답" : `시도 횟수: ${attemptCount}`}
          {!accepted && nextTier && (
            <span style={{ color: "#2196f3", marginLeft: 8 }}>
              다음 구간: {nextTier.min_attempts}회~ → {nextTier.score_ratio}%
            </span>
          )}
        </span>
        <button
          onClick={handleSubmit}
          disabled={submitting || accepted}
          style={{
            marginLeft: "auto",
            padding: "6px 20px",
            background: accepted ? "#9e9e9e" : "#2196f3",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: accepted ? "not-allowed" : "pointer",
            fontWeight: 600,
          }}
        >
          {submitting ? "제출 중..." : "제출"}
        </button>
      </div>
      <MonacoEditor
        height="300px"
        language={MONACO_LANGUAGE_MAP[language] ?? "plaintext"}
        value={code}
        onChange={v => setCode(v ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          tabSize: 4,
          automaticLayout: true,
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
