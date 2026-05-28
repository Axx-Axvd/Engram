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

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
      <div className="flex items-center gap-2 text-xs text-ink-faint">
        <Link href="/artifacts" className="hover:text-ink hover:underline">
          Artifacts
        </Link>
        <span>›</span>
        <span className="text-ink-mute">{ARTIFACT_TYPE_LABEL[a.type]}</span>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <TypeBadge type={a.type} />
            <StatusBadge status={a.status} />
            <span className="text-xs text-ink-faint">v{a.current_version}</span>
          </div>
          <h1 className="text-xl font-medium leading-snug tracking-tight text-ink">{a.title}</h1>
        </div>
      </div>

      <div className="flex gap-1 border-b border-hairline">
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
          className="w-full rounded-md border border-hairline-strong bg-canvas px-3 py-2 text-sm font-medium text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={8}
          className="w-full resize-y rounded-md border border-hairline-strong bg-canvas px-3 py-2 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ArtifactStatus)}
            className="rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink focus:border-primary focus:ring-2 focus:ring-primary/20"
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
            className="flex-1 rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
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
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
          {a.content || <span className="text-ink-faint">No content.</span>}
        </p>
      </Card>
      {a.items && a.items.length > 0 && <ItemsSection items={a.items} />}
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
        <dt className="text-ink-faint">Source</dt>
        <dd className="truncate text-ink">{a.source_ref ?? "—"}</dd>
        <dt className="text-ink-faint">Created</dt>
        <dd className="text-ink">
          {formatDateTime(a.created_at)} · {a.created_by}
        </dd>
        <dt className="text-ink-faint">Updated</dt>
        <dd className="text-ink">
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
        <p className="text-sm text-ink-faint">No links yet.</p>
      )}
      {links.data && links.data.length > 0 && (
        <Card className="divide-y divide-hairline-cool">
          {links.data.map((l) => {
            const outgoing = l.source_id === artifactId;
            const other = nameOf(outgoing ? l.target_id : l.source_id);
            if (!other) return null;
            return (
              <Link
                key={l.id}
                href={`/artifacts/${other.id}`}
                className="flex items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-canvas-soft"
              >
                <span className="truncate text-sm font-medium text-ink">{other.title}</span>
                <span className="shrink-0 text-xs text-ink-faint">
                  {l.type.replace("_", " ")}
                </span>
              </Link>
            );
          })}
        </Card>
      )}

      <Card className="space-y-3 p-4">
        <div>
          <p className="text-sm font-medium text-ink">Add link</p>
          <p className="text-xs text-ink-faint">Relate this document to another one.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={type}
            onChange={(e) => setType(e.target.value as LinkType)}
            className="rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink focus:border-primary focus:ring-2 focus:ring-primary/20"
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
            className="min-w-48 flex-1 rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink focus:border-primary focus:ring-2 focus:ring-primary/20"
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
