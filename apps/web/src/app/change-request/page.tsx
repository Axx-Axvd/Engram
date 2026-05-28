"use client";

import Link from "next/link";
import { useState } from "react";

import { ArtifactDetailPanel } from "@/components/ArtifactDetailPanel";
import { ArtifactGraph } from "@/components/ArtifactGraph";
import { Button, TypeBadge } from "@/components/ui";
import { useChangeRequest } from "@/lib/queries";
import type { Artifact, ChangeImpactResult } from "@/lib/types";

const SAMPLE = "Let users share task lists with teammates and external guests by email invite.";

export default function ChangeRequestPage() {
  const [text, setText] = useState(SAMPLE);
  const [result, setResult] = useState<ChangeImpactResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const change = useChangeRequest();

  const graphArtifacts: Artifact[] = result
    ? [result.change_request, ...result.impacted.map((i) => i.artifact)]
    : [];
  const selected = graphArtifacts.find((a) => a.id === selectedId) ?? null;

  function run() {
    change.mutate(text, {
      onSuccess: (data) => {
        setResult(data);
        setSelectedId(data.change_request.id);
      },
    });
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-96 shrink-0 flex-col gap-3 overflow-y-auto border-r border-hairline p-4">
        <div>
          <h1 className="text-base font-medium tracking-tight text-ink">Change request</h1>
          <p className="mt-1 text-xs text-ink-mute">
            Describe a change. Engram finds the impacted artifacts, revises them into new versions,
            and links them to the request.
          </p>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="resize-none rounded-md border border-hairline-strong bg-canvas p-3 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
          placeholder="Describe the change…"
        />
        <Button onClick={run} disabled={change.isPending || !text.trim()}>
          {change.isPending ? "Analyzing…" : "Analyze impact"}
        </Button>
        {change.isError && <p className="text-xs text-red-500">Failed — is the backend running?</p>}

        {result && (
          <div className="space-y-3">
            <p className="rounded-md bg-canvas-soft p-3 text-xs text-ink-mute ring-1 ring-inset ring-hairline">
              {result.summary}
            </p>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
              Impacted ({result.impacted.length})
            </p>
            <ul className="space-y-2">
              {result.impacted.map((item) => (
                <li
                  key={item.artifact.id}
                  className={`rounded-md border p-2.5 text-sm transition-colors ${
                    selectedId === item.artifact.id
                      ? "border-primary bg-primary/10"
                      : "border-hairline"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedId(item.artifact.id)}
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <TypeBadge type={item.artifact.type} />
                    <span className="flex-1 truncate font-medium text-ink">{item.artifact.title}</span>
                    <span className="text-xs text-ink-faint">v{item.artifact.current_version}</span>
                  </button>
                  <p className="mt-1 text-xs text-ink-mute">{item.rationale}</p>
                  <Link
                    href={`/artifacts/${item.artifact.id}`}
                    className="mt-1 inline-block text-xs text-ink-secondary underline-offset-2 hover:text-primary-deep hover:underline"
                  >
                    Open page →
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>

      <div className="flex-1 bg-canvas-soft">
        {result ? (
          <ArtifactGraph
            artifacts={graphArtifacts}
            links={result.links}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-ink-faint">
            Describe a change and click <strong className="mx-1 font-medium text-ink">Analyze impact</strong> to see what
            it touches.
          </div>
        )}
      </div>

      {selected && (
        <aside className="w-80 border-l border-hairline">
          <ArtifactDetailPanel artifact={selected} />
        </aside>
      )}
    </div>
  );
}
