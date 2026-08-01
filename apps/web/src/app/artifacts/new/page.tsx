"use client";

import type { JSONContent } from "@tiptap/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { RichTextEditor } from "@/components/editor/RichTextEditor";
import { Popover } from "@/components/overlay/Popover";
import { Button } from "@/components/ui";
import { EMPTY_DOC, serializeDoc } from "@/lib/editor/content";
import { useCreateArtifact } from "@/lib/queries";
import {
  ARTIFACT_TYPE_COLOR,
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
  const [doc, setDoc] = useState<JSONContent>(EMPTY_DOC);
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
        content: serializeDoc(doc),
        status,
        source_ref: sourceRef.trim() || null,
      },
      { onSuccess: (a) => router.push(`/artifacts/${a.id}`) },
    );
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-8 lg:px-16">
      <div className="flex items-center gap-2 text-xs text-ink-faint">
        <Link href="/artifacts" className="hover:text-ink hover:underline">
          Artifacts
        </Link>
        <span aria-hidden>/</span>
        <span className="text-ink-mute">New</span>
      </div>

      <header className="mt-7 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <TypeControl type={type} onChange={onTypeChange} />
            <StatusControl type={type} status={status} onChange={setStatus} />
          </div>
          <textarea
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            rows={1}
            placeholder="Untitled"
            autoFocus
            ref={(el) => {
              if (!el) return;
              el.style.height = "auto";
              el.style.height = `${el.scrollHeight}px`;
            }}
            className="w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-[2.125rem] font-bold leading-tight tracking-tight text-ink outline-none placeholder:text-ink-ghost"
          />
          <SourceField value={sourceRef} onChange={setSourceRef} />
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Button onClick={submit} disabled={create.isPending || !title.trim()}>
            {create.isPending ? "Creating…" : "Create artifact"}
          </Button>
          <Button variant="secondary" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </header>

      {create.isError && (
        <p className="mt-3 text-xs text-red-500">Creation failed.</p>
      )}

      <div className="mt-8 border-t border-hairline pt-7">
        <RichTextEditor value="" editable onChange={setDoc} />
      </div>
    </div>
  );
}

function TypeControl({
  type,
  onChange,
}: {
  type: ArtifactType;
  onChange: (t: ArtifactType) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full bg-canvas-soft px-2.5 py-1 text-xs font-medium text-ink-mute ring-1 ring-inset ring-hairline transition-colors hover:bg-canvas hover:text-ink"
      >
        <span className="size-1.5 rounded-full" style={{ background: ARTIFACT_TYPE_COLOR[type] }} />
        {ARTIFACT_TYPE_LABEL[type]}
        <svg
          viewBox="0 0 12 12"
          aria-hidden
          className={`size-3 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        containerRef={ref}
        className="absolute left-0 z-20 mt-1.5 w-56 rounded-lg border border-hairline bg-canvas p-1.5 shadow-float"
      >
        <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Type
        </p>
        {ARTIFACT_TYPE_ORDER.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => {
              onChange(t);
              setOpen(false);
            }}
            className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
              t === type
                ? "bg-canvas-soft text-ink"
                : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
            }`}
          >
            <span className="size-1.5 rounded-full" style={{ background: ARTIFACT_TYPE_COLOR[t] }} />
            <span>{ARTIFACT_TYPE_LABEL[t]}</span>
            {t === type && (
              <svg viewBox="0 0 12 12" aria-hidden className="ml-auto size-3.5 text-primary-deep">
                <path
                  d="M2.5 6.5 5 9l4.5-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        ))}
      </Popover>
    </div>
  );
}

function StatusControl({
  type,
  status,
  onChange,
}: {
  type: ArtifactType;
  status: ArtifactStatus;
  onChange: (s: ArtifactStatus) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full bg-canvas-soft px-2.5 py-1 text-xs font-medium capitalize text-ink-mute ring-1 ring-inset ring-hairline transition-colors hover:bg-canvas hover:text-ink"
      >
        <span className="size-1.5 rounded-full bg-ink-faint" />
        {status.replace("_", " ")}
        <svg
          viewBox="0 0 12 12"
          aria-hidden
          className={`size-3 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        containerRef={ref}
        className="absolute left-0 z-20 mt-1.5 w-56 rounded-lg border border-hairline bg-canvas p-1.5 shadow-float"
      >
        <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Status
        </p>
        {STATUSES_FOR_TYPE[type].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => {
              onChange(s);
              setOpen(false);
            }}
            className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm capitalize transition-colors ${
              s === status
                ? "bg-canvas-soft text-ink"
                : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
            }`}
          >
            <span>{s.replace("_", " ")}</span>
            {s === status && (
              <svg viewBox="0 0 12 12" aria-hidden className="size-3.5 text-primary-deep">
                <path
                  d="M2.5 6.5 5 9l4.5-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        ))}
      </Popover>
    </div>
  );
}

function SourceField({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-faint">
      <svg viewBox="0 0 16 16" aria-hidden className="size-3.5 shrink-0">
        <path
          d="M6.5 9.5 9.5 6.5M5.4 4.2 6.8 2.8a3 3 0 0 1 4.4 4.4l-1.4 1.4M10.6 11.8l-1.4 1.4a3 3 0 0 1-4.4-4.4l1.4-1.4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Add a source — interview, project_description, parent id…"
        className="w-full max-w-md border-0 bg-transparent p-0 text-sm text-ink-secondary outline-none placeholder:text-ink-faint"
      />
    </div>
  );
}
