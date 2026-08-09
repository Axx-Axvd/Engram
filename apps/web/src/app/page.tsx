"use client";

import { useState } from "react";

import { Button, ButtonLink, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { useProject } from "@/lib/project-context";
import {
  useChangeSets,
  useContextPackages,
  useCreateProject,
  useImpactAnalyses,
  useProjectItems,
  useSources,
} from "@/lib/queries";

export default function ProjectsPage() {
  const { projects, project, projectId, setProjectId, isLoading } = useProject();
  const [name, setName] = useState("");
  const create = useCreateProject();
  const items = useProjectItems(projectId);
  const sources = useSources(projectId);
  const analyses = useImpactAnalyses(projectId);
  const packages = useContextPackages(projectId);
  const changes = useChangeSets(projectId);

  function createProject() {
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim() },
      {
        onSuccess: (value) => {
          setName("");
          setProjectId(value.id);
        },
      },
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-7 p-6">
      <PageHeader
        title="Projects"
        description="Each project is a hard isolation boundary for sources, knowledge, links, analyses and packages."
        actions={<ButtonLink href="/sources">Connect a source</ButtonLink>}
      />

      {isLoading ? (
        <Spinner label="Loading projects…" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((value) => (
            <button
              type="button"
              key={value.id}
              onClick={() => setProjectId(value.id)}
              className={`rounded-lg border p-4 text-left shadow-card transition-colors ${
                value.id === projectId
                  ? "border-primary bg-primary/5"
                  : "border-hairline bg-canvas hover:border-hairline-strong"
              }`}
            >
              <span className="flex items-center justify-between gap-3">
                <span className="font-medium text-ink">{value.name}</span>
                {value.id === projectId && (
                  <span className="rounded-full bg-primary px-2 py-0.5 text-[11px] font-medium text-on-primary">
                    active
                  </span>
                )}
              </span>
              <span className="mt-2 block text-xs text-ink-mute">
                {value.description || `Created ${formatDateTime(value.created_at)}`}
              </span>
              <span className="mt-3 block font-mono text-[10px] text-ink-faint">{value.id}</span>
            </button>
          ))}
          <Card className="p-4">
            <p className="text-sm font-medium text-ink">Create project</p>
            <div className="mt-3 flex gap-2">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") createProject();
                }}
                placeholder="Project name"
                className="min-w-0 flex-1 rounded-md border border-hairline-strong px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <Button onClick={createProject} disabled={!name.trim() || create.isPending}>
                Add
              </Button>
            </div>
          </Card>
        </div>
      )}

      {project ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-medium tracking-tight text-ink">{project.name} at a glance</h2>
            <p className="mt-1 text-sm text-ink-mute">
              Live counts from the isolated project scope, not the legacy global workspace.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              ["GitHub sources", sources.data?.filter((source) => source.kind === "github").length ?? 0],
              ["Knowledge items", items.data?.length ?? 0],
              ["Changes", changes.data?.length ?? 0],
              ["Impact analyses", analyses.data?.length ?? 0],
              ["Context packages", packages.data?.length ?? 0],
            ].map(([label, count]) => (
              <Card key={label} className="p-4">
                <p className="text-xs text-ink-mute">{label}</p>
                <p className="mt-1 text-2xl font-medium tracking-tight text-ink">{count}</p>
              </Card>
            ))}
          </div>
          {!sources.isLoading &&
            (sources.data?.filter((source) => source.kind === "github").length ?? 0) === 0 && (
            <EmptyState
              title="Connect the first source"
              hint="GitHub is the only supported integration in this MVP. Engram imports a fixed commit SHA and remains read-only."
              action={<ButtonLink href="/sources">Connect GitHub</ButtonLink>}
            />
          )}
        </section>
      ) : null}
    </div>
  );
}
