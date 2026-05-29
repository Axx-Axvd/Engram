"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useMemo, useRef, useState } from "react";

import type { JSONContent } from "@tiptap/react";

import { RichTextEditor } from "@/components/editor/RichTextEditor";
import { Popover } from "@/components/overlay/Popover";
import { SidePanel } from "@/components/overlay/SidePanel";
import { Button, Card, Spinner, StatusBadge, TypeBadge } from "@/components/ui";
import { EMPTY_DOC, parseDocContent, serializeDoc } from "@/lib/editor/content";
import { formatDateTime } from "@/lib/format";
import {
  useArtifact,
  useArtifactLinks,
  useArtifactVersions,
  useArtifacts,
  useCreateLink,
  useUpdateArtifact,
} from "@/lib/queries";
import {
  ARTIFACT_TYPE_COLOR,
  ARTIFACT_TYPE_LABEL,
  type Artifact,
  type ArtifactItem,
  type ArtifactStatus,
  type ArtifactType,
  LINK_TYPES,
  type LinkType,
  STATUSES_FOR_TYPE,
} from "@/lib/types";

type Tab = "content" | "links" | "history";

export default function ArtifactPage() {
  const { id } = useParams<{ id: string }>();
  const artifact = useArtifact(id);
  const update = useUpdateArtifact(id);

  const [tab, setTab] = useState<Tab>("content");
  const [editing, setEditing] = useState(false);
  const [showItems, setShowItems] = useState(false);
  const [title, setTitle] = useState("");
  const [doc, setDoc] = useState<JSONContent>(EMPTY_DOC);
  const [status, setStatus] = useState<ArtifactStatus>("draft");
  const [reason, setReason] = useState("");

  if (artifact.isLoading) {
    return (
      <div className="p-8">
        <Spinner label="Loading artifact…" />
      </div>
    );
  }
  if (artifact.isError || !artifact.data) {
    return (
      <div className="mx-auto max-w-3xl p-8">
        <p className="text-sm text-red-500">Artifact not found.</p>
        <Link
          href="/artifacts"
          className="text-sm text-ink-secondary underline-offset-2 hover:text-primary-deep hover:underline"
        >
          ← Back to artifacts
        </Link>
      </div>
    );
  }

  const a = artifact.data;
  const items = a.items ?? [];
  const hasItems = items.length > 0;

  function startEdit() {
    setTitle(a.title);
    setDoc(parseDocContent(a.content));
    setStatus(a.status);
    setReason("");
    setShowItems(false);
    setEditing(true);
  }

  function save() {
    update.mutate(
      { title, content: serializeDoc(doc), status, reason: reason || null },
      { onSuccess: () => setEditing(false) },
    );
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] px-8 py-8 lg:px-16">
      <div className="flex items-center gap-2 text-xs text-ink-faint">
        <Link href="/artifacts" className="hover:text-ink hover:underline">
          Artifacts
        </Link>
      </div>

      <header className="mt-7 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <TypeBadge type={a.type} />
            <StatusBadge status={editing ? status : a.status} />
            <span className="text-xs text-ink-faint">v{a.current_version}</span>
            <MetaPopover artifact={a} />
          </div>
          {editing ? (
            <textarea
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              rows={1}
              placeholder="Untitled"
              ref={(el) => {
                if (!el) return;
                el.style.height = "auto";
                el.style.height = `${el.scrollHeight}px`;
              }}
              className="w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-[2.125rem] font-bold leading-tight tracking-tight text-ink outline-none placeholder:text-ink-ghost"
            />
          ) : (
            <h1 className="text-[2.125rem] font-bold leading-tight tracking-tight break-words text-ink">
              {a.title}
            </h1>
          )}
        </div>

        {tab === "content" && (
          <div className="flex shrink-0 items-center gap-2">
            {editing ? (
              <>
                <Button onClick={save} disabled={update.isPending || !title.trim()}>
                  {update.isPending ? "Saving…" : "Save"}
                </Button>
                <StatusControl
                  type={a.type}
                  status={status}
                  reason={reason}
                  onStatusChange={setStatus}
                  onReasonChange={setReason}
                />
                {update.isError && <span className="text-xs text-red-500">Save failed.</span>}
                <Button variant="secondary" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                {hasItems && (
                  <Button variant="secondary" onClick={() => setShowItems((v) => !v)}>
                    {showItems ? "Hide items" : `Items (${items.length})`}
                  </Button>
                )}
                <Button variant="secondary" onClick={startEdit}>
                  Edit
                </Button>
              </>
            )}
          </div>
        )}
      </header>

      {!editing && (
        <div className="mt-5 flex gap-1 border-b border-hairline">
          {(["content", "links", "history"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium capitalize transition-colors ${
                tab === t
                  ? "border-primary text-ink"
                  : "border-transparent text-ink-mute hover:text-ink"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {tab === "content" && (
        <div className="mt-7 flex flex-col gap-10 lg:flex-row lg:items-start">
          <div className="min-w-0 flex-1">
            {editing ? (
              <RichTextEditor key="editor-edit" value={a.content} editable onChange={setDoc} />
            ) : a.content ? (
              <RichTextEditor key="editor-read" value={a.content} editable={false} />
            ) : (
              <button
                type="button"
                onClick={startEdit}
                className="text-sm text-ink-faint hover:text-ink"
              >
                Empty document — click to add content →
              </button>
            )}
          </div>

          <SidePanel
            open={!editing && showItems && hasItems}
            className="w-full shrink-0 space-y-2 lg:sticky lg:top-4 lg:w-72"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                Items
              </p>
              <button
                type="button"
                onClick={() => setShowItems(false)}
                className="text-xs text-ink-faint hover:text-ink"
              >
                Hide
              </button>
            </div>
            <ItemsSection items={items} />
          </SidePanel>
        </div>
      )}

      {tab === "links" && (
        <div className="mt-7 max-w-3xl">
          <LinksTab artifactId={a.id} />
        </div>
      )}
      {tab === "history" && (
        <div className="mt-7 max-w-3xl">
          <HistoryTab artifactId={a.id} />
        </div>
      )}
    </div>
  );
}

function MetaPopover({ artifact }: { artifact: Artifact }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded px-1.5 py-0.5 text-xs text-ink-faint transition-colors hover:bg-canvas-soft hover:text-ink"
      >
        Updated {formatDateTime(artifact.updated_at)}
      </button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        containerRef={ref}
        role="dialog"
        className="absolute left-0 z-20 mt-1.5 w-72 rounded-lg border border-hairline bg-canvas p-3 shadow-float"
      >
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-ink-faint">Source</dt>
          <dd className="truncate text-ink">{artifact.source_ref ?? "—"}</dd>
          <dt className="text-ink-faint">Created</dt>
          <dd className="text-ink">
            {formatDateTime(artifact.created_at)} · {artifact.created_by}
          </dd>
          <dt className="text-ink-faint">Updated</dt>
          <dd className="text-ink">
            {formatDateTime(artifact.updated_at)} · {artifact.updated_by}
          </dd>
        </dl>
      </Popover>
    </div>
  );
}

function StatusControl({
  type,
  status,
  reason,
  onStatusChange,
  onReasonChange,
}: {
  type: ArtifactType;
  status: ArtifactStatus;
  reason: string;
  onStatusChange: (s: ArtifactStatus) => void;
  onReasonChange: (r: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const needsReason = status !== "approved";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 rounded-md border border-hairline-strong bg-canvas px-3 py-2 text-sm font-medium text-ink transition-colors hover:bg-canvas-soft"
      >
        <span className="capitalize">{status.replace("_", " ")}</span>
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
        align="end"
        className="absolute right-0 z-20 mt-1.5 w-64 rounded-lg border border-hairline bg-canvas p-1.5 shadow-float"
      >
        <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Status
        </p>
        {STATUSES_FOR_TYPE[type].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onStatusChange(s)}
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
          {needsReason && (
            <div className="mt-1.5 border-t border-hairline-cool px-1 pb-1 pt-2">
              <label className="mb-1 block px-1 text-xs font-medium text-ink-faint">
                Reason for change
              </label>
              <input
                value={reason}
                onChange={(e) => onReasonChange(e.target.value)}
                placeholder="Why this change?"
                className="w-full rounded-md border border-hairline-strong bg-canvas px-2.5 py-1.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
          )}
      </Popover>
    </div>
  );
}

function LinksTab({ artifactId }: { artifactId: string }) {
  const links = useArtifactLinks(artifactId);
  const { data: allArtifacts = [] } = useArtifacts();
  const createLink = useCreateLink();

  const nameOf = useMemo(() => {
    const map = new Map(allArtifacts.map((a) => [a.id, a]));
    return (id: string) => map.get(id);
  }, [allArtifacts]);

  const [targetId, setTargetId] = useState("");
  const [type, setType] = useState<LinkType>("related_to");

  const candidates = allArtifacts.filter((a) => a.id !== artifactId);

  function add() {
    if (!targetId) return;
    createLink.mutate(
      { source_id: artifactId, target_id: targetId, type },
      { onSuccess: () => setTargetId("") },
    );
  }

  return (
    <div className="space-y-4">
      {links.isLoading && <Spinner />}
      {links.data && links.data.length === 0 && (
        <p className="text-sm text-ink-faint">No links yet.</p>
      )}
      {links.data && links.data.length > 0 && (
        <ul className="-mx-3 flex flex-col">
          {links.data.map((l) => {
            const outgoing = l.source_id === artifactId;
            const other = nameOf(outgoing ? l.target_id : l.source_id);
            if (!other) return null;
            return (
              <li key={l.id}>
                <Link
                  href={`/artifacts/${other.id}`}
                  className="group flex items-center gap-2.5 rounded-lg px-3 py-2 transition-colors hover:bg-canvas-soft"
                >
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: ARTIFACT_TYPE_COLOR[other.type] }}
                    aria-hidden
                  />
                  <span className="min-w-0 truncate text-sm font-medium text-ink">
                    {other.title}
                  </span>
                  <span className="shrink-0 rounded bg-canvas-soft px-1.5 py-0.5 text-[11px] font-medium text-ink-mute ring-1 ring-inset ring-hairline-cool transition-colors group-hover:bg-canvas group-hover:text-ink-secondary">
                    {l.type.replace("_", " ")}
                  </span>
                  <svg
                    viewBox="0 0 12 12"
                    aria-hidden
                    className="ml-auto size-3.5 shrink-0 -translate-x-1 text-ink-faint opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
                  >
                    <path
                      d="M2.5 6h7M6.5 3l3 3-3 3"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <div className="rounded-xl border border-hairline bg-canvas-soft p-5 shadow-card">
        <div className="mb-4 flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary-deep">
            <svg viewBox="0 0 20 20" aria-hidden className="size-5">
              <path
                d="M8.5 11.5 11.5 8.5M7.4 6.2 8.8 4.8a3 3 0 0 1 4.4 4.4l-1.4 1.4M12.6 13.8l-1.4 1.4a3 3 0 0 1-4.4-4.4l1.4-1.4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">Add link</p>
            <p className="text-xs text-ink-faint">Connect this document to a related artifact.</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <RelationDropdown value={type} onChange={setType} />
          <TargetCombobox candidates={candidates} value={targetId} onChange={setTargetId} />
          <Button
            onClick={add}
            disabled={!targetId || createLink.isPending}
            className="h-10 shrink-0"
          >
            {createLink.isPending ? (
              "Linking…"
            ) : (
              <>
                Link
                <svg viewBox="0 0 12 12" aria-hidden className="size-3.5">
                  <path
                    d="M2.5 6h7M6.5 3l3 3-3 3"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </>
            )}
          </Button>
        </div>
        {createLink.isError && (
          <p className="mt-2.5 text-xs text-red-500">
            Could not create link (duplicate or invalid).
          </p>
        )}
      </div>
    </div>
  );
}

function RelationDropdown({
  value,
  onChange,
}: {
  value: LinkType;
  onChange: (t: LinkType) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-hairline-strong bg-canvas px-3 text-sm font-medium capitalize text-ink transition-colors hover:bg-canvas-soft sm:w-40"
      >
        <span>{value.replace("_", " ")}</span>
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
          Relationship
        </p>
        {LINK_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => {
                onChange(t);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm capitalize transition-colors ${
                t === value
                  ? "bg-canvas-soft text-ink"
                  : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
              }`}
            >
              <span>{t.replace("_", " ")}</span>
              {t === value && (
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

function TargetCombobox({
  candidates,
  value,
  onChange,
}: {
  candidates: Artifact[];
  value: string;
  onChange: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // Focus the search box when it mounts. Popover defers mount by a frame, so a
  // plain `[open]` effect would run before the input exists; a callback ref
  // fires exactly when the node attaches.
  const focusInput = useCallback((el: HTMLInputElement | null) => el?.focus(), []);

  // Clear the search when closed (set-state-during-render, guarded so it can't loop).
  if (!open && query !== "") setQuery("");

  const selected = candidates.find((c) => c.id === value);
  const q = query.trim().toLowerCase();
  const filtered = q
    ? candidates.filter((c) => c.title.toLowerCase().includes(q))
    : candidates;

  return (
    <div ref={ref} className="relative flex-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-hairline-strong bg-canvas px-3 text-sm transition-colors hover:bg-canvas-soft"
      >
        {selected ? (
          <span className="flex min-w-0 items-center gap-2">
            <span
              className="size-1.5 shrink-0 rounded-full"
              style={{ background: ARTIFACT_TYPE_COLOR[selected.type] }}
            />
            <span className="truncate text-ink">{selected.title}</span>
          </span>
        ) : (
          <span className="text-ink-faint">Select target artifact…</span>
        )}
        <svg
          viewBox="0 0 12 12"
          aria-hidden
          className={`size-3 shrink-0 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        containerRef={ref}
        role="dialog"
        className="absolute left-0 right-0 z-20 mt-1.5 rounded-lg border border-hairline bg-canvas p-1.5 shadow-float"
      >
        <div className="relative mb-1">
          <svg
            viewBox="0 0 16 16"
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-faint"
          >
            <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="m10.5 10.5 3 3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            ref={focusInput}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search artifacts…"
            className="w-full rounded-md border border-hairline-strong bg-canvas py-1.5 pl-8 pr-2.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="max-h-64 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="px-2 py-3 text-center text-sm text-ink-faint">No matches.</p>
          ) : (
            filtered.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    onChange(c.id);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    c.id === value
                      ? "bg-canvas-soft text-ink"
                      : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
                  }`}
                >
                  <span
                    className="size-1.5 shrink-0 rounded-full"
                    style={{ background: ARTIFACT_TYPE_COLOR[c.type] }}
                  />
                  <span className="truncate">{c.title}</span>
                  <span className="ml-auto shrink-0 text-xs text-ink-faint">
                    {ARTIFACT_TYPE_LABEL[c.type]}
                  </span>
                </button>
              ))
          )}
        </div>
      </Popover>
    </div>
  );
}

function ItemsSection({ items }: { items: ArtifactItem[] }) {
  const groups = new Map<string, ArtifactItem[]>();
  for (const item of items) {
    const feature = item.feature ?? "General";
    (groups.get(feature) ?? groups.set(feature, []).get(feature)!).push(item);
  }

  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([feature, groupItems]) => (
        <div key={feature}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-faint">
            {feature}
          </p>
          <Card className="divide-y divide-hairline-cool">
            {groupItems.map((item) => (
              <div key={item.key} className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-canvas-soft px-1.5 py-0.5 font-mono text-xs font-medium text-ink-secondary ring-1 ring-inset ring-hairline">
                    {item.key}
                  </span>
                  <span className="text-sm font-medium text-ink">{item.title}</span>
                </div>
                {item.text && (
                  <p className="mt-1 text-sm text-ink-mute">{item.text}</p>
                )}
                {item.refs && item.refs.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {item.refs.map((ref, idx) => (
                      <Link
                        key={`${ref.artifact_id}-${ref.key}-${idx}`}
                        href={`/artifacts/${ref.artifact_id}`}
                        className="rounded bg-canvas-soft px-1.5 py-0.5 font-mono text-xs text-ink-mute ring-1 ring-inset ring-hairline transition-colors hover:text-primary-deep"
                      >
                        → {ref.key}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </Card>
        </div>
      ))}
    </div>
  );
}

function HistoryTab({ artifactId }: { artifactId: string }) {
  const versions = useArtifactVersions(artifactId);

  if (versions.isLoading) return <Spinner />;
  const items = [...(versions.data ?? [])].sort((a, b) => b.version - a.version);

  return (
    <Card className="divide-y divide-hairline-cool">
      {items.map((v) => (
        <div key={v.id} className="flex items-start gap-3 px-4 py-3">
          <span className="mt-0.5 rounded bg-canvas-soft px-2 py-0.5 font-mono text-xs font-medium text-ink-secondary ring-1 ring-inset ring-hairline">
            v{v.version}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium text-ink">{v.title}</p>
            <p className="text-xs text-ink-faint">
              {v.reason ?? "—"} · {formatDateTime(v.created_at)} · {v.created_by}
            </p>
          </div>
          <StatusBadge status={v.status} />
          {v.is_active && (
            <span className="text-xs font-medium text-primary-deep">active</span>
          )}
        </div>
      ))}
    </Card>
  );
}
