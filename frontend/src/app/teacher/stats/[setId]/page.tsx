"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/services/api";

type ProblemStat = {
  problem_id: string;
  title: string;
  submitted_count: number;
  accepted_count: number;
  avg_attempts: number;
  avg_score: number;
};

type Stats = {
  total_students: number;
  submitted_students: number;
  avg_total_score: number;
  problems: ProblemStat[];
};

export default function StatsPage() {
  const { setId } = useParams<{ setId: string }>();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient
      .get(`/problem-sets/${setId}/stats`)
      .then(res => setStats(res.data))
      .catch(() => setError("통계 데이터를 불러오지 못했습니다."));
  }, [setId]);

  if (error) return <p style={{ color: "red", padding: 24 }}>{error}</p>;
  if (!stats) return <p style={{ padding: 24 }}>로딩 중...</p>;

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>문제 세트 통계</h1>
      <div style={{ display: "flex", gap: 32, marginBottom: 24 }}>
        <div style={{ background: "#f5f5f5", borderRadius: 8, padding: "12px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.total_students}</div>
          <div style={{ fontSize: 12, color: "#666" }}>전체 학생</div>
        </div>
        <div style={{ background: "#f5f5f5", borderRadius: 8, padding: "12px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.submitted_students}</div>
          <div style={{ fontSize: 12, color: "#666" }}>제출한 학생</div>
        </div>
        <div style={{ background: "#f5f5f5", borderRadius: 8, padding: "12px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.avg_total_score.toFixed(1)}</div>
          <div style={{ fontSize: 12, color: "#666" }}>평균 총점</div>
        </div>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "#f0f0f0" }}>
            <th style={{ border: "1px solid #ddd", padding: "8px 12px", textAlign: "left" }}>문제</th>
            <th style={{ border: "1px solid #ddd", padding: "8px 12px" }}>제출 학생 수</th>
            <th style={{ border: "1px solid #ddd", padding: "8px 12px" }}>정답 학생 수</th>
            <th style={{ border: "1px solid #ddd", padding: "8px 12px" }}>평균 시도 횟수</th>
            <th style={{ border: "1px solid #ddd", padding: "8px 12px" }}>평균 점수</th>
          </tr>
        </thead>
        <tbody>
          {stats.problems.map(p => (
            <tr key={p.problem_id}>
              <td style={{ border: "1px solid #ddd", padding: "8px 12px" }}>{p.title}</td>
              <td style={{ border: "1px solid #ddd", padding: "8px 12px", textAlign: "center" }}>{p.submitted_count}</td>
              <td style={{ border: "1px solid #ddd", padding: "8px 12px", textAlign: "center" }}>{p.accepted_count}</td>
              <td style={{ border: "1px solid #ddd", padding: "8px 12px", textAlign: "center" }}>{p.avg_attempts.toFixed(1)}</td>
              <td style={{ border: "1px solid #ddd", padding: "8px 12px", textAlign: "center" }}>{p.avg_score.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
