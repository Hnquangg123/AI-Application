const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");

export type InterviewLevel = "intern" | "fresher" | "junior" | "mid" | "senior" | "lead";
export type InterviewStyle = "technical" | "behavioral" | "mixed";
export type InterviewMode = "structured" | "conversation";

export type InterviewConfig = {
  job_role: string;
  level: InterviewLevel;
  skills: string[];
  job_description?: string;
  num_questions: number;
  language: "vi" | "en";
  style: InterviewStyle;
  mode: InterviewMode;
  project_id?: string | null;
};

export type ProjectData = {
  id: string;
  project_section_id: string | null;
  chunk_index: number | null;
  source_type: "text" | "image";
  status: "pending" | "processing" | "ready" | "failed";
  extracted_text: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectSectionBlock = {
  type: "text" | "image";
  value: string;
  caption?: string | null;
};

export type ProjectSection = {
  id: string;
  project_id: string;
  title: string;
  slug: string;
  content: { blocks: ProjectSectionBlock[] };
  sort_order: number;
  indexing_status: "pending" | "processing" | "ready" | "failed";
  indexing_error: string | null;
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  data: ProjectData[];
  sections: ProjectSection[];
  created_at: string;
  updated_at: string;
};

export type InterviewQuestion = {
  id: string;
  index: number;
  text: string;
  title: string;
  skill_tag: string | null;
  type: string;
  status: "pending" | "current" | "answered" | "skipped" | "not_attempted";
  score: number | null;
  follow_up_count: number;
};

export type InterviewMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  question_id: string | null;
  created_at: string;
};

export type InterviewSummary = {
  id: string;
  overall_score: number;
  readiness: "needs_practice" | "getting_there" | "interview_ready";
  competencies: Array<{ name: string; score: number; comment: string }>;
  strengths: string[];
  improvements: string[];
  per_question: Array<{ question_id: string; score: number; feedback: string }>;
  summary_text: string;
  created_at: string;
};

export type InterviewSession = {
  session_id: string;
  status: string;
  config: InterviewConfig;
  questions: InterviewQuestion[];
  messages: InterviewMessage[];
  current_question: InterviewQuestion | null;
  progress: { answered: number; completed: number; total: number };
  summary: InterviewSummary | null;
  action: "created" | "follow_up" | "next_question" | "skipped" | "end_interview" | null;
  done: boolean;
};

export type InterviewListItem = {
  session_id: string;
  status: string;
  config: InterviewConfig;
  progress: { answered: number; completed: number; total: number };
  message_count: number;
  overall_score: number | null;
  readiness: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type InterviewListResponse = {
  items: InterviewListItem[];
  total: number;
  limit: number;
  offset: number;
};
export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : "The request could not be completed.";
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const interviewApi = {
  create: (config: InterviewConfig) =>
    request<InterviewSession>("/interviews", { method: "POST", body: JSON.stringify(config) }),
  list: (limit = 20, offset = 0, archived = false) =>
    request<InterviewListResponse>(`/interviews?limit=${limit}&offset=${offset}&archived=${archived}`),
  get: (sessionId: string) => request<InterviewSession>(`/interviews/${sessionId}`),
  setMode: (sessionId: string, mode: InterviewMode) =>
    request<InterviewSession>(`/interviews/${sessionId}/mode`, {
      method: "PATCH",
      body: JSON.stringify({ mode }),
    }),
  archive: (sessionId: string, archived: boolean) =>
    request<{ session_id: string; archived_at: string | null }>(`/interviews/${sessionId}/archive`, {
      method: "PATCH",
      body: JSON.stringify({ archived }),
    }),
  delete: (sessionId: string) =>
    request<void>(`/interviews/${sessionId}`, { method: "DELETE" }),
  answer: (sessionId: string, message: string, questionId: string, clientMessageId: string) =>
    request<InterviewSession>(`/interviews/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ message, question_id: questionId, client_message_id: clientMessageId }),
    }),
  skip: (sessionId: string) => request<InterviewSession>(`/interviews/${sessionId}/skip`, { method: "POST" }),
  end: (sessionId: string) => request<InterviewSession>(`/interviews/${sessionId}/end`, { method: "POST" }),
  messageAudioUrl: (sessionId: string, messageId: string, voice?: string) =>
    `${API_BASE_URL}/interviews/${sessionId}/messages/${messageId}/audio${voice ? `?voice=${encodeURIComponent(voice)}` : ""}`,
};

export const projectApi = {
  list: () => request<Project[]>('/projects'),
  get: (projectId: string) => request<Project>(`/projects/${projectId}`),
  create: (name: string, description: string) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify({ name, description }) }),
  update: (projectId: string, name: string, description: string) =>
    request<Project>(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify({ name, description }) }),
  delete: (projectId: string) => request<void>(`/projects/${projectId}`, { method: 'DELETE' }),
  addData: (projectId: string, sourceType: 'text' | 'image', sourceContent: string) =>
    request<ProjectData>(`/projects/${projectId}/data`, {
      method: 'POST',
      body: JSON.stringify({ source_type: sourceType, source_content: sourceContent }),
    }),
  reindex: (projectId: string) =>
    request<{ status: string; count: number }>(`/projects/${projectId}/reindex`, { method: 'POST' }),
  createSection: (
    projectId: string,
    payload: { title: string; slug?: string; sort_order: number; content: { blocks: ProjectSectionBlock[] } },
  ) => request<ProjectSection>(`/projects/${projectId}/sections`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  updateSection: (
    projectId: string,
    sectionId: string,
    payload: { title: string; slug?: string; sort_order: number; content: { blocks: ProjectSectionBlock[] } },
  ) => request<ProjectSection>(`/projects/${projectId}/sections/${sectionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  deleteSection: (projectId: string, sectionId: string) =>
    request<void>(`/projects/${projectId}/sections/${sectionId}`, { method: "DELETE" }),
  indexSection: (projectId: string, sectionId: string) =>
    request<{ status: string; count: number }>(`/projects/${projectId}/sections/${sectionId}/index`, {
      method: "POST",
    }),
};
