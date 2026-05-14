"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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

  useEffect(() => {
    const loadData = async () => {
      try {
        const coursesRes = await apiClient.get("/courses");
        const teacherCourses = coursesRes.data.filter((c: Course) => c.role === "teacher");
        setCourses(teacherCourses);
        if (teacherCourses.length > 0) {
          setCourseId(teacherCourses[0].id);
        }

        // Load problem sets
        const setsRes = await apiClient.get("/problem-sets");
        setProblemSets(setsRes.data);
      } catch (err: any) {
        setMessage(`❌ 로드 실패: ${err.response?.data?.error?.message}`);
      }
      setLoading(false);
    };
    loadData();
  }, []);

  const loadProblemSets = async () => {
    try {
      const res = await apiClient.get("/problem-sets");
      setProblemSets(res.data);
      setMessage("");
    } catch (err: any) {
      setMessage(`❌ 문제 세트 로드 실패`);
    }
  };

  const handleCreate = async () => {
    if (!name.trim() || !courseId) return;
    try {
      const res = await apiClient.post("/problem-sets", { name, course_id: courseId });
      setMessage(`✅ 문제 세트가 생성되었습니다.`);
      setName("");
      // Reload problem sets
      await loadProblemSets();
    } catch (err: any) {
      setMessage(`❌ 오류: ${err.response?.data?.error?.message}`);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>문제 세트 관리</h1>

      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16 }}>강좌 동기화</h2>
        <button
          onClick={loadProblemSets}
          style={{ padding: "6px 16px", background: "#4caf50", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          새로고침
        </button>
      </div>

      <div style={{ marginBottom: 32 }}>
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

      <div>
        <h2 style={{ fontSize: 16 }}>문제 세트 목록</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>이름</th>
              <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>강좌</th>
              <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>문제 수</th>
              <th style={{ padding: 8, textAlign: "left", fontWeight: 600 }}>작업</th>
            </tr>
          </thead>
          <tbody>
            {problemSets.map(set => (
              <tr key={set.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 8 }}>{set.name}</td>
                <td style={{ padding: 8 }}>{courses.find(c => c.id === set.course_id)?.name || set.course_id}</td>
                <td style={{ padding: 8 }}>{set.problems.length}</td>
                <td style={{ padding: 8 }}>
                  <Link href={`/teacher/problem-sets/${set.id}`} style={{ color: "#2196f3", textDecoration: "none", cursor: "pointer" }}>
                    편집
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {problemSets.length === 0 && <p style={{ fontSize: 13, color: "#999", marginTop: 8 }}>문제 세트가 없습니다.</p>}
      </div>
    </div>
  );
}
