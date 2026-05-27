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
      <aside className="flex w-80 shrink-0 flex-col gap-3 border-r border-neutral-200 p-4 dark:border-neutral-800">
        <div>
          <h1 className="text-base font-semibold">Formalize</h1>
          <p className="mt-1 text-xs text-neutral-500">
            Turn a free-text project description into a connected artifact graph (mock LLM).
          </p>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="flex-1 resize-none rounded-lg border border-neutral-300 p-3 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          placeholder="Describe the project…"
        />
        <Button onClick={run} disabled={formalize.isPending || !description.trim()}>
          {formalize.isPending ? "Formalizing…" : "Formalize"}
        </Button>
        {result && (
          <p className="text-xs text-neutral-500">
            Created {result.artifacts.length} artifacts · {result.links.length} links.{" "}
            <Link href="/artifacts" className="text-indigo-600 hover:underline">
              Browse →
            </Link>
          </p>
        )}
        {formalize.isError && (
          <p className="text-xs text-red-500">Failed — is the backend running?</p>
        )}
      </aside>

      <div className="flex-1 bg-neutral-50 dark:bg-neutral-950">
        {result ? (
          <ArtifactGraph
            artifacts={result.artifacts}
            links={result.links}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-neutral-400">
            Enter a description and click <strong className="mx-1">Formalize</strong> to generate a
            connected artifact graph.
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
