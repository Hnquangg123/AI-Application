"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { Project, ProjectSection, ProjectSectionBlock, projectApi } from "../../../lib/api";
import { getTranslations, UiLanguage } from "../../../lib/i18n";

function message(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function ProjectDocumentationPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const [language, setLanguage] = useState<UiLanguage>("en");
  const [project, setProject] = useState<Project | null>(null);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [sectionEditorOpen, setSectionEditorOpen] = useState(false);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [sectionTitle, setSectionTitle] = useState("");
  const [sectionSlug, setSectionSlug] = useState("");
  const [sectionBlocks, setSectionBlocks] = useState<ProjectSectionBlock[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = getTranslations(language);

  function openSection(section: ProjectSection) {
    setSectionEditorOpen(true);
    setEditingSectionId(section.id);
    setSectionTitle(section.title);
    setSectionSlug(section.slug);
    setSectionBlocks(section.content.blocks.map((block) => ({ ...block })));
  }

  function applyProject(next: Project, preferredSectionId?: string | null) {
    setProject(next);
    setProjectName(next.name);
    setProjectDescription(next.description);
    const section = next.sections.find((item) => item.id === preferredSectionId)
      ?? next.sections.find((item) => item.id === editingSectionId)
      ?? next.sections[0];
    if (section) openSection(section);
    else {
      setSectionEditorOpen(false);
      setEditingSectionId(null);
    }
  }

  useEffect(() => {
    const saved = window.localStorage.getItem("mockmate.language");
    const frame = window.requestAnimationFrame(() => setLanguage(saved === "vi" ? "vi" : "en"));
    projectApi.get(projectId)
      .then((next) => {
        setProject(next);
        setProjectName(next.name);
        setProjectDescription(next.description);
        if (next.sections[0]) openSection(next.sections[0]);
      })
      .catch((requestError) => setError(message(requestError, "Could not load this project.")));
    return () => window.cancelAnimationFrame(frame);
  }, [projectId]);

  function createPage() {
    setSectionEditorOpen(true);
    setEditingSectionId(null);
    setSectionTitle("");
    setSectionSlug("");
    setSectionBlocks([{ type: "text", value: "" }]);
  }

  function updateBlock(index: number, update: Partial<ProjectSectionBlock>) {
    setSectionBlocks((current) => current.map((block, blockIndex) =>
      blockIndex === index ? { ...block, ...update } : block,
    ));
  }

  function addImage(event: React.ChangeEvent<HTMLInputElement>) {
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

  async function saveProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !projectName.trim()) return;
    setIsBusy(true);
    setError(null);
    try {
      const saved = await projectApi.update(project.id, projectName.trim(), projectDescription.trim());
      applyProject(saved, editingSectionId);
    } catch (requestError) {
      setError(message(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function savePage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !sectionTitle.trim()) return;
    setIsBusy(true);
    setError(null);
    try {
      const payload = {
        title: sectionTitle.trim(),
        slug: sectionSlug.trim() || undefined,
        sort_order: editingSectionId
          ? project.sections.find((section) => section.id === editingSectionId)?.sort_order ?? project.sections.length
          : project.sections.length,
        content: { blocks: sectionBlocks.filter((block) => block.value.trim()) },
      };
      const saved = editingSectionId
        ? await projectApi.updateSection(project.id, editingSectionId, payload)
        : await projectApi.createSection(project.id, payload);
      applyProject(await projectApi.get(project.id), saved.id);
    } catch (requestError) {
      setError(message(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function deletePage() {
    if (!project || !editingSectionId) return;
    const section = project.sections.find((item) => item.id === editingSectionId);
    if (!section || !window.confirm(`${t.deletePageConfirm} ${section.title}?`)) return;
    setIsBusy(true);
    setError(null);
    try {
      await projectApi.deleteSection(project.id, section.id);
      applyProject(await projectApi.get(project.id));
    } catch (requestError) {
      setError(message(requestError, t.genericError));
    } finally {
      setIsBusy(false);
    }
  }

  async function buildRag() {
    if (!project || project.sections.length === 0 || isIndexing) return;
    setIsIndexing(true);
    setError(null);
    try {
      await projectApi.reindex(project.id);
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const updated = await projectApi.get(project.id);
        applyProject(updated, editingSectionId);
        if (!updated.sections.every((section) => ["ready", "failed"].includes(section.indexing_status))) continue;
        if (updated.sections.some((section) => section.indexing_status === "failed")) setError(t.ragFailed);
        return;
      }
      setError(t.ragStillProcessing);
    } catch (requestError) {
      setError(message(requestError, t.genericError));
    } finally {
      setIsIndexing(false);
    }
  }

  if (!project) {
    return <main className="project-doc-page"><div className="project-doc-loading">{error ?? "Loading project..."}</div></main>;
  }

  const activeSection = project.sections.find((section) => section.id === editingSectionId);
  const readyPages = project.sections.filter((section) => section.indexing_status === "ready").length;
  const vectorChunks = project.data.filter((item) => item.project_section_id).length;

  return (
    <main className="project-doc-page">
      <header className="project-doc-header">
        <div className="project-doc-brand"><Link href="/?view=projects" aria-label={language === "vi" ? "Quay lại danh sách project" : "Back to projects"}>&larr;</Link><div><span>MockMate Knowledge</span><strong>{project.name}</strong></div></div>
        <div className="project-doc-header-actions"><span>{readyPages}/{project.sections.length} {t.pagesReady}</span><button className="clay-button primary-button" type="button" onClick={() => void buildRag()} disabled={isIndexing || project.sections.length === 0}>{isIndexing ? t.buildingRag : t.buildRag}</button></div>
      </header>

      {error && <div className="api-error project-doc-error" role="alert"><span>{error}</span><button type="button" onClick={() => setError(null)}>x</button></div>}

      <div className="project-doc-layout">
        <aside className="project-doc-sidebar">
          <div className="project-doc-summary"><span className="step-label">PROJECT</span><h1>{project.name}</h1><p>{project.description}</p></div>
          <div className="project-doc-nav-heading"><span>{t.projectPages}</span><button type="button" onClick={createPage}>+</button></div>
          <nav aria-label={t.projectPages}>
            {project.sections.map((section) => <button className={editingSectionId === section.id ? "active" : ""} type="button" key={section.id} onClick={() => openSection(section)}><span>{section.title}</span><small className={`index-status ${section.indexing_status}`}>{section.indexing_status}</small></button>)}
          </nav>
          {project.sections.length === 0 && <p className="docs-empty">{t.noPages}</p>}
          <div className="project-doc-index"><span>{vectorChunks} {t.vectorChunks}</span><span>{readyPages}/{project.sections.length} {t.pagesReady}</span></div>
          <details className="project-doc-settings">
            <summary>{t.editProject}</summary>
            <form onSubmit={saveProject}>
              <label className="field"><span>{t.projectName}</span><input value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label>
              <label className="field"><span>{t.projectDescription}</span><textarea rows={4} value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} /></label>
              <button className="clay-button secondary-button" type="submit" disabled={isBusy}>{t.saveProject}</button>
            </form>
          </details>
        </aside>

        <section className="project-doc-content">
          {!sectionEditorOpen && <div className="project-doc-empty"><span>&#10022;</span><h2>{t.selectPage}</h2><p>{t.selectPageHint}</p><button className="clay-button primary-button" type="button" onClick={createPage}>{t.newPage}</button></div>}
          {sectionEditorOpen && <form className="project-page-editor" onSubmit={savePage}>
            <div className="project-page-breadcrumb"><span>{project.name}</span><b>/</b><span>{sectionSlug || "new-page"}</span></div>
            <div className="project-page-title-row"><div><span className="step-label">{editingSectionId ? t.editPage : t.newPage}</span><h2>{sectionTitle || t.untitledPage}</h2></div>{activeSection && <small className={`index-status ${activeSection.indexing_status}`}>{activeSection.indexing_status}</small>}</div>
            <div className="section-fields"><label className="field"><span>{t.pageTitle}</span><input value={sectionTitle} onChange={(event) => setSectionTitle(event.target.value)} required /></label><label className="field"><span>{t.pageSlug}</span><input value={sectionSlug} onChange={(event) => setSectionSlug(event.target.value)} placeholder={t.pageSlugHint} /></label></div>
            <div className="content-blocks">
              {sectionBlocks.map((block, index) => <div className={`content-block ${block.type}`} key={`${block.type}-${index}`}><div className="content-block-heading"><strong>{block.type === "text" ? t.textBlock : t.imageBlock}</strong><button type="button" onClick={() => setSectionBlocks((current) => current.filter((_, blockIndex) => blockIndex !== index))}>{t.removeBlock}</button></div>{block.type === "text" ? <textarea rows={12} value={block.value} onChange={(event) => updateBlock(index, { value: event.target.value })} placeholder={t.textContentHint} /> : <><Image src={block.value} alt={block.caption || t.imageBlock} width={1400} height={800} unoptimized /><label className="field"><span>{t.imageCaption}</span><input value={block.caption ?? ""} onChange={(event) => updateBlock(index, { caption: event.target.value })} /></label></>}</div>)}
            </div>
            <div className="block-toolbar"><button className="clay-button secondary-button" type="button" onClick={() => setSectionBlocks((current) => [...current, { type: "text", value: "" }])}>+ {t.addTextBlock}</button><label className="clay-button secondary-button file-button">+ {t.addImageBlock}<input type="file" accept="image/png,image/jpeg,image/webp" onChange={addImage} /></label></div>
            <div className="section-actions"><button className="clay-button primary-button" type="submit" disabled={isBusy || !sectionTitle.trim()}>{isBusy ? t.savingPage : t.savePage}</button>{editingSectionId && <button className="clay-button secondary-button danger-button" type="button" onClick={() => void deletePage()} disabled={isBusy}>{t.deletePage}</button>}</div>
            {activeSection?.indexing_error && <p className="section-index-error">{activeSection.indexing_error}</p>}
          </form>}
        </section>
      </div>
    </main>
  );
}
