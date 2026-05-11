"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/services/api";
import CodeEditor from "@/components/editor/CodeEditor";
import JudgeResult from "@/components/judge/JudgeResult";

type ScoreTier = { min_attempts: number; max_attempts: number | null; score_ratio: number };
type MyProgress = {
  attempt_count: number;
  final_score: number | null;
  accepted: boolean;
  current_tier: { score_ratio: number } | null;
  next_tier: { min_attempts: number; score_ratio: number } | null;
};
type Problem = {
  id: string;
  display_order: number;
  title: string;
  description_md: string;
  time_limit_sec: number;
  memory_limit_mb: number;
  max_points: number;
  allowed_languages: string[];
  score_tiers: ScoreTier[];
  my_progress: MyProgress;
  public_test_cases: { order: number; input_preview: string; expected_output_preview: string }[];
};
type ProblemSetData = {
  problem_set: { id: string; name: string; due_at: string | null; allow_late_submission: boolean };
  problems: Problem[];
  my_total_score: number;
  is_late_access: boolean;
};

export default function AssignmentPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ProblemSetData | null>(null);
  const [selectedProblem, setSelectedProblem] = useState<Problem | null>(null);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get(`/assignments/${id}/problem-set`)
      .then(res => {
        setData(res.data);
        if (res.data.problems.length > 0) setSelectedProblem(res.data.problems[0]);
      })
      .catch(err => setError(err.response?.data?.error?.message ?? "Failed to load assignment"));
  }, [id]);

  const handleSubmit = async (code: string, language: string) => {
    if (!selectedProblem) return;
    try {
      const res = await apiClient.post(`/problems/${selectedProblem.id}/submissions`, { code, language });
      setSubmissionId(res.data.submission_id);
    } catch (err: any) {
      setError(err.response?.data?.error?.message ?? "Submission failed");
    }
  };

  if (error) return <div style={{ padding: 16, color: "red" }}>Error: {error}</div>;
  if (!data) return <div style={{ padding: 16 }}>Loading...</div>;

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Sidebar: problem list */}
      <aside style={{ width: 240, borderRight: "1px solid #eee", padding: 16, overflowY: "auto" }}>
        <h2 style={{ fontSize: 14, marginBottom: 8 }}>{data.problem_set.name}</h2>
        <p style={{ fontSize: 12, color: "#666" }}>총 점수: {data.my_total_score.toFixed(1)}</p>
        {data.is_late_access && <p style={{ fontSize: 12, color: "orange" }}>지각 제출</p>}
        {data.problems.map(p => (
          <div
            key={p.id}
            onClick={() => { setSelectedProblem(p); setSubmissionId(null); }}
            style={{
              padding: "8px 12px",
              marginBottom: 4,
              cursor: "pointer",
              borderRadius: 4,
              background: selectedProblem?.id === p.id ? "#e8f4fd" : "transparent",
              border: selectedProblem?.id === p.id ? "1px solid #2196f3" : "1px solid transparent",
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600 }}>
              {p.display_order}. {p.title}
            </div>
            <div style={{ fontSize: 11, color: p.my_progress.accepted ? "green" : "#666" }}>
              {p.my_progress.accepted
                ? `✓ ${p.my_progress.final_score?.toFixed(1)} / ${p.max_points}`
                : `시도: ${p.my_progress.attempt_count} | ${p.max_points}점`}
            </div>
          </div>
        ))}
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {selectedProblem && (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
              <h1 style={{ fontSize: 18 }}>
                {selectedProblem.display_order}. {selectedProblem.title}
              </h1>
              <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
                시간: {selectedProblem.time_limit_sec}초 | 메모리: {selectedProblem.memory_limit_mb}MB | 배점: {selectedProblem.max_points}점
              </div>
              <pre style={{ background: "#f5f5f5", padding: 12, borderRadius: 4, whiteSpace: "pre-wrap" }}>
                {selectedProblem.description_md}
              </pre>
              {selectedProblem.public_test_cases.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <h3 style={{ fontSize: 14 }}>예제</h3>
                  {selectedProblem.public_test_cases.map(tc => (
                    <div key={tc.order} style={{ display: "flex", gap: 12, marginBottom: 8 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 600 }}>입력 {tc.order}</div>
                        <pre style={{ background: "#f5f5f5", padding: 8, borderRadius: 4, fontSize: 12 }}>{tc.input_preview}</pre>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 600 }}>출력 {tc.order}</div>
                        <pre style={{ background: "#f5f5f5", padding: 8, borderRadius: 4, fontSize: 12 }}>{tc.expected_output_preview}</pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {/* Score tiers */}
              <div style={{ marginTop: 12 }}>
                <h3 style={{ fontSize: 14 }}>점수 구간</h3>
                <table style={{ fontSize: 12, borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>시도 범위</th>
                      <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>점수 비율</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedProblem.score_tiers.map((tier, i) => (
                      <tr key={i}>
                        <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                          {tier.min_attempts}~{tier.max_attempts ?? "∞"}회
                        </td>
                        <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>{tier.score_ratio}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {submissionId && (
                <JudgeResult submissionId={submissionId} />
              )}
            </div>
            <div style={{ borderTop: "1px solid #eee" }}>
              <CodeEditor
                allowedLanguages={selectedProblem.allowed_languages}
                attemptCount={selectedProblem.my_progress.attempt_count}
                nextTier={selectedProblem.my_progress.next_tier}
                accepted={selectedProblem.my_progress.accepted}
                onSubmit={handleSubmit}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
