"use client";

import { useState } from "react";
import { apiClient } from "@/services/api";

type ScoreTier = { min_attempts: number; max_attempts: number | null; score_ratio: number };

type Props = {
  problemSetId: string;
  onCreated?: () => void;
};

const LANGUAGES = ["python3", "java17", "cpp17", "c17"];

export default function ProblemEditor({ problemSetId, onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [descriptionMd, setDescriptionMd] = useState("");
  const [timeLimitSec, setTimeLimitSec] = useState(1.0);
  const [memoryLimitMb, setMemoryLimitMb] = useState(256);
  const [maxPoints, setMaxPoints] = useState(100);
  const [allowedLanguages, setAllowedLanguages] = useState<string[]>(["python3"]);
  const [tiers, setTiers] = useState<ScoreTier[]>([
    { min_attempts: 1, max_attempts: 5, score_ratio: 100 },
    { min_attempts: 6, max_attempts: 10, score_ratio: 80 },
    { min_attempts: 11, max_attempts: null, score_ratio: 60 },
  ]);
  const [message, setMessage] = useState("");

  const toggleLanguage = (lang: string) => {
    setAllowedLanguages(prev =>
      prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]
    );
  };

  const handleCreate = async () => {
    try {
      await apiClient.post(`/problem-sets/${problemSetId}/problems`, {
        title,
        description_md: descriptionMd,
        time_limit_sec: timeLimitSec,
        memory_limit_mb: memoryLimitMb,
        max_points: maxPoints,
        allowed_languages: allowedLanguages,
        score_tiers: tiers,
      });
      setMessage("✅ 문제가 생성되었습니다.");
      onCreated?.();
    } catch (err: any) {
      setMessage(`❌ ${err.response?.data?.error?.message ?? "오류 발생"}`);
    }
  };

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 20, maxWidth: 700 }}>
      <h2 style={{ fontSize: 16, marginBottom: 16 }}>문제 추가</h2>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>문제 제목</label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          style={{ width: "100%", padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4 }}
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>문제 설명 (Markdown)</label>
        <textarea
          value={descriptionMd}
          onChange={e => setDescriptionMd(e.target.value)}
          rows={6}
          style={{ width: "100%", padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, fontFamily: "monospace", fontSize: 13 }}
        />
      </div>
      <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
        <div>
          <label style={{ display: "block", fontSize: 13 }}>시간 제한(초)</label>
          <input type="number" min={0.5} max={10} step={0.5} value={timeLimitSec} onChange={e => setTimeLimitSec(Number(e.target.value))} style={{ width: 80, padding: "4px 8px" }} />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 13 }}>메모리 제한(MB)</label>
          <input type="number" min={32} max={512} value={memoryLimitMb} onChange={e => setMemoryLimitMb(Number(e.target.value))} style={{ width: 80, padding: "4px 8px" }} />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 13 }}>배점</label>
          <input type="number" min={1} value={maxPoints} onChange={e => setMaxPoints(Number(e.target.value))} style={{ width: 80, padding: "4px 8px" }} />
        </div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>허용 언어</label>
        <div style={{ display: "flex", gap: 12 }}>
          {LANGUAGES.map(l => (
            <label key={l} style={{ fontSize: 13, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={allowedLanguages.includes(l)}
                onChange={() => toggleLanguage(l)}
                style={{ marginRight: 4 }}
              />
              {l}
            </label>
          ))}
        </div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>점수 구간</label>
        <table style={{ fontSize: 12, borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr style={{ background: "#f0f0f0" }}>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>최소 시도</th>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>최대 시도</th>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>점수 비율(%)</th>
            </tr>
          </thead>
          <tbody>
            {tiers.map((tier, i) => (
              <tr key={i}>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                  <input type="number" value={tier.min_attempts} onChange={e => {
                    const t = [...tiers]; t[i] = { ...t[i], min_attempts: Number(e.target.value) }; setTiers(t);
                  }} style={{ width: 60 }} />
                </td>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                  <input type="number" value={tier.max_attempts ?? ""} placeholder="∞" onChange={e => {
                    const t = [...tiers]; t[i] = { ...t[i], max_attempts: e.target.value ? Number(e.target.value) : null }; setTiers(t);
                  }} style={{ width: 60 }} />
                </td>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                  <input type="number" value={tier.score_ratio} onChange={e => {
                    const t = [...tiers]; t[i] = { ...t[i], score_ratio: Number(e.target.value) }; setTiers(t);
                  }} style={{ width: 60 }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {message && <p style={{ fontSize: 13, color: message.startsWith("✅") ? "green" : "red" }}>{message}</p>}
      <button
        onClick={handleCreate}
        style={{ padding: "8px 24px", background: "#2196f3", color: "white", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}
      >
        문제 저장
      </button>
    </div>
  );
}
