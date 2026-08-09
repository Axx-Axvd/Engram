"use client";

import Link from "next/link";

import { useProject } from "@/lib/project-context";
import { useHealth } from "@/lib/queries";

export function Topbar() {
  const health = useHealth();
  const { projects, projectId, setProjectId, isLoading } = useProject();
  const status = health.isLoading ? "bg-amber-400" : health.isSuccess ? "bg-primary" : "bg-red-500";

  return (
    <header className="flex items-center gap-4 border-b border-hairline bg-canvas/90 px-5 py-3 backdrop-blur">
      <Link href="/" className="flex min-w-44 items-baseline gap-2">
        <span className="flex items-center gap-1.5 text-lg font-medium tracking-tight text-ink">
          <span className="size-2 translate-y-px rounded-full bg-primary" />
          Engram
        </span>
        <span className="hidden text-xs text-ink-faint xl:inline">evidence-backed impact</span>
      </Link>

      <div className="flex flex-1 items-center gap-2">
        <span className="text-xs font-medium text-ink-faint">Project</span>
        <select
          value={projectId ?? ""}
          onChange={(event) => setProjectId(event.target.value)}
          disabled={isLoading || projects.length === 0}
          className="min-w-56 rounded-md border border-hairline-strong bg-canvas px-3 py-1.5 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        >
          {!projectId && <option value="">Loading projects…</option>}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        <Link href="/" className="text-xs text-ink-mute hover:text-primary-deep">
          manage
        </Link>
      </div>

      <span className="inline-flex items-center gap-2 text-xs text-ink-mute">
        <span className={`size-2 rounded-full ${status}`} />
        <span className="hidden md:inline">{health.isSuccess ? "API connected" : "API offline"}</span>
      </span>
    </header>
  );
}
