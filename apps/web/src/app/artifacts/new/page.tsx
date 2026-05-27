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
            <span className="text-neutral-500">Type</span>
            <select
              value={type}
              onChange={(e) => onTypeChange(e.target.value as ArtifactType)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            >
              {ARTIFACT_TYPE_ORDER.map((t) => (
                <option key={t} value={t}>
                  {ARTIFACT_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-neutral-500">Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ArtifactStatus)}
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
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
          <span className="text-neutral-500">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Short, descriptive title"
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="text-neutral-500">Content</span>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            placeholder="The body of the artifact…"
            className="w-full resize-y rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="text-neutral-500">Source (optional)</span>
          <input
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            placeholder="e.g. interview, project_description, parent artifact id"
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
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
