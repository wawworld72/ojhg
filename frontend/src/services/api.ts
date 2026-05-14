import axios, { AxiosError, AxiosResponse } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost";

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Redirect to login on 401
apiClient.interceptors.response.use(
  (res: AxiosResponse) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.location.href = `${BASE_URL}/api/v1/auth/google`;
    }
    return Promise.reject(error);
  }
);

export type ApiError = {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
};

export function getApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error) && error.response?.data?.error) {
    return error.response.data.error as ApiError;
  }
  return { code: "UNKNOWN_ERROR", message: "An unexpected error occurred", details: null };
}

// SSE helper for submission result streaming
export function subscribeSubmissionStream(
  submissionId: string,
  onVerdict: (data: { verdict: string; score: number | null; attempt_number: number }) => void,
  onError?: (err: Event) => void
): EventSource {
  const es = new EventSource(`${BASE_URL}/api/v1/submissions/${submissionId}/stream`, {
    withCredentials: true,
  });
  es.addEventListener("verdict", (e: MessageEvent) => {
    onVerdict(JSON.parse(e.data));
    es.close();
  });
  if (onError) es.onerror = onError;
  return es;
}
