"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/services/api";

type Problem = {
  id: string;
  title: string;
  display_order: number;
  max_points: number;
};

type ProblemSet = {
  id: string;
  name: string;
  course_id: string;
  problems: Problem[];
};

type ScoreTier = {
  min_attempts: number;
  max_attempts: number | null;
  score_ratio: number;
};

type NewProblem = {
  title: string;
  description_md: string;
  input_description_md: string;
  output_description_md: string;
  time_limit_sec: number;
  memory_limit_mb: number;
  max_points: number;
  allowed_languages: string[];
  score_tiers: ScoreTier[];
};

export default function ProblemSetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const setId = params.setId as string;

  const [problemSet, setProblemSet] = useState<ProblemSet | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const [newProblem, setNewProblem] = useState<NewProblem>({
    title: "",
    description_md: "",
    input_description_md: "",
    output_description_md: "",
    time_limit_sec: 1.0,
    memory_limit_mb: 256,
    max_points: 100,
    allowed_languages: ["python3", "cpp17"],
    score_tiers: [
      { min_attempts: 1, max_attempts: 1, score_ratio: 1.0 },
      { min_attempts: 2, max_attempts: null, score_ratio: 0.8 },
    ],
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await apiClient.get(`/problem-sets/${setId}`);
        setProblemSet(res.data);
      } catch (err: any) {
        setMessage(`❌ 로드 실패: ${err.response?.data?.detail || err.message}`);
      }
      setLoading(false);
    };
    loadData();
  }, [setId]);

  const handleCreateProblem = async () => {
    if (!newProblem.title.trim()) {
      setMessage("❌ 문제 제목을 입력하세요");
      return;
    }
    if (!newProblem.description_md.trim()) {
      setMessage("❌ 문제 설명을 입력하세요");
      return;
    }

    try {
      const res = await apiClient.post(`/problem-sets/${setId}/problems`, newProblem);
      setMessage(`✅ 문제가 생성되었습니다: ${res.data.title}`);

      // Reload problem set
      const psRes = await apiClient.get(`/problem-sets/${setId}`);
      setProblemSet(psRes.data);

      // Reset form
      setNewProblem({
        title: "",
        description_md: "",
        input_description_md: "",
        output_description_md: "",
        time_limit_sec: 1.0,
        memory_limit_mb: 256,
        max_points: 100,
        allowed_languages: ["python3", "cpp17"],
        score_tiers: [
          { min_attempts: 1, max_attempts: 1, score_ratio: 1.0 },
          { min_attempts: 2, max_attempts: null, score_ratio: 0.8 },
        ],
      });
      setShowCreateForm(false);
    } catch (err: any) {
      const errors = err.response?.data?.detail;
      if (typeof errors === "string") {
        setMessage(`❌ ${errors}`);
      } else {
        setMessage(`❌ 문제 생성 실패`);
      }
    }
  };

  if (loading) return <div style={{ padding: 24 }}>로드 중...</div>;
  if (!problemSet) return <div style={{ padding: 24 }}>문제 세트를 찾을 수 없습니다.</div>;

  return (
    <div style={{ padding: 24 }}>
      <button
        onClick={() => router.back()}
        style={{
          padding: "6px 12px",
          background: "#f0f0f0",
          border: "1px solid #ddd",
          borderRadius: 4,
          cursor: "pointer",
          marginBottom: 16,
        }}
      >
        ← 돌아가기
      </button>

      <h1>{problemSet.name}</h1>

      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>문제 목록</h2>
        {problemSet.problems.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ddd" }}>
                <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>순서</th>
                <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>제목</th>
                <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>만점</th>
                <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>작업</th>
              </tr>
            </thead>
            <tbody>
              {problemSet.problems.map((problem) => (
                <tr key={problem.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: 8 }}>{problem.display_order}</td>
                  <td style={{ padding: 8 }}>{problem.title}</td>
                  <td style={{ padding: 8 }}>{problem.max_points}</td>
                  <td style={{ padding: 8 }}>
                    <a
                      href={`/teacher/problems/${problem.id}`}
                      style={{ color: "#2196f3", textDecoration: "none", cursor: "pointer" }}
                    >
                      편집
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ fontSize: 13, color: "#999" }}>문제가 없습니다.</p>
        )}
      </div>

      <div style={{ marginBottom: 32 }}>
        {!showCreateForm ? (
          <button
            onClick={() => setShowCreateForm(true)}
            style={{
              padding: "8px 16px",
              background: "#4caf50",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            + 새 문제 추가
          </button>
        ) : (
          <div
            style={{
              border: "1px solid #ddd",
              borderRadius: 4,
              padding: 16,
              background: "#fafafa",
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: 12 }}>새 문제 추가</h3>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                문제 제목 *
              </label>
              <input
                type="text"
                value={newProblem.title}
                onChange={(e) =>
                  setNewProblem({ ...newProblem, title: e.target.value })
                }
                placeholder="문제 제목을 입력하세요"
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 14,
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                문제 설명 (마크다운) *
              </label>
              <textarea
                value={newProblem.description_md}
                onChange={(e) =>
                  setNewProblem({ ...newProblem, description_md: e.target.value })
                }
                placeholder="문제 설명을 입력하세요"
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 14,
                  minHeight: 100,
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                입력 설명 (마크다운)
              </label>
              <textarea
                value={newProblem.input_description_md}
                onChange={(e) =>
                  setNewProblem({ ...newProblem, input_description_md: e.target.value })
                }
                placeholder="입력 형식 설명"
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 14,
                  minHeight: 80,
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                출력 설명 (마크다운)
              </label>
              <textarea
                value={newProblem.output_description_md}
                onChange={(e) =>
                  setNewProblem({ ...newProblem, output_description_md: e.target.value })
                }
                placeholder="출력 형식 설명"
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 14,
                  minHeight: 80,
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                  시간 제한 (초)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="10"
                  value={newProblem.time_limit_sec}
                  onChange={(e) =>
                    setNewProblem({
                      ...newProblem,
                      time_limit_sec: parseFloat(e.target.value),
                    })
                  }
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    border: "1px solid #ddd",
                    borderRadius: 4,
                    fontSize: 14,
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                  메모리 제한 (MB)
                </label>
                <input
                  type="number"
                  min="32"
                  max="512"
                  value={newProblem.memory_limit_mb}
                  onChange={(e) =>
                    setNewProblem({
                      ...newProblem,
                      memory_limit_mb: parseInt(e.target.value),
                    })
                  }
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    border: "1px solid #ddd",
                    borderRadius: 4,
                    fontSize: 14,
                    boxSizing: "border-box",
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, fontWeight: 500 }}>
                만점
              </label>
              <input
                type="number"
                min="1"
                value={newProblem.max_points}
                onChange={(e) =>
                  setNewProblem({
                    ...newProblem,
                    max_points: parseFloat(e.target.value),
                  })
                }
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  fontSize: 14,
                  boxSizing: "border-box",
                }}
              />
            </div>

            {message && (
              <p
                style={{
                  fontSize: 13,
                  color: message.startsWith("✅") ? "green" : "red",
                  marginBottom: 12,
                }}
              >
                {message}
              </p>
            )}

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleCreateProblem}
                style={{
                  padding: "8px 16px",
                  background: "#2196f3",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                생성
              </button>

              <button
                onClick={() => {
                  setShowCreateForm(false);
                  setMessage("");
                }}
                style={{
                  padding: "8px 16px",
                  background: "#ccc",
                  color: "#333",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                취소
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
