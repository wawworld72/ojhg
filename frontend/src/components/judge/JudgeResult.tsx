"use client";

import { useEffect, useState } from "react";
import { subscribeSubmissionStream, apiClient } from "@/services/api";

type TcResult = {
  order: number;
  verdict: string;
  time_ms: number | null;
  memory_mb: number | null;
  input_preview: string | null;
  expected_output_preview: string | null;
};

type SubmissionResult = {
  id: string;
  verdict: string | null;
  score: number | null;
  attempt_number: number;
  is_late: boolean;
  test_case_results: TcResult[] | null;
  judged_at: string | null;
};

const VERDICT_COLOR: Record<string, string> = {
  ACCEPTED: "green",
  WRONG_ANSWER: "red",
  TIME_LIMIT_EXCEEDED: "orange",
  MEMORY_LIMIT_EXCEEDED: "orange",
  RUNTIME_ERROR: "red",
  COMPILATION_ERROR: "red",
  PENDING: "#666",
};

export default function JudgeResult({ submissionId }: { submissionId: string }) {
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [pending, setPending] = useState(true);

  useEffect(() => {
    const es = subscribeSubmissionStream(
      submissionId,
      async () => {
        // Fetch full result after verdict event
        const res = await apiClient.get(`/submissions/${submissionId}`);
        setResult(res.data);
        setPending(false);
      },
      () => setPending(false),
    );
    return () => es.close();
  }, [submissionId]);

  if (pending && !result) {
    return (
      <div style={{ marginTop: 16, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
        <span style={{ color: "#666" }}>⏳ 채점 중...</span>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div style={{ marginTop: 16, padding: 12, background: "#f9f9f9", borderRadius: 4, border: "1px solid #eee" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 8 }}>
        <span
          style={{
            fontWeight: 700,
            fontSize: 16,
            color: VERDICT_COLOR[result.verdict ?? "PENDING"] ?? "#333",
          }}
        >
          {result.verdict}
        </span>
        {result.score !== null && (
          <span style={{ fontSize: 14 }}>
            획득 점수: <strong>{result.score.toFixed(1)}</strong>
          </span>
        )}
        <span style={{ fontSize: 12, color: "#666" }}>시도 #{result.attempt_number}</span>
        {result.is_late && <span style={{ fontSize: 12, color: "orange" }}>지각 제출</span>}
      </div>

      {result.test_case_results && result.test_case_results.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "#f0f0f0" }}>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" }}>#</th>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" }}>결과</th>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" }}>시간(ms)</th>
              <th style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" }}>메모리(MB)</th>
            </tr>
          </thead>
          <tbody>
            {result.test_case_results.map(tc => (
              <tr key={tc.order}>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>{tc.order}</td>
                <td
                  style={{
                    border: "1px solid #ddd",
                    padding: "4px 8px",
                    color: VERDICT_COLOR[tc.verdict] ?? "#333",
                    fontWeight: 600,
                  }}
                >
                  {tc.verdict}
                </td>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>{tc.time_ms ?? "-"}</td>
                <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                  {tc.memory_mb != null ? tc.memory_mb.toFixed(1) : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
