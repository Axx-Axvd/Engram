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
  project_brief: 0,
  requirement: 1,
  user_story: 2,
  task: 3,
  test_case: 4,
  change_request: 5,
};

function buildNodes(artifacts: Artifact[], selectedId: string | null): Node[] {
  const perLayer: Record<number, number> = {};
  return artifacts.map((a) => {
    const layer = LAYER[a.type] ?? 5;
    const idx = perLayer[layer] ?? 0;
    perLayer[layer] = idx + 1;
    const color = ARTIFACT_TYPE_COLOR[a.type];
    const selected = a.id === selectedId;
    return {
      id: a.id,
      position: { x: idx * 250, y: layer * 130 },
      data: { label: a.title },
      style: {
        border: `2px solid ${color}`,
        borderRadius: 8,
        padding: 8,
        width: 210,
        fontSize: 12,
        // White canvas with the category colour as the accent; selection adds a
        // faint tint + ring + lift rather than flooding the node (keeps the
        // near-black label legible across every hue, incl. light emerald).
        background: selected ? `${color}1f` : "#ffffff",
        color: "#171717",
        boxShadow: selected
          ? `0 0 0 3px ${color}40, 0 8px 24px rgba(0,0,0,0.08)`
          : "0 1px 3px rgba(0,0,0,0.06)",
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
    style: { stroke: "#c7c7c7" },
    labelStyle: { fontSize: 10, fill: "#707070" },
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
