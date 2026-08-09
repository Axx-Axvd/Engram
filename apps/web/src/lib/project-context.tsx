"use client";

import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { api } from "@/lib/api/client";
import type { Project } from "@/lib/types";

const STORAGE_KEY = "engram.project-id";
const EMPTY_PROJECTS: Project[] = [];

interface ProjectContextValue {
  projects: Project[];
  project: Project | null;
  projectId: string | null;
  setProjectId: (id: string) => void;
  isLoading: boolean;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<string | null>(() =>
    typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY),
  );
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: async (): Promise<Project[]> => {
      const result = await api.GET("/api/projects");
      if (result.error || !result.data) throw new Error("Could not load projects");
      return result.data;
    },
  });
  const projects = projectsQuery.data ?? EMPTY_PROJECTS;
  const fallback = projects.find((project) => project.is_default) ?? projects[0] ?? null;
  const project = projects.find((value) => value.id === selected) ?? fallback;
  const projectId = project?.id ?? null;

  const value = useMemo<ProjectContextValue>(
    () => ({
      projects,
      project,
      projectId,
      setProjectId: (id) => {
        setSelected(id);
        window.localStorage.setItem(STORAGE_KEY, id);
      },
      isLoading: projectsQuery.isLoading,
    }),
    [project, projectId, projects, projectsQuery.isLoading],
  );
  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject() {
  const value = useContext(ProjectContext);
  if (!value) throw new Error("useProject must be used inside ProjectProvider");
  return value;
}
