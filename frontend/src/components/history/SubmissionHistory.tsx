"use client";

import { useState } from "react";

type SubmissionItem = {
  submission_id: string;
  attempt_number: number;
  submitted_at: string;
  verdict: string | null;
  score: number | null;
  language: string;
  is_late: boolean;
  code?: string | null;
};

type ProblemGroup = {
  problem_id: string;
  problem_title: string;
  submissions: SubmissionItem[];
};

type Props = {
  problems: ProblemGroup[];
};

const VERDICT_COLORS: Record<string, string> = {
  ACCEPTED: "#4caf50",
  WRONG_ANSWER: "#f44336",
  TIME_LIMIT_EXCEEDED: "#ff9800",
  MEMORY_LIMIT_EXCEEDED: "#ff9800",
  RUNTIME_ERROR: "#e91e63",
  COMPILE_ERROR: "#9c27b0",
  PENDING: "#9e9e9e",
};

export default function SubmissionHistory({ problems }: Props) {
  const [codeModal, setCodeModal] = useState<{ code: string; language: string } | null>(null);

  return (
    <div>
      {problems.map(group => (
        <div key={group.problem_id} style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 15, marginBottom: 8, borderBottom: "1px solid #eee", paddingBottom: 4 }}>
            {group.problem_title}
          </h3>
          {group.submissions.length === 0 ? (
            <p style={{ fontSize: 13, color: "#999" }}>제출 없음</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>시도</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>제출 시간</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>언어</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>결과</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>점수</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>코드</th>
                </tr>
              </thead>
              <tbody>
                {group.submissions.map(s => (
                  <tr key={s.submission_id}>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>
                      #{s.attempt_number}
                      {s.is_late && (
                        <span style={{ marginLeft: 4, fontSize: 10, color: "#ff9800", fontWeight: 600 }}>지각</span>
                      )}
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                      {new Date(s.submitted_at).toLocaleString("ko-KR")}
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>{s.language}</td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        background: VERDICT_COLORS[s.verdict ?? "PENDING"] ?? "#9e9e9e",
                        color: "white",
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {s.verdict ?? "PENDING"}
                      </span>
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>
                      {s.score !== null ? s.score.toFixed(1) : "-"}
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>
                      {s.code && (
                        <button
                          onClick={() => setCodeModal({ code: s.code!, language: s.language })}
                          style={{ fontSize: 12, cursor: "pointer", color: "#2196f3", background: "none", border: "none", textDecoration: "underline" }}
                        >
                          보기
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}

      {codeModal && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
          }}
          onClick={() => setCodeModal(null)}
        >
          <div
            style={{ background: "white", borderRadius: 8, padding: 24, maxWidth: 720, width: "90%", maxHeight: "80vh", overflow: "auto" }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{codeModal.language}</span>
              <button onClick={() => setCodeModal(null)} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer" }}>✕</button>
            </div>
            <pre style={{ background: "#1e1e1e", color: "#d4d4d4", padding: 16, borderRadius: 4, fontSize: 12, overflow: "auto", margin: 0 }}>
              {codeModal.code}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
