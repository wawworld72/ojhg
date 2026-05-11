"use client";

import { useCallback, useState } from "react";

type Violation = { field?: string; message: string; problem_index?: number };

type Props = {
  onFileSelected: (file: File) => void;
  accept?: string;
};

export default function JsonImportDropzone({ onFileSelected, accept = ".json" }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }, [onFileSelected]);

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      style={{
        border: `2px dashed ${dragging ? "#2196f3" : "#ccc"}`,
        borderRadius: 8,
        padding: 32,
        textAlign: "center",
        cursor: "pointer",
        background: dragging ? "#e3f2fd" : "#fafafa",
        transition: "all 0.2s",
      }}
    >
      <p style={{ fontSize: 14, color: "#666", margin: 0 }}>
        JSON 파일을 여기에 드래그하거나{" "}
        <label style={{ color: "#2196f3", cursor: "pointer", textDecoration: "underline" }}>
          클릭하여 선택
          <input
            type="file"
            accept={accept}
            style={{ display: "none" }}
            onChange={e => {
              const file = e.target.files?.[0];
              if (file) onFileSelected(file);
            }}
          />
        </label>
      </p>
      <p style={{ fontSize: 12, color: "#999", marginTop: 8 }}>problem.schema.json 또는 assignment.schema.json</p>
    </div>
  );
}

export function ViolationList({ violations }: { violations: Violation[] }) {
  if (!violations.length) return null;
  return (
    <div style={{ background: "#fff3f3", border: "1px solid #f44336", borderRadius: 6, padding: 12, marginTop: 12 }}>
      <p style={{ fontSize: 13, fontWeight: 600, color: "#f44336", margin: "0 0 8px" }}>유효성 오류:</p>
      <ul style={{ margin: 0, paddingLeft: 20 }}>
        {violations.map((v, i) => (
          <li key={i} style={{ fontSize: 12, color: "#c62828" }}>
            {v.problem_index !== undefined ? `[문제 ${v.problem_index + 1}] ` : ""}
            {v.field ? `${v.field}: ` : ""}
            {v.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
