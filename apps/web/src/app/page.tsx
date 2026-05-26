"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ArtifactDetailPanel } from "@/components/ArtifactDetailPanel";
import { ArtifactGraph } from "@/components/ArtifactGraph";
import { api } from "@/lib/api/client";
import type { FormalizeResult } from "@/lib/types";

const SAMPLE = `Users can create tasks with a title and due date.
Users can mark tasks as complete.
Users can organize tasks into named lists.
Users can share a list with other users.`;

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await api.GET("/health");
      if (error) throw new Error("unreachable");
      return data;
    },
    retry: false,
  });
}

export default function Home() {
  const [description, setDescription] = useState(SAMPLE);
  const [result, setResult] = useState<FormalizeResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const health = useHealth();

  const formalize = useMutation({
    mutationFn: async (desc: string): Promise<FormalizeResult> => {
      const { data, error } = await api.POST("/api/workflows/formalize", {
        body: { description: desc, created_by: "web" },
      });
      if (error || !data) throw new Error("Formalization failed");
      return data;
    },
    onSuccess: (data) => {
      setResult(data);
      setSelectedId(null);
    },
  });

  const selected = useMemo(
    () => result?.artifacts.find((a) => a.id === selectedId) ?? null,
    [result, selectedId],
  );

  const backendOk = health.isSuccess;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-neutral-200 px-5 py-3 dark:border-neutral-800">
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-semibold tracking-tight">Engram</span>
          <span className="text-xs text-neutral-400">project memory</span>
        </div>
        <span className="inline-flex items-center gap-2 text-xs text-neutral-500">
          <span
            className={`size-2 rounded-full ${
              health.isLoading ? "bg-amber-400" : backendOk ? "bg-emerald-500" : "bg-red-500"
            }`}
          />
          {health.isLoading ? "connecting" : backendOk ? "backend connected" : "backend offline"}
        </span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-80 flex-col gap-3 border-r border-neutral-200 p-4 dark:border-neutral-800">
          <label htmlFor="desc" className="text-sm font-medium">
            Project description
          </label>
          <textarea
            id="desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="flex-1 resize-none rounded-lg border border-neutral-300 p-3 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Describe the project…"
          />
          <button
            type="button"
            onClick={() => formalize.mutate(description)}
            disabled={formalize.isPending || !description.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
          >
            {formalize.isPending ? "Formalizing…" : "Formalize"}
          </button>
          {result && (
            <p className="text-xs text-neutral-500">
              {result.artifacts.length} artifacts · {result.links.length} links
            </p>
          )}
          {formalize.isError && (
            <p className="text-xs text-red-500">Failed — is the backend running?</p>
          )}
        </aside>

        <main className="flex-1 bg-neutral-50 dark:bg-neutral-950">
          {result ? (
            <ArtifactGraph
              artifacts={result.artifacts}
              links={result.links}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          ) : (
            <div className="flex h-full items-center justify-center p-8 text-center text-sm text-neutral-400">
              Enter a project description and click <strong className="mx-1">Formalize</strong> to
              generate a connected artifact graph.
            </div>
          )}
        </main>

        <aside className="w-80 border-l border-neutral-200 dark:border-neutral-800">
          <ArtifactDetailPanel artifact={selected} />
        </aside>
      </div>
    </div>
  );
}
