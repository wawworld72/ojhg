"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/services/api";

type Course = { id: string; name: string; role: string };
type ProblemSet = { id: string; name: string; course_id: string; problems: { id: string; title: string }[] };

export default function TeacherProblemSetsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [problemSets, setProblemSets] = useState<ProblemSet[]>([]);
  const [name, setName] = useState("");
  const [courseId, setCourseId] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [coursesRes, setsRes] = await Promise.all([
        apiClient.get("/courses"),
        apiClient.get("/problem-sets"),
      ]);
      const teacherCourses = coursesRes.data.filter((c: Course) => c.role === "teacher");
      setCourses(teacherCourses);
      if (teacherCourses.length > 0 && !courseId) {
        setCourseId(teacherCourses[0].id);
      }
      setProblemSets(setsRes.data);
    } catch {
      setMessage("❌ 데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async () => {
    if (!name.trim() || !courseId) return;
    try {
      await apiClient.post("/problem-sets", { name, course_id: courseId });
      setMessage(`✅ 문제 세트가 생성되었습니다.`);
      setName("");
      await fetchData();
    } catch (err: any) {
      setMessage(`❌ 오류: ${err.response?.data?.error?.message ?? err.message}`);
    }
  };

  const courseMap = Object.fromEntries(courses.map(c => [c.id, c.name]));

  return (
    <div style={{ padding: 24 }}>
      <h1>문제 세트 관리</h1>

      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>새 문제 세트 만들기</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
            placeholder="문제 세트 이름"
            style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, width: 300 }}
          />
          <select
            value={courseId}
            onChange={e => setCourseId(e.target.value)}
            style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4 }}
          >
            {courses.length === 0 && <option value="">강좌 없음</option>}
            {courses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || !courseId}
            style={{ padding: "6px 16px", background: "#2196f3", color: "white", border: "none", borderRadius: 4, cursor: "pointer", opacity: (!name.trim() || !courseId) ? 0.5 : 1 }}
          >
            생성
          </button>
        </div>
        {message && (
          <p style={{ fontSize: 13, color: message.startsWith("✅") ? "green" : "red" }}>
            {message}
          </p>
        )}
      </div>

      <div>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>문제 세트 목록</h2>
        {loading ? (
          <p style={{ color: "#999", fontSize: 14 }}>불러오는 중...</p>
        ) : problemSets.length === 0 ? (
          <p style={{ color: "#999", fontSize: 14 }}>생성된 문제 세트가 없습니다.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #eee", textAlign: "left" }}>
                <th style={{ padding: "8px 12px" }}>이름</th>
                <th style={{ padding: "8px 12px" }}>강좌</th>
                <th style={{ padding: "8px 12px" }}>문제 수</th>
              </tr>
            </thead>
            <tbody>
              {problemSets.map(ps => (
                <tr key={ps.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "8px 12px" }}>{ps.name}</td>
                  <td style={{ padding: "8px 12px" }}>{courseMap[ps.course_id] ?? ps.course_id}</td>
                  <td style={{ padding: "8px 12px" }}>{ps.problems?.length ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
