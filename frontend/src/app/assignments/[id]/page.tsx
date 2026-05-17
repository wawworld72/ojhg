"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function AssignmentRedirectPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/assignments/${id}/problem-set`);
  }, [id, router]);

  return <div style={{ padding: 16 }}>Redirecting to problem set...</div>;
}
