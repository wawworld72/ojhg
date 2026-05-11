"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/services/api";

type Course = { id: string; name: string; role: string };
type Assignment = { id: string; title: string; due_at?: string };

type SimilarityPair = {
  id: string;
  problem_id: string;
  problem_title: string;
  student_a_id: string;
  student_a_name: string;
  student_b_id: string;
  student_b_name: string;
  similarity_score: number;
  threshold_used: number;
  analyzed_at: string;
};

type DiffData = {
  report_id: string;
  similarity_score: number;
  student_a_name: string;
  code_a: string;
  language_a: string;
  student_b_name: string;
  code_b: string;
  language_b: string;
};

export default function SimilarityPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState("");
  const [threshold, setThreshold] = useState(80);
  const [pairs, setPairs] = useState<SimilarityPair[]>([]);
  const [message, setMessage] = useState("");
  const [diffModal, setDiffModal] = useState<DiffData | null>(null);

  useEffect(() => {
    apiClient.get("/courses").then(res => {
      const teacherCourses = res.data.filter((c: Course) => c.role === "teacher");
      setCourses(teacherCourses);
      if (teacherCourses.length > 0) setSelectedCourse(teacherCourses[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedCourse) return;
    apiClient.get(`/courses/${selectedCourse}/assignments`).then(res => {
      setAssignments(res.data);
      if (res.data.length > 0) setSelectedAssignment(res.data[0].id);
    });
  }, [selectedCourse]);

  useEffect(() => {
    if (!selectedAssignment) return;
    apiClient
      .get(`/assignments/${selectedAssignment}/similarity-reports`)
      .then(res => setPairs(res.data))
      .catch(() => setPairs([]));
  }, [selectedAssignment]);

  const handleAnalyze = async () => {
    setMessage("분석 중...");
    try {
      await apiClient.post(`/assignments/${selectedAssignment}/similarity-analysis`, { threshold });
      setMessage("분석이 시작되었습니다. 잠시 후 새로고침하세요.");
    } catch (err: any) {
      setMessage(`오류: ${err.response?.data?.detail ?? "알 수 없는 오류"}`);
    }
  };

  const handleViewDiff = async (reportId: string) => {
    try {
      const res = await apiClient.get(`/similarity-reports/${reportId}/diff`);
      setDiffModal(res.data);
    } catch {
      alert("코드를 불러오지 못했습니다.");
    }
  };

  const grouped = pairs.reduce<Record<string, SimilarityPair[]>>((acc, p) => {
    const key = p.problem_title;
    if (!acc[key]) acc[key] = [];
    acc[key].push(p);
    return acc;
  }, {});

  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>유사도 분석</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <select
          value={selectedCourse}
          onChange={e => setSelectedCourse(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4 }}
        >
          {courses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select
          value={selectedAssignment}
          onChange={e => setSelectedAssignment(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4 }}
        >
          {assignments.map(a => <option key={a.id} value={a.id}>{a.title}</option>)}
        </select>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 13 }}>임계값(%)</label>
          <input
            type="number"
            value={threshold}
            min={50}
            max={100}
            onChange={e => setThreshold(Number(e.target.value))}
            style={{ width: 70, padding: "6px 8px", border: "1px solid #ddd", borderRadius: 4 }}
          />
        </div>
        <button
          onClick={handleAnalyze}
          style={{ padding: "6px 16px", background: "#2196f3", color: "white", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13 }}
        >
          분석 실행
        </button>
      </div>

      {message && <p style={{ fontSize: 13, color: message.startsWith("오류") ? "red" : "blue", marginBottom: 12 }}>{message}</p>}

      {Object.keys(grouped).length === 0 ? (
        <p style={{ fontSize: 13, color: "#999" }}>플래그된 유사한 제출이 없습니다.</p>
      ) : (
        Object.entries(grouped).map(([problemTitle, problemPairs]) => (
          <div key={problemTitle} style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: 15, marginBottom: 8, borderBottom: "1px solid #eee", paddingBottom: 4 }}>
              {problemTitle}
            </h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ border: "1px solid #ddd", padding: "6px 10px", textAlign: "left" }}>학생 A</th>
                  <th style={{ border: "1px solid #ddd", padding: "6px 10px", textAlign: "left" }}>학생 B</th>
                  <th style={{ border: "1px solid #ddd", padding: "6px 10px" }}>유사도</th>
                  <th style={{ border: "1px solid #ddd", padding: "6px 10px" }}>분석 시간</th>
                  <th style={{ border: "1px solid #ddd", padding: "6px 10px" }}>코드 비교</th>
                </tr>
              </thead>
              <tbody>
                {problemPairs.map(p => (
                  <tr key={p.id}>
                    <td style={{ border: "1px solid #ddd", padding: "6px 10px" }}>{p.student_a_name}</td>
                    <td style={{ border: "1px solid #ddd", padding: "6px 10px" }}>{p.student_b_name}</td>
                    <td style={{ border: "1px solid #ddd", padding: "6px 10px", textAlign: "center" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 4,
                        background: p.similarity_score >= 90 ? "#f44336" : p.similarity_score >= 80 ? "#ff9800" : "#4caf50",
                        color: "white", fontWeight: 600,
                      }}>
                        {p.similarity_score.toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "6px 10px" }}>
                      {new Date(p.analyzed_at).toLocaleString("ko-KR")}
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "6px 10px", textAlign: "center" }}>
                      <button
                        onClick={() => handleViewDiff(p.id)}
                        style={{ fontSize: 12, cursor: "pointer", color: "#2196f3", background: "none", border: "none", textDecoration: "underline" }}
                      >
                        비교 보기
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}

      {diffModal && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
          }}
          onClick={() => setDiffModal(null)}
        >
          <div
            style={{ background: "white", borderRadius: 8, padding: 24, maxWidth: "90vw", width: 900, maxHeight: "85vh", overflow: "auto" }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, margin: 0 }}>
                코드 비교 — 유사도: {diffModal.similarity_score.toFixed(1)}%
              </h3>
              <button onClick={() => setDiffModal(null)} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{diffModal.student_a_name} ({diffModal.language_a})</div>
                <pre style={{ background: "#1e1e1e", color: "#d4d4d4", padding: 12, borderRadius: 4, fontSize: 11, overflow: "auto", margin: 0, maxHeight: 500 }}>
                  {diffModal.code_a}
                </pre>
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{diffModal.student_b_name} ({diffModal.language_b})</div>
                <pre style={{ background: "#1e1e1e", color: "#d4d4d4", padding: 12, borderRadius: 4, fontSize: 11, overflow: "auto", margin: 0, maxHeight: 500 }}>
                  {diffModal.code_b}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
