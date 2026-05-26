"use client";

import {
  Background,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

import { ARTIFACT_TYPE_COLOR, type Artifact, type ArtifactType, type Link } from "@/lib/types";

const LAYER: Record<ArtifactType, number> = {
  requirement: 0,
  user_story: 1,
  task: 2,
  test_case: 3,
  change_request: 4,
};

function buildNodes(artifacts: Artifact[], selectedId: string | null): Node[] {
  const perLayer: Record<number, number> = {};
  return artifacts.map((a) => {
    const layer = LAYER[a.type] ?? 5;
    const idx = perLayer[layer] ?? 0;
    perLayer[layer] = idx + 1;
    const color = ARTIFACT_TYPE_COLOR[a.type];
    return {
      id: a.id,
      position: { x: idx * 250, y: layer * 130 },
      data: { label: a.title },
      style: {
        border: `2px solid ${color}`,
        borderRadius: 10,
        padding: 8,
        width: 210,
        fontSize: 12,
        background: a.id === selectedId ? color : "white",
        color: a.id === selectedId ? "white" : "#0f172a",
        boxShadow: a.id === selectedId ? `0 0 0 3px ${color}33` : "none",
      },
    };
  });
}

function buildEdges(links: Link[]): Edge[] {
  return links.map((l) => ({
    id: l.id,
    source: l.source_id,
    target: l.target_id,
    label: l.type,
    style: { stroke: "#94a3b8" },
    labelStyle: { fontSize: 10, fill: "#475569" },
  }));
}

export function ArtifactGraph({
  artifacts,
  links,
  selectedId,
  onSelect,
}: {
  artifacts: Artifact[];
  links: Link[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const nodes = useMemo(() => buildNodes(artifacts, selectedId), [artifacts, selectedId]);
  const edges = useMemo(() => buildEdges(links), [links]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      nodesDraggable={false}
      nodesConnectable={false}
      onNodeClick={(_, node) => onSelect(node.id)}
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable />
    </ReactFlow>
  );
}
