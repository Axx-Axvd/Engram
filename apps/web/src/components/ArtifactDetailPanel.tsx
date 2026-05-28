"use client";

import { ARTIFACT_TYPE_COLOR, ARTIFACT_TYPE_LABEL, type Artifact } from "@/lib/types";

export function ArtifactDetailPanel({ artifact }: { artifact: Artifact | null }) {
  if (!artifact) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-ink-faint">
        Select a node in the graph to inspect the artifact.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-5">
      <span
        className="w-fit rounded-full px-2.5 py-1 text-xs font-medium text-white"
        style={{ background: ARTIFACT_TYPE_COLOR[artifact.type] }}
      >
        {ARTIFACT_TYPE_LABEL[artifact.type]}
      </span>

      <h2 className="text-lg font-medium leading-snug tracking-tight text-ink">{artifact.title}</h2>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-ink-faint">Status</dt>
        <dd className="text-ink">{artifact.status}</dd>
        <dt className="text-ink-faint">Version</dt>
        <dd className="text-ink">v{artifact.current_version}</dd>
        <dt className="text-ink-faint">Source</dt>
        <dd className="truncate text-ink">{artifact.source_ref ?? "—"}</dd>
      </dl>

      <div className="whitespace-pre-wrap border-t border-hairline pt-3 text-sm text-ink">
        {artifact.content || <span className="text-ink-faint">No content.</span>}
      </div>
    </div>
  );
}
