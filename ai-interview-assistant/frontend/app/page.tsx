"use client";

import Image from "next/image";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import {
  InterviewLevel,
  InterviewListItem,
  InterviewMode,
  InterviewSession,
  InterviewStyle,
  interviewApi,
  Project,
  ProjectSection,
  ProjectSectionBlock,
  projectApi,
} from "../lib/api";
import { getTranslations, UiLanguage } from "../lib/i18n";

type Stage = "setup" | "interview" | "summary" | "sessions" | "projects";
type Theme = "light" | "dark";
const STORAGE_KEY = "mockmate.sessionId";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0?: { transcript: string } }> }) => void) | null;
  onspeechstart: (() => void) | null;
  onspeechend: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;
type VoiceStatus = "idle" | "speaking" | "listening" | "transcribing" | "submitting" | "processing" | "error";
const SILENCE_TIMEOUT_MS = 4000;
const MIN_VOICE_ANSWER_LENGTH = 2;
const END_SIGNAL_PATTERN = /\b(?:that's all|thats all|i am done|i'm done|im done|that's it|thats it)\b/i;

function hasEndSignal(text: string) {
  return END_SIGNAL_PATTERN.test(text);
}

function ClayLogo() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <span className="brand-dot brand-dot-one" />
      <span className="brand-dot brand-dot-two" />
      <span className="brand-spark">&#10022;</span>
    </div>
  );
}

const speakButtonStyle: React.CSSProperties = {
  marginInlineStart: 8,
  padding: 2,
  border: "none",
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  opacity: 0.7,
  verticalAlign: "middle",
  display: "inline-flex",
  alignItems: "center",
  lineHeight: 0,
};

function SpeakerIcon({ playing }: { playing: boolean }) {
  if (playing) {
    return (
      <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true">
        <rect x="6" y="6" width="12" height="12" rx="2" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M11 5 6 9H3v6h3l5 4z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M18.5 6a9 9 0 0 1 0 12" />
    </svg>
  );
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function readinessLabel(value: string | undefined, t: ReturnType<typeof getTranslations>) {
  if (value === "interview_ready") return t.interviewReady;
  if (value === "getting_there") return t.gettingThere;
  return t.keepPracticing;
}

function questionCategory(type: string, skill: string | null, language: UiLanguage) {
  if (skill) return skill;
  const translated: Record<string, string> = language === "vi"
    ? { technical: "Kỹ thuật", behavioral: "Hành vi", system_design: "Thiết kế hệ thống", coding: "Lập trình", hr: "Nhân sự" }
    : { technical: "Technical", behavioral: "Behavioral", system_design: "System design", coding: "Coding", hr: "HR" };
  if (translated[type]) return translated[type];
  return type.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function levelLabel(value: string, t: ReturnType<typeof getTranslations>) {
  const key = value.toLowerCase() as "junior" | "mid" | "senior" | "lead";
  return t[key] ?? value;
}

function sessionStatus(value: string, language: UiLanguage) {
  const labels: Record<string, string> = language === "vi"
    ? { in_progress: "đang thực hiện", summarized: "đã hoàn thành", failed: "thất bại", evaluating: "đang đánh giá" }
    : { in_progress: "in progress", summarized: "completed", failed: "failed", evaluating: "evaluating" };
  return labels[value] ?? value.replaceAll("_", " ");
}

export default function Home() {
  const [stage, setStage] = useState<Stage>("setup");
  const [theme, setTheme] = useState<Theme>("light");
  const [language, setLanguage] = useState<UiLanguage>("en");
  const [practiceLanguage, setPracticeLanguage] = useState<UiLanguage>("en");
  const [role, setRole] = useState("Backend Engineer");
  const [level, setLevel] = useState("Senior");
  const [skills, setSkills] = useState("Python, FastAPI, PostgreSQL");
  const [style, setStyle] = useState("Mixed");
  const [interviewMode, setInterviewMode] = useState<InterviewMode>("structured");
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [sessionHistory, setSessionHistory] = useState<InterviewListItem[]>([]);
  const [historySession, setHistorySession] = useState<InterviewSession | null>(null);
  const [historyArchived, setHistoryArchived] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [sectionEditorOpen, setSectionEditorOpen] = useState(false);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [sectionTitle, setSectionTitle] = useState("");
  const [sectionSlug, setSectionSlug] = useState("");
  const [sectionBlocks, setSectionBlocks] = useState<ProjectSectionBlock[]>([]);
  const [indexingProjectId, setIndexingProjectId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const transcriptEnd = useRef<HTMLDivElement>(null);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const finalTranscriptRef = useRef("");
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speechEndedRef = useRef(false);
  const spokenMessageIdRef = useRef<string | null>(null);
  const speakAssistantRef = useRef<(messageId: string, text: string) => void>(() => undefined);

  const t = getTranslations(language);
  const questions = session?.questions ?? [];
  const messages = session?.messages;
  const summary = session?.summary;
  const currentQuestion = session?.current_question;
  const completedCount = session?.progress.completed ?? 0;
  const totalQuestions = session?.progress.total ?? 6;
  const plannedQuestionCount = selectedProjectId ? 7 : 6;
  const progress = totalQuestions ? Math.round((completedCount / totalQuestions) * 100) : 0;

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    projectApi.list().then(setProjects).catch(() => undefined);
    const frame = window.requestAnimationFrame(() => {
      if (new URLSearchParams(window.location.search).get("view") === "projects") setStage("projects");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const saved = window.localStorage.getItem("mockmate.language");
      const detected: UiLanguage = saved === "vi" || (!saved && navigator.language.toLowerCase().startsWith("vi")) ? "vi" : "en";
      setLanguage(detected);
      if (!window.localStorage.getItem(STORAGE_KEY)) setPracticeLanguage(detected);
      document.documentElement.lang = detected;
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function syncSession(next: InterviewSession) {
    setSession(next);
    setRole(next.config.job_role);
    setLevel(next.config.level[0].toUpperCase() + next.config.level.slice(1));
    setSkills(next.config.skills.join(", "));
    setStyle(next.config.style[0].toUpperCase() + next.config.style.slice(1));
    setInterviewMode(next.config.mode ?? "structured");
    setPracticeLanguage(next.config.language);
    window.localStorage.setItem(STORAGE_KEY, next.session_id);
    setStage(next.summary ? "summary" : "interview");
  }

  useEffect(() => {
    const savedSessionId = window.localStorage.getItem(STORAGE_KEY);
    if (!savedSessionId) return;
    interviewApi.get(savedSessionId)
      .then(syncSession)
      .catch(() => window.localStorage.removeItem(STORAGE_KEY));
  }, []);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, isBusy]);

  useEffect(() => () => {
    window.speechSynthesis.cancel();
    recognitionRef.current?.stop();
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
  }, []);

  useEffect(() => {
    function closeMenusOnOutsidePress(event: PointerEvent) {
      if (!(event.target instanceof Node)) return;
      document.querySelectorAll<HTMLDetailsElement>(".history-item-menu[open]").forEach((menu) => {
        if (!menu.contains(event.target as Node)) menu.removeAttribute("open");
      });
    }

    function closeMenusOnEscape(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") return;
      const menu = document.querySelector<HTMLDetailsElement>(".history-item-menu[open]");
      if (!menu) return;
      menu.removeAttribute("open");
      menu.querySelector<HTMLElement>("summary")?.focus();
    }

    document.addEventListener("pointerdown", closeMenusOnOutsidePress);
    document.addEventListener("keydown", closeMenusOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeMenusOnOutsidePress);
      document.removeEventListener("keydown", closeMenusOnEscape);
    };
  }, []);

  async function showSessions(archived = false) {
    setStage("sessions");
    setHistoryArchived(archived);
    setHistorySession(null);
    setIsBusy(true);
    setError(null);
    try {
      const history = await interviewApi.list(20, 0, archived);
      setSessionHistory(history.items);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function showProjects() {
    setStage("projects");
    setIsBusy(true);
    setError(null);
    try {
      setProjects(await projectApi.list());
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  function beginProjectEdit(project?: Project) {
    setEditingProjectId(project?.id ?? null);
    setProjectName(project?.name ?? "");
    setProjectDescription(project?.description ?? "");
    setSectionEditorOpen(false);
    setEditingSectionId(null);
    setSectionTitle("");
    setSectionSlug("");
    setSectionBlocks([]);
  }

  async function saveProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectName.trim() || isBusy) return;
    setIsBusy(true);
    setError(null);
    try {
      const saved = editingProjectId
        ? await projectApi.update(editingProjectId, projectName.trim(), projectDescription.trim())
        : await projectApi.create(projectName.trim(), projectDescription.trim());
      if (!editingProjectId) {
        window.location.assign(`/projects/${saved.id}`);
        return;
      }
      setProjects(await projectApi.list());
      setEditingProjectId(saved.id);
      setProjectName(saved.name);
      setProjectDescription(saved.description);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteProject(project: Project) {
    if (!window.confirm(`${t.deleteProjectConfirm} ${project.name}?`)) return;
    setIsBusy(true);
    setError(null);
    try {
      await projectApi.delete(project.id);
      if (selectedProjectId === project.id) setSelectedProjectId("");
      if (editingProjectId === project.id) beginProjectEdit();
      setProjects(await projectApi.list());
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  function beginSectionCreate() {
    setSectionEditorOpen(true);
    setEditingSectionId(null);
    setSectionTitle("");
    setSectionSlug("");
    setSectionBlocks([{ type: "text", value: "" }]);
  }

  function beginSectionEdit(section: ProjectSection) {
    setSectionEditorOpen(true);
    setEditingSectionId(section.id);
    setSectionTitle(section.title);
    setSectionSlug(section.slug);
    setSectionBlocks(section.content.blocks.map((block) => ({ ...block })));
  }

  function updateSectionBlock(index: number, update: Partial<ProjectSectionBlock>) {
    setSectionBlocks((current) => current.map((block, blockIndex) =>
      blockIndex === index ? { ...block, ...update } : block,
    ));
  }

  function addSectionImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") return;
      setSectionBlocks((current) => [...current, { type: "image", value: reader.result as string, caption: file.name }]);
      event.target.value = "";
    };
    reader.readAsDataURL(file);
  }

  async function saveSection(event: FormEvent<HTMLFormElement>, project: Project) {
    event.preventDefault();
    if (!sectionTitle.trim() || isBusy) return;
    const blocks = sectionBlocks.filter((block) => block.value.trim());
    setIsBusy(true);
    setError(null);
    try {
      const payload = {
        title: sectionTitle.trim(),
        slug: sectionSlug.trim() || undefined,
        sort_order: editingSectionId
          ? project.sections.find((section) => section.id === editingSectionId)?.sort_order ?? project.sections.length
          : project.sections.length,
        content: { blocks },
      };
      const saved = editingSectionId
        ? await projectApi.updateSection(project.id, editingSectionId, payload)
        : await projectApi.createSection(project.id, payload);
      const updated = await projectApi.get(project.id);
      setProjects((current) => current.map((item) => item.id === updated.id ? updated : item));
      beginSectionEdit(saved);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteSection(project: Project, section: ProjectSection) {
    if (!window.confirm(`${t.deletePageConfirm} ${section.title}?`)) return;
    setIsBusy(true);
    setError(null);
    try {
      await projectApi.deleteSection(project.id, section.id);
      const updated = await projectApi.get(project.id);
      setProjects((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSectionEditorOpen(false);
      setEditingSectionId(null);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function buildProjectRag(project: Project) {
    const legacyData = project.data.filter((item) => !item.project_section_id);
    if ((project.sections.length === 0 && legacyData.length === 0) || indexingProjectId) {
      if (project.sections.length === 0 && legacyData.length === 0) setError(t.noProjectData);
      return;
    }
    setIndexingProjectId(project.id);
    setError(null);
    try {
      await projectApi.reindex(project.id);
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const updated = await projectApi.get(project.id);
        setProjects((current) => current.map((item) => item.id === updated.id ? updated : item));
        const finished = updated.sections.every((section) => section.indexing_status === "ready" || section.indexing_status === "failed")
          && updated.data.filter((item) => !item.project_section_id).every((item) => item.status === "ready" || item.status === "failed");
        if (!finished) continue;
        if (updated.sections.some((section) => section.indexing_status === "failed") || updated.data.some((item) => item.status === "failed")) setError(t.ragFailed);
        return;
      }
      setError(t.ragStillProcessing);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIndexingProjectId(null);
    }
  }

  async function openHistorySession(sessionId: string) {
    setIsBusy(true);
    setError(null);
    try {
      setHistorySession(await interviewApi.get(sessionId));
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function updateArchive(sessionId: string, archived: boolean) {
    setIsBusy(true);
    setError(null);
    try {
      await interviewApi.archive(sessionId, archived);
      if (historySession?.session_id === sessionId) setHistorySession(null);
      const history = await interviewApi.list(20, 0, historyArchived);
      setSessionHistory(history.items);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteHistorySession(item: InterviewListItem) {
    const confirmed = window.confirm(
      `${t.deleteConfirmBefore} ${item.config.job_role} ${t.deleteConfirmAfter}`,
    );
    if (!confirmed) return;

    setIsBusy(true);
    setError(null);
    try {
      await interviewApi.delete(item.session_id);
      if (historySession?.session_id === item.session_id) setHistorySession(null);
      if (session?.session_id === item.session_id) {
        window.localStorage.removeItem(STORAGE_KEY);
        setSession(null);
      }
      const history = await interviewApi.list(20, 0, historyArchived);
      setSessionHistory(history.items);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function beginInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsBusy(true);
    setError(null);
    try {
      const next = await interviewApi.create({
        job_role: role.trim(),
        level: level.toLowerCase() as InterviewLevel,
        skills: skills.split(",").map((skill) => skill.trim()).filter(Boolean),
         num_questions: 6,
         language: practiceLanguage,
         style: style.toLowerCase() as InterviewStyle,
         mode: interviewMode,
         project_id: selectedProjectId || null,
       });
      syncSession(next);
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function finalizeInterview(sessionId = session?.session_id) {
    if (!sessionId || isBusy) return;
    stopVoiceLoop();
    setIsBusy(true);
    setError(null);
    try {
      syncSession(await interviewApi.end(sessionId));
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function submitAnswer(candidateAnswer = answer) {
    const cleanAnswer = candidateAnswer.trim();
    if (!cleanAnswer || !session || !currentQuestion || isBusy) return;
    stopListening();
    setVoiceStatus("processing");
    setIsBusy(true);
    setError(null);
    try {
      let next = await interviewApi.answer(
        session.session_id,
        cleanAnswer,
        currentQuestion.id,
        crypto.randomUUID(),
      );
      setAnswer("");
      if (next.done && !next.summary) next = await interviewApi.end(next.session_id);
      syncSession(next);
      setVoiceStatus(next.summary ? "idle" : "speaking");
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
      setVoiceStatus("error");
    } finally {
      setIsBusy(false);
    }
  }

  async function skipQuestion() {
    if (!session || isBusy) return;
    stopVoiceLoop();
    setIsBusy(true);
    setError(null);
    try {
      let next = await interviewApi.skip(session.session_id);
      if (next.done && !next.summary) next = await interviewApi.end(next.session_id);
      syncSession(next);
      setVoiceStatus(next.summary ? "idle" : "speaking");
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (session?.config.mode === "conversation") return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitAnswer();
    }
  }

  async function toggleConversationMode() {
    if (!session || isBusy) return;
    const nextMode: InterviewMode = session.config.mode === "conversation" ? "structured" : "conversation";
    if (nextMode === "structured") stopVoiceLoop();
    setIsBusy(true);
    setError(null);
    try {
      const next = await interviewApi.setMode(session.session_id, nextMode);
      syncSession(next);
      setVoiceStatus(nextMode === "conversation" ? "speaking" : "idle");
    } catch (requestError) {
      setError(errorMessage(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  function stopListening() {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setIsListening(false);
  }

  function stopVoiceLoop() {
    window.speechSynthesis.cancel();
    setPlayingMessageId(null);
    stopListening();
    setVoiceStatus("idle");
  }

  function startListening() {
    const speechConstructor = (window as unknown as { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor });
    const Recognition = speechConstructor.SpeechRecognition ?? speechConstructor.webkitSpeechRecognition;
    if (!Recognition) {
      setError(t.voiceUnsupported);
      setVoiceStatus("error");
      return;
    }
    stopListening();
    finalTranscriptRef.current = "";
    speechEndedRef.current = false;
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    const scheduleVoiceSubmit = () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const finalAnswer = finalTranscriptRef.current.trim();
        if (finalAnswer.length < MIN_VOICE_ANSWER_LENGTH) {
          setVoiceStatus("listening");
          return;
        }
        setVoiceStatus("submitting");
        void submitAnswer(finalAnswer);
      }, SILENCE_TIMEOUT_MS);
    };
    recognition.onspeechstart = () => {
      speechEndedRef.current = false;
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      setVoiceStatus("listening");
    };
    recognition.onspeechend = () => {
      speechEndedRef.current = true;
      setVoiceStatus("transcribing");
      scheduleVoiceSubmit();
    };
    recognition.onresult = (event) => {
      let interimTranscript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result?.[0]?.transcript ?? "";
        if (result?.isFinal) {
          finalTranscriptRef.current += text;
          if (hasEndSignal(finalTranscriptRef.current)) {
            if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            setVoiceStatus("submitting");
            void submitAnswer(finalTranscriptRef.current.trim());
          } else if (speechEndedRef.current) {
            scheduleVoiceSubmit();
          }
        }
        else interimTranscript += text;
      }
      const transcript = `${finalTranscriptRef.current} ${interimTranscript}`.trim();
      setAnswer(transcript);
      setVoiceStatus(finalTranscriptRef.current.trim() ? "transcribing" : "listening");
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setIsListening(false);
      if (voiceStatus !== "submitting" && voiceStatus !== "processing") setVoiceStatus("idle");
    };
    recognition.onerror = (event) => {
      recognitionRef.current = null;
      setIsListening(false);
      setVoiceStatus("error");
      setError(event.error === "not-allowed" ? t.voicePermission : t.voiceError);
    };
    recognitionRef.current = recognition;
    setIsListening(true);
    setVoiceStatus("listening");
    recognition.start();
  }

  function toggleListening() {
    if (isListening) {
      stopListening();
      setVoiceStatus("idle");
      return;
    }
    window.speechSynthesis.cancel();
    setPlayingMessageId(null);
    startListening();
  }

  function changeDisplayLanguage(nextLanguage: UiLanguage) {
    setLanguage(nextLanguage);
    document.documentElement.lang = nextLanguage;
    window.localStorage.setItem("mockmate.language", nextLanguage);
  }

  function toggleTheme() {
    const nextTheme: Theme = theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem("mockmate.theme", nextTheme);
    setTheme(nextTheme);
  }

  function resetInterview() {
    stopVoiceLoop();
    setInterviewMode("structured");
    window.localStorage.removeItem(STORAGE_KEY);
    setStage("setup");
    setSession(null);
    setAnswer("");
    setError(null);
  }

  function exportFeedback() {
    if (!session?.summary) return;
    const blob = new Blob([JSON.stringify(session, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `mockmate-feedback-${session.session_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function toggleSpeak(messageId: string, text: string, messageLanguage: UiLanguage) {
    if (!("speechSynthesis" in window)) {
      setError(t.audioError);
      return;
    }

    if (playingMessageId === messageId) {
      window.speechSynthesis.cancel();
      setPlayingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = messageLanguage === "vi" ? "vi-VN" : "en-US";
    utterance.rate = 1;
    utterance.pitch = 1;
    setPlayingMessageId(messageId);
    utterance.onend = () => {
      setPlayingMessageId((current) => current === messageId ? null : current);
    };
    utterance.onerror = () => {
      setPlayingMessageId((current) => current === messageId ? null : current);
      setError(t.audioError);
    };
    window.speechSynthesis.speak(utterance);
  }

  function speakAssistantMessage(messageId: string, text: string) {
    if (!("speechSynthesis" in window)) {
      setError(t.audioError);
      setVoiceStatus("error");
      return;
    }
    stopListening();
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1;
    utterance.pitch = 1;
    setPlayingMessageId(messageId);
    setVoiceStatus("speaking");
    utterance.onend = () => {
      setPlayingMessageId((current) => current === messageId ? null : current);
      if (session?.config.mode === "conversation" && !isBusy) startListening();
    };
    utterance.onerror = () => {
      setPlayingMessageId((current) => current === messageId ? null : current);
      setVoiceStatus("error");
      setError(t.audioError);
    };
    window.speechSynthesis.speak(utterance);
  }

  useEffect(() => {
    speakAssistantRef.current = speakAssistantMessage;
  });

  useEffect(() => {
    if (stage !== "interview" || session?.config.mode !== "conversation") return;
    const latestAssistant = [...(messages ?? [])].reverse().find((message) => message.role === "assistant");
    if (!latestAssistant || latestAssistant.id === spokenMessageIdRef.current || isBusy) return;
    spokenMessageIdRef.current = latestAssistant.id;
    speakAssistantRef.current(latestAssistant.id, latestAssistant.content);
  }, [messages, session?.config.mode, stage, isBusy]);

  return (
    <main className="app-shell">
      <div className="ambient-world" aria-hidden="true">
        <span className="ambient-blob blob-violet" />
        <span className="ambient-blob blob-pink" />
        <span className="ambient-blob blob-blue" />
        <span className="ambient-blob blob-green" />
      </div>

       <header className="topbar clay-card">
        <a className="brand" href="#top" aria-label="MockMate"><ClayLogo /><span>MockMate</span></a>
        <nav className="topnav" aria-label={t.primaryNavigation}>
          <button className={`nav-link ${stage !== "sessions" && stage !== "projects" ? "is-active" : ""}`} type="button" onClick={() => setStage(session?.summary ? "summary" : session ? "interview" : "setup")}>{t.navPractice}</button>
          <button className={`nav-link ${stage === "sessions" ? "is-active" : ""}`} type="button" onClick={() => void showSessions()}>{t.navSessions}</button>
          <button className="nav-link" type="button">{t.navHow}</button>
          <button className={`nav-link ${stage === "projects" ? "is-active" : ""}`} type="button" onClick={() => void showProjects()}>{t.manageProjects}</button>
        </nav>
        <div className="header-actions">
          <label className="language-control"><span className="sr-only">{t.languageLabel}</span><select value={language} onChange={(event) => changeDisplayLanguage(event.target.value as UiLanguage)} aria-label={t.languageLabel}><option value="en">EN</option><option value="vi">VI</option></select></label>
          <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={theme === "light" ? t.themeDark : t.themeLight} title={theme === "light" ? t.themeDark : t.themeLight}>
            <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span>
          </button>
          <button className="avatar-button" type="button" aria-label={t.profile}>DC</button>
        </div>
      </header>

      {error && (
        <div className="api-error clay-card" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} aria-label={t.dismissError}>x</button>
        </div>
      )}

      {stage === "projects" && (
        <section className="history-layout" id="top">
          <div className="history-heading">
            <div>
              <span className="eyebrow clay-pill"><span>&#10022;</span> {t.manageProjects}</span>
              <h1>{t.projectKnowledge}</h1>
              <p>{t.projectKnowledgeDescription}</p>
            </div>
            <button className="clay-button primary-button history-new-button" type="button" onClick={() => beginProjectEdit()}>{t.newProject} <span>+</span></button>
          </div>
          <div className="history-workspace">
            <aside className="history-list clay-card" aria-label={t.projects}>
              <div className="history-list-heading"><span>{t.projects}</span><strong>{projects.length}</strong></div>
              {projects.length === 0 && <div className="history-empty"><strong>{t.noProjects}</strong><span>{t.createProjectHint}</span></div>}
              {projects.map((project) => (
                <button className="history-item-open" type="button" key={project.id} onClick={() => window.location.assign(`/projects/${project.id}`)}>
                  <div><strong>{project.name}</strong><span>{project.sections.length} {t.projectPages.toLowerCase()}</span></div>
                  <div className="history-item-meta"><b>{project.sections.filter((section) => section.indexing_status === "ready").length}/{project.sections.length}</b></div>
                </button>
              ))}
            </aside>
            <article className="history-chat clay-surface">
              {editingProjectId === null && <form className="setup-card project-editor" onSubmit={saveProject}>
                <div className="card-heading"><div><span className="step-label">{t.project}</span><h2>{t.newProject}</h2></div></div>
                <label className="field"><span>{t.projectName}</span><input value={projectName} onChange={(event) => setProjectName(event.target.value)} required /></label>
                <label className="field"><span>{t.projectDescription}</span><textarea value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} rows={5} /></label>
                <button className="clay-button primary-button" type="submit" disabled={isBusy}>{t.saveProject}</button>
              </form>}
              {editingProjectId && (() => {
                const project = projects.find((item) => item.id === editingProjectId);
                if (!project) return null;
                return <div className="project-editor">
                  <form className="setup-card project-settings" onSubmit={saveProject}>
                    <div className="card-heading"><div><span className="step-label">{t.project}</span><h2>{t.editProject}</h2></div></div>
                    <label className="field"><span>{t.projectName}</span><input value={projectName} onChange={(event) => setProjectName(event.target.value)} required /></label>
                    <label className="field"><span>{t.projectDescription}</span><textarea value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} rows={4} /></label>
                    <div className="project-editor-actions"><button className="clay-button primary-button" type="submit" disabled={isBusy}>{t.saveProject}</button><button className="clay-button secondary-button" type="button" onClick={() => void buildProjectRag(project)} disabled={isBusy || indexingProjectId !== null || project.sections.length === 0}>{indexingProjectId === project.id ? t.buildingRag : t.buildRag}</button><button className="clay-button secondary-button danger-button" type="button" onClick={() => void deleteProject(project)} disabled={isBusy || indexingProjectId !== null}>{t.delete}</button></div>
                  </form>
                  <div className="docs-manager">
                    <aside className="docs-sidebar">
                      <div className="docs-sidebar-heading"><div><span className="step-label">{t.projectPages}</span><strong>{project.sections.length}</strong></div><button type="button" onClick={beginSectionCreate} aria-label={t.newPage} title={t.newPage}>+</button></div>
                      {project.sections.length === 0 && <p className="docs-empty">{t.noPages}</p>}
                      {project.sections.map((section) => <button className={`docs-page-link ${editingSectionId === section.id ? "active" : ""}`} type="button" key={section.id} onClick={() => beginSectionEdit(section)}><span>{section.title}</span><small className={`index-status ${section.indexing_status}`}>{section.indexing_status}</small></button>)}
                    </aside>
                    <div className="docs-content">
                      {!sectionEditorOpen && <div className="history-placeholder"><div className="mini-orb orb-purple" aria-hidden="true">&#10022;</div><h2>{t.selectPage}</h2><p>{t.selectPageHint}</p><button className="clay-button primary-button" type="button" onClick={beginSectionCreate}>{t.newPage}</button></div>}
                      {sectionEditorOpen && <form className="section-editor" onSubmit={(event) => void saveSection(event, project)}>
                        <div className="section-editor-heading"><div><span className="step-label">{editingSectionId ? t.editPage : t.newPage}</span><h2>{sectionTitle || t.untitledPage}</h2></div>{editingSectionId && <small className={`index-status ${project.sections.find((section) => section.id === editingSectionId)?.indexing_status ?? "pending"}`}>{project.sections.find((section) => section.id === editingSectionId)?.indexing_status ?? "pending"}</small>}</div>
                        <div className="section-fields">
                          <label className="field"><span>{t.pageTitle}</span><input value={sectionTitle} onChange={(event) => setSectionTitle(event.target.value)} required /></label>
                          <label className="field"><span>{t.pageSlug}</span><input value={sectionSlug} onChange={(event) => setSectionSlug(event.target.value)} placeholder={t.pageSlugHint} /></label>
                        </div>
                        <div className="content-blocks">
                          {sectionBlocks.map((block, index) => <div className={`content-block ${block.type}`} key={`${block.type}-${index}`}>
                            <div className="content-block-heading"><strong>{block.type === "text" ? t.textBlock : t.imageBlock}</strong><button type="button" onClick={() => setSectionBlocks((current) => current.filter((_, blockIndex) => blockIndex !== index))}>{t.removeBlock}</button></div>
                            {block.type === "text" ? <textarea value={block.value} onChange={(event) => updateSectionBlock(index, { value: event.target.value })} rows={10} placeholder={t.textContentHint} /> : <><Image src={block.value} alt={block.caption || t.imageBlock} width={1200} height={700} unoptimized /><label className="field"><span>{t.imageCaption}</span><input value={block.caption ?? ""} onChange={(event) => updateSectionBlock(index, { caption: event.target.value })} /></label></>}
                          </div>)}
                          {sectionBlocks.length === 0 && <p className="docs-empty">{t.noBlocks}</p>}
                        </div>
                        <div className="block-toolbar"><button className="clay-button secondary-button" type="button" onClick={() => setSectionBlocks((current) => [...current, { type: "text", value: "" }])}>+ {t.addTextBlock}</button><label className="clay-button secondary-button file-button">+ {t.addImageBlock}<input type="file" accept="image/png,image/jpeg,image/webp" onChange={addSectionImage} /></label></div>
                        <div className="section-actions"><button className="clay-button primary-button" type="submit" disabled={isBusy || !sectionTitle.trim()}>{isBusy ? t.savingPage : t.savePage}</button>{editingSectionId && <button className="clay-button secondary-button danger-button" type="button" onClick={() => { const section = project.sections.find((item) => item.id === editingSectionId); if (section) void deleteSection(project, section); }} disabled={isBusy}>{t.deletePage}</button>}</div>
                        {editingSectionId && project.sections.find((section) => section.id === editingSectionId)?.indexing_error && <p className="section-index-error">{project.sections.find((section) => section.id === editingSectionId)?.indexing_error}</p>}
                      </form>}
                    </div>
                  </div>
                  <div className="rag-summary"><div><span className="step-label">RAG INDEX</span><strong>{project.sections.filter((section) => section.indexing_status === "ready").length}/{project.sections.length} {t.pagesReady}</strong></div><span>{project.data.filter((item) => item.project_section_id).length} {t.vectorChunks}</span></div>
                </div>;
              })()}
            </article>
          </div>
        </section>
      )}

      {stage === "sessions" && (
        <section className="history-layout" id="top">
          <div className="history-heading">
            <div>
              <span className="eyebrow clay-pill"><span>&#10022;</span> {t.archiveEyebrow}</span>
              <h1>{t.practicedChats}</h1>
              <p>{t.historyDescription}</p>
            </div>
            <button className="clay-button primary-button history-new-button" type="button" onClick={resetInterview}>{t.newPractice} <span>&rarr;</span></button>
          </div>
          <div className="history-workspace">
            <aside className="history-list clay-card" aria-label={t.practiceSessions}>
              <div className="history-list-heading"><span>{t.yourSessions}</span><strong>{sessionHistory.length}</strong></div>
              <div className="history-filters" role="group" aria-label={t.historyFilter}>
                <button className={!historyArchived ? "active" : ""} type="button" onClick={() => void showSessions(false)} disabled={isBusy}>{t.active}</button>
                <button className={historyArchived ? "active" : ""} type="button" onClick={() => void showSessions(true)} disabled={isBusy}>{t.archived}</button>
              </div>
              {isBusy && sessionHistory.length === 0 && <p className="history-empty">{t.loadingChats}</p>}
              {!isBusy && sessionHistory.length === 0 && (
                <div className="history-empty">
                  <strong>{historyArchived ? t.noArchived : t.noPracticed}</strong>
                  <span>{historyArchived ? t.archivedHint : t.practicedHint}</span>
                </div>
              )}
              {sessionHistory.map((item) => (
                <div className={`history-item ${historySession?.session_id === item.session_id ? "selected" : ""}`} key={item.session_id}>
                  <button className="history-item-open" type="button" onClick={() => void openHistorySession(item.session_id)}>
                    <div><strong>{levelLabel(item.config.level, t)} {item.config.job_role}</strong><span>{new Date(item.created_at).toLocaleString(language === "vi" ? "vi-VN" : "en-US", { dateStyle: "medium", timeStyle: "short" })}</span></div>
                    <div className="history-item-meta"><span>{item.message_count} {t.messages}</span>{item.overall_score !== null ? <b>{item.overall_score}</b> : <b className="status-score">{sessionStatus(item.status, language)}</b>}</div>
                  </button>
                  <details className="history-item-menu">
                    <summary aria-label={`${t.actionsFor} ${item.config.job_role}`} title={t.sessionActions}>
                      <span aria-hidden="true">&#8230;</span>
                    </summary>
                    <div className="history-item-menu-popover">
                      <button type="button" onClick={() => void updateArchive(item.session_id, !historyArchived)} disabled={isBusy}>
                        {historyArchived ? t.restore : t.archive}
                      </button>
                      <button className="delete-action" type="button" onClick={() => void deleteHistorySession(item)} disabled={isBusy}>
                        {t.delete}
                      </button>
                    </div>
                  </details>
                </div>
              ))}
            </aside>
            <article className="history-chat clay-surface">
              {!historySession && <div className="history-placeholder"><div className="mini-orb orb-purple" aria-hidden="true">&#10022;</div><h2>{t.selectSession}</h2><p>{t.transcriptHint}</p></div>}
              {historySession && (
                <>
                  <div className="history-chat-heading">
                    <div><span className="step-label">{t.transcript}</span><h2>{levelLabel(historySession.config.level, t)} {historySession.config.job_role}</h2><p>{historySession.config.skills.join(" - ")}</p></div>
                    {historySession.summary && <div className="history-score"><strong>{historySession.summary.overall_score}</strong><span>/100</span></div>}
                  </div>
                  <div className="history-transcript">
                    {historySession.messages.map((message) => (
                      <article className={`message ${message.role === "assistant" ? "coach" : "you"}`} key={message.id}>
                        {message.role === "assistant" && <div className="message-avatar" aria-hidden="true">A</div>}
                        <div className="message-content">
                          <span>
                            {message.role === "assistant" ? "ARI" : t.you}
                            {message.role === "assistant" && (
                              <button
                                type="button"
                                className={`speak-button ${playingMessageId === message.id ? "is-playing" : ""}`}
                                 onClick={() => toggleSpeak(message.id, message.content, historySession.config.language)}
                                aria-label={playingMessageId === message.id ? t.stopAudio : t.playQuestion}
                                aria-pressed={playingMessageId === message.id}
                                title={playingMessageId === message.id ? t.stopAudio : t.playQuestion}
                                style={speakButtonStyle}
                              >
                                <SpeakerIcon playing={playingMessageId === message.id} />
                              </button>
                            )}
                          </span>
                          <p>{message.content}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                  <div className="history-actions">
                    {historySession.summary ? <button className="clay-button secondary-button" type="button" onClick={() => syncSession(historySession)}>{t.viewFeedback}</button> : historySession.status === "in_progress" ? <button className="clay-button primary-button" type="button" onClick={() => syncSession(historySession)}>{t.continuePractice} <span>&rarr;</span></button> : null}
                  </div>
                </>
              )}
            </article>
          </div>
        </section>
      )}

      {stage === "setup" && (
        <section className="setup-grid" id="top">
          <div className="hero-copy">
            <div className="eyebrow clay-pill"><span>&#10022;</span> {t.heroEyebrow}</div>
            <h1>{t.heroTitleBefore} <span>{t.heroTitleAccent}</span></h1>
            <p>{t.heroDescription}</p>
            <div className="trust-row" aria-label={t.productBenefits}>
              <span><b>&infin;</b> {t.practiceFreely}</span><span><b>2</b> {t.languages}</span><span><b>5 min</b> {t.toBegin}</span>
            </div>
          </div>

          <form className="setup-card clay-surface" onSubmit={beginInterview}>
            <div className="floating-note note-one clay-card" aria-hidden="true"><span>82</span><small>{t.readiness}</small></div>
            <div className="card-heading">
              <div><span className="step-label">{t.planLabel}</span><h2>{t.shapeInterview}</h2></div>
              <div className="mini-orb orb-purple" aria-hidden="true">&#10022;</div>
            </div>
            <div className="field-grid">
              <label className="field field-wide"><span>{t.targetRole}</span><input value={role} onChange={(event) => setRole(event.target.value)} required /></label>
              <label className="field"><span>{t.experienceLevel}</span><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="Junior">{t.junior}</option><option value="Mid">{t.mid}</option><option value="Senior">{t.senior}</option><option value="Lead">{t.lead}</option></select></label>
              <label className="field"><span>{t.interviewStyle}</span><select value={style} onChange={(event) => setStyle(event.target.value)}><option value="Mixed">{t.mixed}</option><option value="Technical">{t.technical}</option><option value="Behavioral">{t.behavioral}</option></select></label>
               <label className="field"><span>{t.interviewLanguage}</span><select value={practiceLanguage} onChange={(event) => setPracticeLanguage(event.target.value as UiLanguage)}><option value="en">{t.english}</option><option value="vi">{t.vietnamese}</option></select></label>
               <label className="field field-wide"><span>{t.projectContext}</span><select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}><option value="">{t.noProject}</option>{projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}</select></label>
               <label className="field field-wide"><span>{t.skillsFocus}</span><input value={skills} onChange={(event) => setSkills(event.target.value)} required /><small>{t.skillsHint}</small></label>
            </div>
            <div className="plan-preview">
              <div className="preview-orb orb-blue" aria-hidden="true">{plannedQuestionCount}</div>
              <div><strong>{t.balancedSession}</strong><span>{t.planDetails} - {practiceLanguage === "vi" ? t.vietnamese : t.english}</span></div>
            </div>
            <button className="clay-button primary-button" type="submit" disabled={isBusy}>
              {isBusy ? t.preparing : t.startInterview} <span aria-hidden="true">&rarr;</span>
            </button>
            <p className="privacy-note"><span aria-hidden="true">&#9679;</span> {t.privacy}</p>
          </form>
          <div className="floating-note note-two clay-card" aria-hidden="true"><span>&#10022;</span><small>{t.adaptive}</small></div>
        </section>
      )}

      {stage === "interview" && session && (
        <section className="workspace" id="top">
          <div className="session-banner clay-card">
            <div><span className="live-dot" /><div><small>{t.mockInterview}</small><strong>{levelLabel(level, t)} {role}</strong></div></div>
            <div className="skill-chips" aria-label={t.interviewSkills}>{session.config.skills.slice(0, 3).map((skill) => <span key={skill}>{skill}</span>)}</div>
            <button className="icon-button" type="button" onClick={resetInterview} aria-label={t.returnSetup}>&#8634;</button>
          </div>

          <aside className="progress-panel clay-card">
            <div className="progress-heading">
              <div><span>{t.yourProgress}</span><strong>{completedCount} {t.of} {totalQuestions}</strong></div>
              <div className="progress-orb" style={{ "--progress": `${progress * 3.6}deg` } as React.CSSProperties}><span>{progress}%</span></div>
            </div>
            <ol className="question-list">
              {questions.map((question) => (
                <li className={`question-row ${question.status}`} key={question.id}>
                  <span className="question-status" aria-hidden="true">{question.status === "answered" ? "✓" : question.status === "skipped" ? "-" : question.index + 1}</span>
                  <div><strong>{question.title}</strong><span>{questionCategory(question.type, question.skill_tag, language)}</span></div>
                  {question.score !== null && <b>{question.score}/5</b>}
                </li>
              ))}
            </ol>
            <div className="coach-tip"><span aria-hidden="true">&#9728;</span><p><strong>{t.coachTip}</strong>{t.coachTipText}</p></div>
          </aside>

          <div className="chat-panel clay-surface">
            <div className="chat-heading">
              <div className="coach-portrait" aria-hidden="true">A</div>
              <div><strong>{t.coachName}</strong><span><i /> {t.listening}</span></div>
              <div className="question-counter">{t.question} {(currentQuestion?.index ?? 0) + 1} / {totalQuestions}</div>
            </div>
            <div className="transcript" aria-live="polite">
              <div className="session-divider"><span>{t.todaysPractice}</span></div>
              {messages?.map((message) => {
                const linkedQuestion = questions.find((question) => question.id === message.question_id);
                return (
                  <article className={`message ${message.role === "assistant" ? "coach" : "you"}`} key={message.id}>
                    {message.role === "assistant" && <div className="message-avatar" aria-hidden="true">A</div>}
                    <div className="message-content">
                      <span>
                        {message.role === "assistant" ? "ARI" : t.you}
                        {message.role === "assistant" && (
                          <button
                            type="button"
                            className={`speak-button ${playingMessageId === message.id ? "is-playing" : ""}`}
                             onClick={() => toggleSpeak(message.id, message.content, session.config.language)}
                            aria-label={playingMessageId === message.id ? t.stopAudio : t.playQuestion}
                            aria-pressed={playingMessageId === message.id}
                            title={playingMessageId === message.id ? t.stopAudio : t.playQuestion}
                            style={speakButtonStyle}
                          >
                            <SpeakerIcon playing={playingMessageId === message.id} />
                          </button>
                        )}
                      </span>
                      {linkedQuestion && message.role === "assistant" && <small>{t.question} {linkedQuestion.index + 1} - {questionCategory(linkedQuestion.type, linkedQuestion.skill_tag, language)}</small>}
                      <p>{message.content}</p>
                    </div>
                  </article>
                );
              })}
              {isBusy && <div className="message coach thinking" aria-label={t.ariThinking}><div className="message-avatar" aria-hidden="true">A</div><div className="typing-bubble"><i /><i /><i /></div></div>}
              <div ref={transcriptEnd} />
            </div>

            <div className="composer-wrap">
              <label className="sr-only" htmlFor="answer">{t.yourAnswer}</label>
              <textarea id="answer" value={answer} onChange={(event) => setAnswer(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder={t.shareAnswer} readOnly={session.config.mode === "conversation"} disabled={isBusy} rows={3} />
              <div className="composer-actions">
                <span>{voiceStatus === "speaking" ? t.voiceSpeaking : voiceStatus === "listening" || voiceStatus === "transcribing" ? t.voiceListening : voiceStatus === "processing" || voiceStatus === "submitting" ? t.voiceProcessing : t.sendHint}</span>
                <div>
                  <button className="text-button" type="button" onClick={() => void toggleConversationMode()} disabled={isBusy} aria-pressed={session.config.mode === "conversation"}>{session.config.mode === "conversation" ? t.disableConversation : t.enableConversation}</button>
                  <button className={`text-button ${isListening ? "is-active" : ""}`} type="button" onClick={toggleListening} disabled={isBusy} aria-pressed={isListening}>{isListening ? t.stopListening : voiceStatus === "speaking" ? t.interruptAndListen : t.speakAnswer}</button>
                  <button className="text-button" type="button" onClick={() => void skipQuestion()} disabled={isBusy}>{t.skip}</button>
                  {session.config.mode !== "conversation" && <button className="clay-button send-button" type="button" onClick={() => void submitAnswer()} disabled={!answer.trim() || isBusy} aria-label={t.sendAnswer}>{t.send} <b aria-hidden="true">&uarr;</b></button>}
                </div>
              </div>
            </div>
          </div>

          <div className="session-footer">
            <p><span aria-hidden="true">&#9679;</span> {t.savedAutomatically}</p>
            <button className="end-button" type="button" onClick={() => void finalizeInterview()} disabled={isBusy}>{t.endInterview}</button>
          </div>
        </section>
      )}

      {stage === "summary" && session && summary && (
        <section className="summary-layout" id="top">
          <div className="summary-hero clay-surface">
            <div className="celebration" aria-hidden="true"><span>&#10022;</span><span>&#9679;</span><span>&#10022;</span></div>
            <div className="score-orb"><strong>{summary.overall_score}</strong><span>/ 100</span></div>
            <span className="readiness-badge">{readinessLabel(summary.readiness, t)}</span>
            <h1>{t.practiceComplete}</h1>
            <p>{summary.summary_text}</p>
            <div className="summary-actions">
              <button className="clay-button primary-button" type="button" onClick={resetInterview}>{t.practiceAgain} <span>&#8599;</span></button>
              <button className="clay-button secondary-button" type="button" onClick={exportFeedback}>{t.exportFeedback}</button>
            </div>
          </div>

          <div className="feedback-grid">
            <article className="feedback-card clay-card strengths-card">
              <div className="feedback-icon orb-green" aria-hidden="true">&#10003;</div><span className="step-label">{t.whatWorked}</span><h2>{t.strengths}</h2>
              <ul>{summary.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
            <article className="feedback-card clay-card growth-card">
              <div className="feedback-icon orb-amber" aria-hidden="true">&#8599;</div><span className="step-label">{t.nextLevel}</span><h2>{t.focusAreas}</h2>
              <ul>{summary.improvements.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
            <article className="competency-card clay-card">
              <div className="card-heading"><div><span className="step-label">{t.competencyMap}</span><h2>{t.howYouShowedUp}</h2></div><span className="mini-orb orb-pink">&#10022;</span></div>
              {summary.competencies.map((competency) => {
                const percent = competency.score * 20;
                return <div className="skill-meter" key={competency.name}><div><span>{competency.name}</span><strong>{percent}%</strong></div><div className="meter-track"><i style={{ width: `${percent}%` }} /></div></div>;
              })}
            </article>
          </div>
          <p className="coaching-disclaimer">{t.disclaimer}</p>
        </section>
      )}
    </main>
  );
}
