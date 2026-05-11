"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/services/api";

type StudentResult = {
  student_id: string;
  status: string;
  branch_name?: string;
  branch_url?: string;
  commits_pushed: number;
  error_message?: string;
};

type PublishStatus = {
  id: string;
  assignment_id: string;
  status: string;
  repo_url?: string;
  started_at?: string;
  completed_at?: string;
  student_results: StudentResult[];
};

type Course = { id: string; name: string; role: string };
type Assignment = { id: string; title: string; due_at?: string };

export default function PublishPage() {
  const [githubConnected, setGithubConnected] = useState<boolean | null>(null);
  const [githubUsername, setGithubUsername] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedAssignment, setSelectedAssignment] = useState("");
  const [publishStatus, setPublishStatus] = useState<PublishStatus | null>(null);
  const [message, setMessage] = useState("");
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    apiClient.get("/github/status").then(res => {
      setGithubConnected(res.data.connected);
      if (res.data.connected) setGithubUsername(res.data.github_username);
    });
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
    apiClient.get(`/assignments/${selectedAssignment}/publish/status`)
      .then(res => setPublishStatus(res.data))
      .catch(() => setPublishStatus(null));
  }, [selectedAssignment]);

  useEffect(() => {
    if (!polling || !selectedAssignment) return;
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/assignments/${selectedAssignment}/publish/status`);
        setPublishStatus(res.data);
        if (res.data.status !== "pending" && res.data.status !== "running") {
          setPolling(false);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [polling, selectedAssignment]);

  const handlePublish = async () => {
    setMessage("");
    try {
      await apiClient.post(`/assignments/${selectedAssignment}/publish`);
      setMessage("게시 작업이 시작되었습니다.");
      setPolling(true);
    } catch (err: any) {
      setMessage(`오류: ${err.response?.data?.detail ?? "알 수 없는 오류"}`);
    }
  };

  const handleRetry = async () => {
    setMessage("");
    try {
      await apiClient.post(`/assignments/${selectedAssignment}/publish/retry`);
      setMessage("재시도 작업이 시작되었습니다.");
      setPolling(true);
    } catch (err: any) {
      setMessage(`오류: ${err.response?.data?.detail ?? "알 수 없는 오류"}`);
    }
  };

  const isPastDue = () => {
    const assignment = assignments.find(a => a.id === selectedAssignment);
    if (!assignment?.due_at) return true;
    return new Date() > new Date(assignment.due_at);
  };

  const completedCount = publishStatus?.student_results.filter(r => r.status === "success").length ?? 0;
  const totalCount = publishStatus?.student_results.length ?? 0;

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>GitHub 게시</h1>

      <div style={{ marginBottom: 20, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ fontSize: 15, marginBottom: 8 }}>GitHub 연결 상태</h2>
        {githubConnected === null ? (
          <p style={{ fontSize: 13 }}>로딩 중...</p>
        ) : githubConnected ? (
          <p style={{ fontSize: 13, color: "green" }}>연결됨: @{githubUsername}</p>
        ) : (
          <div>
            <p style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>GitHub 계정이 연결되지 않았습니다.</p>
            <a
              href="/api/v1/github/connect"
              style={{ padding: "6px 16px", background: "#24292e", color: "white", borderRadius: 4, textDecoration: "none", fontSize: 13 }}
            >
              GitHub 연결
            </a>
          </div>
        )}
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
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
            {assignments.map(a => (
              <option key={a.id} value={a.id}>
                {a.title} {a.due_at ? `(마감: ${new Date(a.due_at).toLocaleDateString("ko-KR")})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handlePublish}
            disabled={!githubConnected || !isPastDue() || polling}
            style={{
              padding: "8px 20px", background: githubConnected && isPastDue() && !polling ? "#24292e" : "#ccc",
              color: "white", border: "none", borderRadius: 4, cursor: githubConnected && isPastDue() && !polling ? "pointer" : "not-allowed",
              fontWeight: 600, fontSize: 13,
            }}
          >
            {polling ? "게시 중..." : "GitHub에 게시"}
          </button>
          {publishStatus?.status === "failed" || publishStatus?.status === "partial" ? (
            <button
              onClick={handleRetry}
              style={{ padding: "8px 20px", background: "#ff9800", color: "white", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13 }}
            >
              재시도
            </button>
          ) : null}
        </div>
        {!isPastDue() && <p style={{ fontSize: 12, color: "#999", marginTop: 4 }}>마감 이전에는 게시할 수 없습니다.</p>}
        {message && <p style={{ fontSize: 13, marginTop: 8, color: message.startsWith("오류") ? "red" : "green" }}>{message}</p>}
      </div>

      {publishStatus && (
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <div>
              <span style={{ fontWeight: 600 }}>상태: </span>
              <StatusBadge status={publishStatus.status} />
            </div>
            {publishStatus.repo_url && (
              <a href={publishStatus.repo_url} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: "#2196f3" }}>
                저장소 보기
              </a>
            )}
          </div>

          {(publishStatus.status === "running" || publishStatus.status === "pending") && totalCount > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>{completedCount}/{totalCount} 학생 완료</div>
              <div style={{ background: "#eee", borderRadius: 4, height: 8, overflow: "hidden" }}>
                <div style={{ background: "#4caf50", height: "100%", width: `${totalCount ? (completedCount / totalCount) * 100 : 0}%`, transition: "width 0.3s" }} />
              </div>
            </div>
          )}

          {publishStatus.student_results.length > 0 && (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "left" }}>학생</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>상태</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>커밋 수</th>
                  <th style={{ border: "1px solid #ddd", padding: "4px 8px" }}>브랜치</th>
                </tr>
              </thead>
              <tbody>
                {publishStatus.student_results.map(sr => (
                  <tr key={sr.student_id}>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>{sr.student_id.slice(0, 8)}...</td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>
                      <StatusBadge status={sr.status} />
                      {sr.error_message && (
                        <div style={{ fontSize: 10, color: "red", marginTop: 2 }}>{sr.error_message}</div>
                      )}
                    </td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px", textAlign: "center" }}>{sr.commits_pushed}</td>
                    <td style={{ border: "1px solid #ddd", padding: "4px 8px" }}>
                      {sr.branch_url ? (
                        <a href={sr.branch_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: "#2196f3" }}>
                          {sr.branch_name}
                        </a>
                      ) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "#9e9e9e", running: "#2196f3",
    completed: "#4caf50", partial: "#ff9800",
    failed: "#f44336", success: "#4caf50",
  };
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 4,
      background: colors[status] ?? "#9e9e9e",
      color: "white", fontSize: 11, fontWeight: 600,
    }}>
      {status}
    </span>
  );
}
