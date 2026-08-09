"use client";

import { useState } from "react";

import { ArtifactDetailPanel } from "@/components/ArtifactDetailPanel";
import { ArtifactGraph } from "@/components/ArtifactGraph";
import { SidePanel } from "@/components/overlay/SidePanel";
import { ButtonLink, EmptyState, Spinner } from "@/components/ui";
import { useProject } from "@/lib/project-context";
import { useAllLinks, useArtifacts } from "@/lib/queries";
import { ARTIFACT_TYPE_COLOR, ARTIFACT_TYPE_LABEL, ARTIFACT_TYPE_ORDER } from "@/lib/types";

function Legend() {
  return (
    <div className="absolute left-3 top-3 z-10 flex flex-wrap gap-3 rounded-lg border border-hairline bg-canvas/90 px-3 py-2 text-xs text-ink-mute shadow-card backdrop-blur">
      {ARTIFACT_TYPE_ORDER.map((t) => (
        <span key={t} className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: ARTIFACT_TYPE_COLOR[t] }} />
          {ARTIFACT_TYPE_LABEL[t]}
        </span>
      ))}
    </div>
  );
}

export default function GraphPage() {
  const { projectId } = useProject();
  const { data: artifacts = [], isLoading, isError } = useArtifacts({}, projectId);
  const { data: links = [] } = useAllLinks(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = artifacts.find((a) => a.id === selectedId) ?? null;

  // Retain the last selection so the panel can finish sliding out after deselect
  // (set-state-during-render, guarded so it can't loop).
  const [panelArtifact, setPanelArtifact] = useState(selected);
  if (selected && selected !== panelArtifact) setPanelArtifact(selected);

  if (isLoading) {
    return (
      <div className="p-6">
        <Spinner label="Loading graph…" />
      </div>
    );
  }
  if (isError) {
    return <p className="p-6 text-sm text-red-500">Backend offline — start the API server.</p>;
  }
  if (artifacts.length === 0) {
    return (
      <div className="p-6">
        <EmptyState
          title="No artifacts to graph"
          hint="Formalize a project description or create artifacts to see their relationships."
          action={<ButtonLink href="/formalize">Formalize a description</ButtonLink>}
        />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="relative flex-1">
        <Legend />
        <ArtifactGraph
          artifacts={artifacts}
          links={links}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </div>
      <SidePanel open={!!selected} className="flex w-80 flex-col border-l border-hairline">
        {panelArtifact && (
          <>
            <div className="flex-1 overflow-y-auto">
              <ArtifactDetailPanel artifact={panelArtifact} />
            </div>
            <div className="border-t border-hairline p-3">
              <ButtonLink
                href={`/artifacts/${panelArtifact.id}`}
                className="w-full"
                variant="secondary"
              >
                Open full page →
              </ButtonLink>
            </div>
          </>
        )}
      </SidePanel>
    </div>
  );
}
