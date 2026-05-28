"use client";

import Link from "next/link";
import { useState } from "react";

import { ArtifactDetailPanel } from "@/components/ArtifactDetailPanel";
import { ArtifactGraph } from "@/components/ArtifactGraph";
import { Button } from "@/components/ui";
import { useFormalize } from "@/lib/queries";
import type { FormalizeResult } from "@/lib/types";

const SAMPLE = `Users can create tasks with a title and due date.
Users can mark tasks as complete.
Users can organize tasks into named lists.
Users can share a list with other users.`;

export default function FormalizePage() {
  const [description, setDescription] = useState(SAMPLE);
  const [result, setResult] = useState<FormalizeResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const formalize = useFormalize();

  const selected = result?.artifacts.find((a) => a.id === selectedId) ?? null;

  function run() {
    formalize.mutate(description, {
      onSuccess: (data) => {
        setResult(data);
        setSelectedId(null);
      },
    });
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-80 shrink-0 flex-col gap-3 border-r border-hairline p-4">
        <div>
          <h1 className="text-base font-medium tracking-tight text-ink">Formalize</h1>
          <p className="mt-1 text-xs text-ink-mute">
            Turn a free-text project description into a connected artifact graph (mock LLM).
          </p>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="flex-1 resize-none rounded-md border border-hairline-strong bg-canvas p-3 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-2 focus:ring-primary/20"
          placeholder="Describe the project…"
        />
        <Button onClick={run} disabled={formalize.isPending || !description.trim()}>
          {formalize.isPending ? "Formalizing…" : "Formalize"}
        </Button>
        {result && (
          <p className="text-xs text-ink-mute">
            Created {result.artifacts.length} artifacts · {result.links.length} links.{" "}
            <Link
              href="/artifacts"
              className="text-ink-secondary underline-offset-2 hover:text-primary-deep hover:underline"
            >
              Browse →
            </Link>
          </p>
        )}
        {formalize.isError && (
          <p className="text-xs text-red-500">Failed — is the backend running?</p>
        )}
      </aside>

      <div className="flex-1 bg-canvas-soft">
        {result ? (
          <ArtifactGraph
            artifacts={result.artifacts}
            links={result.links}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-ink-faint">
            Enter a description and click <strong className="mx-1 font-medium text-ink">Formalize</strong> to generate a
            connected artifact graph.
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
