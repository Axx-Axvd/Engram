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
      <aside className="flex w-96 shrink-0 flex-col gap-3 overflow-y-auto border-r border-neutral-200 p-4 dark:border-neutral-800">
        <div>
          <h1 className="text-base font-semibold">Change request</h1>
          <p className="mt-1 text-xs text-neutral-500">
            Describe a change. Engram finds the impacted artifacts, revises them into new versions,
            and links them to the request.
          </p>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="resize-none rounded-lg border border-neutral-300 p-3 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          placeholder="Describe the change…"
        />
        <Button onClick={run} disabled={change.isPending || !text.trim()}>
          {change.isPending ? "Analyzing…" : "Analyze impact"}
        </Button>
        {change.isError && <p className="text-xs text-red-500">Failed — is the backend running?</p>}

        {result && (
          <div className="space-y-3">
            <p className="rounded-lg bg-neutral-100 p-3 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
              {result.summary}
            </p>
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
              Impacted ({result.impacted.length})
            </p>
            <ul className="space-y-2">
              {result.impacted.map((item) => (
                <li
                  key={item.artifact.id}
                  className={`rounded-lg border p-2.5 text-sm transition-colors ${
                    selectedId === item.artifact.id
                      ? "border-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/30"
                      : "border-neutral-200 dark:border-neutral-800"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedId(item.artifact.id)}
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <TypeBadge type={item.artifact.type} />
                    <span className="flex-1 truncate font-medium">{item.artifact.title}</span>
                    <span className="text-xs text-neutral-400">v{item.artifact.current_version}</span>
                  </button>
                  <p className="mt-1 text-xs text-neutral-500">{item.rationale}</p>
                  <Link
                    href={`/artifacts/${item.artifact.id}`}
                    className="mt-1 inline-block text-xs text-indigo-600 hover:underline"
                  >
                    Open page →
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>

      <div className="flex-1 bg-neutral-50 dark:bg-neutral-950">
        {result ? (
          <ArtifactGraph
            artifacts={graphArtifacts}
            links={result.links}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-neutral-400">
            Describe a change and click <strong className="mx-1">Analyze impact</strong> to see what
            it touches.
          </div>
        )}
      </div>

      {selected && (
        <aside className="w-80 border-l border-neutral-200 dark:border-neutral-800">
          <ArtifactDetailPanel artifact={selected} />
        </aside>
      )}
    </div>
  );
}
