"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/services/api";

type Course = { id: string; name: string; role: string };
type ProblemSet = { id: string; name: string; course_id: string; problems: { id: string; title: string }[] };

export default function TeacherProblemSetsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [name, setName] = useState("");
  const [courseId, setCourseId] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiClient.get("/courses").then(res => {
      const teacherCourses = res.data.filter((c: Course) => c.role === "teacher");
      setCourses(teacherCourses);
      if (teacherCourses.length > 0) setCourseId(teacherCourses[0].id);
    });
  }, []);

  const handleCreate = async () => {
    if (!name.trim() || !courseId) return;
    try {
      const res = await apiClient.post("/problem-sets", { name, course_id: courseId });
      setMessage(`✅ 문제 세트 생성: ${res.data.id}`);
      setName("");
    } catch (err: any) {
      setMessage(`❌ 오류: ${err.response?.data?.error?.message}`);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>문제 세트 관리</h1>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16 }}>새 문제 세트 만들기</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="문제 세트 이름"
            style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, width: 300 }}
          />
          <select
            value={courseId}
            onChange={e => setCourseId(e.target.value)}
            style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4 }}
          >
            {courses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button
            onClick={handleCreate}
            style={{ padding: "6px 16px", background: "#2196f3", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
          >
            생성
          </button>
        </div>
        {message && <p style={{ fontSize: 13, color: message.startsWith("✅") ? "green" : "red" }}>{message}</p>}
      </div>
    </div>
  );
}
