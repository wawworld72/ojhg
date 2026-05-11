"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/services/api";
import JsonImportDropzone, { ViolationList } from "@/components/import/JsonImportDropzone";

type Course = { id: string; name: string; role: string };
type Violation = { field?: string; message: string; problem_index?: number };

type ImportMode = "problem" | "assignment";

export default function ImportPage() {
  const [mode, setMode] = useState<ImportMode>("problem");
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [problemSetId, setProblemSetId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiClient.get("/courses").then(res => {
      const teacherCourses = res.data.filter((c: Course) => c.role === "teacher");
      setCourses(teacherCourses);
      if (teacherCourses.length > 0) setSelectedCourse(teacherCourses[0].id);
    });
  }, []);

  const handleFileSelected = (f: File) => {
    setFile(f);
    setViolations([]);
    setResult(null);
    setMessage("");
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    setViolations([]);
    setResult(null);
    setMessage("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      if (mode === "problem") {
        if (!problemSetId.trim()) {
          setMessage("문제 세트 ID를 입력하세요.");
          setLoading(false);
          return;
        }
        formData.append("problem_set_id", problemSetId.trim());
        const res = await apiClient.post("/problems/import", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setResult(res.data);
        setMessage("문제가 성공적으로 가져와졌습니다.");
      } else {
        formData.append("course_id", selectedCourse);
        const res = await apiClient.post("/problem-sets/import", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setResult(res.data);
        setMessage(`과제가 성공적으로 가져와졌습니다. (${res.data.problems_created}개 문제 생성)`);
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.violations) {
        setViolations(detail.violations);
      } else if (typeof detail === "string") {
        setMessage(`오류: ${detail}`);
      } else {
        setMessage("가져오기에 실패했습니다.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>JSON 가져오기</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button
          onClick={() => setMode("problem")}
          style={{
            padding: "6px 16px", borderRadius: 4, border: "1px solid #ddd",
            background: mode === "problem" ? "#2196f3" : "white",
            color: mode === "problem" ? "white" : "#333",
            cursor: "pointer", fontSize: 13,
          }}
        >
          단일 문제
        </button>
        <button
          onClick={() => setMode("assignment")}
          style={{
            padding: "6px 16px", borderRadius: 4, border: "1px solid #ddd",
            background: mode === "assignment" ? "#2196f3" : "white",
            color: mode === "assignment" ? "white" : "#333",
            cursor: "pointer", fontSize: 13,
          }}
        >
          과제 (여러 문제)
        </button>
      </div>

      {mode === "problem" ? (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>문제 세트 ID</label>
          <input
            value={problemSetId}
            onChange={e => setProblemSetId(e.target.value)}
            placeholder="problem-set UUID"
            style={{ width: "100%", padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, fontSize: 13 }}
          />
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>강좌 선택</label>
          <select
            value={selectedCourse}
            onChange={e => setSelectedCourse(e.target.value)}
            style={{ padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, fontSize: 13 }}
          >
            {courses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      )}

      <JsonImportDropzone onFileSelected={handleFileSelected} />

      {file && (
        <p style={{ fontSize: 13, color: "#555", marginTop: 8 }}>
          선택된 파일: <strong>{file.name}</strong>
        </p>
      )}

      <ViolationList violations={violations} />

      {message && (
        <p style={{ fontSize: 13, marginTop: 8, color: message.startsWith("오류") || message.startsWith("가져오기") && !message.includes("성공") ? "red" : "green" }}>
          {message}
        </p>
      )}

      {result && (
        <div style={{ marginTop: 12, padding: 12, background: "#f0fff0", border: "1px solid #4caf50", borderRadius: 6 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#2e7d32", margin: "0 0 8px" }}>가져오기 성공</p>
          {mode === "problem" ? (
            <p style={{ fontSize: 12, margin: 0 }}>문제 ID: {result.id} — {result.title}</p>
          ) : (
            <div>
              <p style={{ fontSize: 12, margin: "0 0 4px" }}>문제 세트 ID: {result.problem_set_id}</p>
              <p style={{ fontSize: 12, margin: "0 0 4px" }}>이름: {result.name}</p>
              <p style={{ fontSize: 12, margin: 0 }}>생성된 문제: {result.problems_created}개</p>
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <button
          onClick={handleImport}
          disabled={!file || loading}
          style={{
            padding: "8px 24px",
            background: file && !loading ? "#2196f3" : "#ccc",
            color: "white", border: "none", borderRadius: 4,
            cursor: file && !loading ? "pointer" : "not-allowed",
            fontWeight: 600, fontSize: 13,
          }}
        >
          {loading ? "가져오는 중..." : "가져오기"}
        </button>
      </div>
    </div>
  );
}
