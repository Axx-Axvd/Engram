"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, PageHeader } from "@/components/ui";
import { useCreateArtifact } from "@/lib/queries";
import {
  ARTIFACT_TYPE_LABEL,
  ARTIFACT_TYPE_ORDER,
  type ArtifactStatus,
  type ArtifactType,
  STATUSES_FOR_TYPE,
} from "@/lib/types";

const FIELD =
  "w-full rounded-md border border-hairline-strong bg-canvas px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20";

export default function NewArtifactPage() {
  const router = useRouter();
  const create = useCreateArtifact();

  const [type, setType] = useState<ArtifactType>("requirement");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<ArtifactStatus>("draft");
  const [sourceRef, setSourceRef] = useState("");

  function onTypeChange(next: ArtifactType) {
    setType(next);
    setStatus(STATUSES_FOR_TYPE[next][0]);
  }

  function submit() {
    create.mutate(
      {
        type,
        title: title.trim(),
        content,
        status,
        source_ref: sourceRef.trim() || null,
      },
      { onSuccess: (a) => router.push(`/artifacts/${a.id}`) },
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5 p-6">
      <PageHeader title="New artifact" description="Author a piece of project memory by hand." />

      <Card className="space-y-4 p-5">
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1 text-sm">
            <span className="text-ink-mute">Type</span>
            <select value={type} onChange={(e) => onTypeChange(e.target.value as ArtifactType)} className={FIELD}>
              {ARTIFACT_TYPE_ORDER.map((t) => (
                <option key={t} value={t}>
                  {ARTIFACT_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-ink-mute">Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ArtifactStatus)}
              className={FIELD}
            >
              {STATUSES_FOR_TYPE[type].map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block space-y-1 text-sm">
          <span className="text-ink-mute">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Short, descriptive title"
            className={FIELD}
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="text-ink-mute">Content</span>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            placeholder="The body of the artifact…"
            className={`${FIELD} resize-y`}
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="text-ink-mute">Source (optional)</span>
          <input
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            placeholder="e.g. interview, project_description, parent artifact id"
            className={FIELD}
          />
        </label>

        <div className="flex items-center gap-2">
          <Button onClick={submit} disabled={create.isPending || !title.trim()}>
            {create.isPending ? "Creating…" : "Create artifact"}
          </Button>
          <Button variant="secondary" onClick={() => router.back()}>
            Cancel
          </Button>
          {create.isError && <span className="text-xs text-red-500">Creation failed.</span>}
        </div>
      </Card>
    </div>
  );
}
