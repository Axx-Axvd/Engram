"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { Button, Card, Spinner, StatusBadge, TypeBadge } from "@/components/ui";
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
  ARTIFACT_TYPE_LABEL,
  type Artifact,
  type ArtifactItem,
  type ArtifactStatus,
  LINK_TYPES,
  type LinkType,
  STATUSES_FOR_TYPE,
} from "@/lib/types";

type Tab = "content" | "links" | "history";

export default function ArtifactPage() {
  const { id } = useParams<{ id: string }>();
  const artifact = useArtifact(id);
  const [tab, setTab] = useState<Tab>("content");

  if (artifact.isLoading) {
    return (
      <div className="p-6">
        <Spinner label="Loading artifact…" />
      </div>
    );
  }
  if (artifact.isError || !artifact.data) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-red-500">Artifact not found.</p>
        <Link href="/artifacts" className="text-sm text-indigo-600 hover:underline">
          ← Back to artifacts
        </Link>
      </div>
    );
  }

  const a = artifact.data;

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
      <div className="flex items-center gap-2 text-xs text-neutral-400">
        <Link href="/artifacts" className="hover:underline">
          Artifacts
        </Link>
        <span>›</span>
        <span className="text-neutral-500">{ARTIFACT_TYPE_LABEL[a.type]}</span>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <TypeBadge type={a.type} />
            <StatusBadge status={a.status} />
            <span className="text-xs text-neutral-400">v{a.current_version}</span>
          </div>
          <h1 className="text-xl font-semibold leading-snug">{a.title}</h1>
        </div>
      </div>

      <div className="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
        {(["content", "links", "history"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "content" && <ContentTab artifact={a} />}
      {tab === "links" && <LinksTab artifactId={a.id} />}
      {tab === "history" && <HistoryTab artifactId={a.id} />}
    </div>
  );
}

function ContentTab({ artifact: a }: { artifact: Artifact }) {
  const [editing, setEditing] = useState(false);
  const update = useUpdateArtifact(a.id);

  const [title, setTitle] = useState(a.title);
  const [content, setContent] = useState(a.content);
  const [status, setStatus] = useState<ArtifactStatus>(a.status);
  const [reason, setReason] = useState("");

  function startEdit() {
    setTitle(a.title);
    setContent(a.content);
    setStatus(a.status);
    setReason("");
    setEditing(true);
  }

  function save() {
    update.mutate(
      { title, content, status, reason: reason || null },
      { onSuccess: () => setEditing(false) },
    );
  }

  if (editing) {
    return (
      <Card className="space-y-3 p-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-medium outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={8}
          className="w-full resize-y rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ArtifactStatus)}
            className="rounded-lg border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {STATUSES_FOR_TYPE[a.type].map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="reason for change (optional)"
            className="flex-1 rounded-lg border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={save} disabled={update.isPending || !title.trim()}>
            {update.isPending ? "Saving…" : "Save new version"}
          </Button>
          <Button variant="secondary" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          {update.isError && <span className="text-xs text-red-500">Save failed.</span>}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="secondary" onClick={startEdit}>
          Edit
        </Button>
      </div>
      <Card className="p-5">
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {a.content || <span className="text-neutral-400">No content.</span>}
        </p>
      </Card>
      {a.items && a.items.length > 0 && <ItemsSection items={a.items} />}
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
        <dt className="text-neutral-400">Source</dt>
        <dd className="truncate">{a.source_ref ?? "—"}</dd>
        <dt className="text-neutral-400">Created</dt>
        <dd>
          {formatDateTime(a.created_at)} · {a.created_by}
        </dd>
        <dt className="text-neutral-400">Updated</dt>
        <dd>
          {formatDateTime(a.updated_at)} · {a.updated_by}
        </dd>
      </dl>
    </div>
  );
}

function LinksTab({ artifactId }: { artifactId: string }) {
  const links = useArtifactLinks(artifactId);
  const { data: allArtifacts = [] } = useArtifacts();
  const createLink = useCreateLink(artifactId);

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
        <p className="text-sm text-neutral-400">No links yet.</p>
      )}
      {links.data && links.data.length > 0 && (
        <Card className="divide-y divide-neutral-100 dark:divide-neutral-800">
          {links.data.map((l) => {
            const outgoing = l.source_id === artifactId;
            const other = nameOf(outgoing ? l.target_id : l.source_id);
            if (!other) return null;
            return (
              <Link
                key={l.id}
                href={`/artifacts/${other.id}`}
                className="flex items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
              >
                <span className="truncate text-sm font-medium text-indigo-600">{other.title}</span>
                <span className="shrink-0 text-xs text-neutral-400">
                  {l.type.replace("_", " ")}
                </span>
              </Link>
            );
          })}
        </Card>
      )}

      <Card className="space-y-3 p-4">
        <div>
          <p className="text-sm font-medium">Add link</p>
          <p className="text-xs text-neutral-400">Relate this document to another one.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={type}
            onChange={(e) => setType(e.target.value as LinkType)}
            className="rounded-lg border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {LINK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace("_", " ")}
              </option>
            ))}
          </select>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="min-w-48 flex-1 rounded-lg border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            <option value="">Select target artifact…</option>
            {candidates.map((a) => (
              <option key={a.id} value={a.id}>
                [{ARTIFACT_TYPE_LABEL[a.type]}] {a.title}
              </option>
            ))}
          </select>
          <Button onClick={add} disabled={!targetId || createLink.isPending}>
            {createLink.isPending ? "Linking…" : "Link"}
          </Button>
        </div>
        {createLink.isError && (
          <p className="text-xs text-red-500">Could not create link (duplicate or invalid).</p>
        )}
      </Card>
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
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-400">
            {feature}
          </p>
          <Card className="divide-y divide-neutral-100 dark:divide-neutral-800">
            {groupItems.map((item) => (
              <div key={item.key} className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-semibold dark:bg-neutral-800">
                    {item.key}
                  </span>
                  <span className="text-sm font-medium">{item.title}</span>
                </div>
                {item.text && (
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{item.text}</p>
                )}
                {item.refs && item.refs.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {item.refs.map((ref, idx) => (
                      <Link
                        key={`${ref.artifact_id}-${ref.key}-${idx}`}
                        href={`/artifacts/${ref.artifact_id}`}
                        className="rounded bg-indigo-50 px-1.5 py-0.5 text-xs text-indigo-700 hover:underline dark:bg-indigo-950/40 dark:text-indigo-300"
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
    <Card className="divide-y divide-neutral-100 dark:divide-neutral-800">
      {items.map((v) => (
        <div key={v.id} className="flex items-start gap-3 px-4 py-3">
          <span className="mt-0.5 rounded bg-neutral-100 px-2 py-0.5 text-xs font-semibold dark:bg-neutral-800">
            v{v.version}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium">{v.title}</p>
            <p className="text-xs text-neutral-400">
              {v.reason ?? "—"} · {formatDateTime(v.created_at)} · {v.created_by}
            </p>
          </div>
          <StatusBadge status={v.status} />
          {v.is_active && (
            <span className="text-xs font-medium text-emerald-600">active</span>
          )}
        </div>
      ))}
    </Card>
  );
}
