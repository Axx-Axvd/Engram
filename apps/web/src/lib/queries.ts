"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type {
  Artifact,
  ArtifactStatus,
  ArtifactType,
  ArtifactVersion,
  ConsistencyReport,
  Link,
  ChangeSet,
  ContextPackage,
  ImpactAnalysis,
  KnowledgeItem,
  Project,
  Source,
  SourceRevision,
} from "@/lib/types";

function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error || result.data === undefined) {
    throw new Error("Request failed");
  }
  return result.data;
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => unwrap(await api.GET("/health")),
    retry: false,
    refetchInterval: 15_000,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; description?: string }): Promise<Project> =>
      unwrap(
        await api.POST("/api/projects", {
          body: { name: body.name, description: body.description ?? "", created_by: "web" },
        }),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useProjectItems(projectId: string | null) {
  return useQuery({
    queryKey: ["project-items", projectId],
    queryFn: async (): Promise<KnowledgeItem[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/items", {
          params: { path: { project_id: projectId! } },
        }),
      ),
    enabled: Boolean(projectId),
  });
}

export function useSources(projectId: string | null) {
  return useQuery({
    queryKey: ["sources", projectId],
    queryFn: async (): Promise<Source[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/sources", {
          params: { path: { project_id: projectId! } },
        }),
      ),
    enabled: Boolean(projectId),
  });
}

export function useCreateGitHubSource(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { repository: string; ref: string }): Promise<Source> => {
      if (!projectId) throw new Error("Select a project first");
      return unwrap(
        await api.POST("/api/projects/{project_id}/sources/github", {
          params: { path: { project_id: projectId } },
          body: { ...body, created_by: "web" },
        }),
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources", projectId] }),
  });
}

export function useSourceRevisions(projectId: string | null, sourceId: string | null) {
  return useQuery({
    queryKey: ["source-revisions", projectId, sourceId],
    queryFn: async (): Promise<SourceRevision[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/sources/{source_id}/revisions", {
          params: { path: { project_id: projectId!, source_id: sourceId! } },
        }),
      ),
    enabled: Boolean(projectId && sourceId),
  });
}

export function useSyncSource(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { sourceId: string; ref?: string; analysisId?: string }) => {
      if (!projectId) throw new Error("Select a project first");
      return unwrap(
        await api.POST("/api/projects/{project_id}/sources/{source_id}/sync", {
          params: { path: { project_id: projectId, source_id: body.sourceId } },
          body: {
            ref: body.ref ?? null,
            analysis_id: body.analysisId ?? null,
            created_by: "web",
          },
        }),
      );
    },
    onSuccess: (_, body) => {
      qc.invalidateQueries({ queryKey: ["source-revisions", projectId, body.sourceId] });
      qc.invalidateQueries({ queryKey: ["project-items", projectId] });
      qc.invalidateQueries({ queryKey: ["change-sets", projectId] });
    },
  });
}

export function useImpactAnalyses(projectId: string | null) {
  return useQuery({
    queryKey: ["impact-analyses", projectId],
    queryFn: async (): Promise<ImpactAnalysis[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/impact-analyses", {
          params: { path: { project_id: projectId! } },
        }),
      ),
    enabled: Boolean(projectId),
  });
}

export function useCreateImpactAnalysis(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (query: string): Promise<ImpactAnalysis> => {
      if (!projectId) throw new Error("Select a project first");
      return unwrap(
        await api.POST("/api/projects/{project_id}/impact-analyses", {
          params: { path: { project_id: projectId } },
          body: {
            query,
            source_revision_id: null,
            context_budget: 4000,
            max_candidates: 20,
            retrieval_mode: "combined",
            created_by: "web",
          },
        }),
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["impact-analyses", projectId] }),
  });
}

export function useReviewCandidate(projectId: string | null, analysisId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { candidateId: string; decision: "approved" | "rejected" }) => {
      if (!projectId || !analysisId) throw new Error("Select an analysis first");
      return unwrap(
        await api.PATCH(
          "/api/projects/{project_id}/impact-analyses/{analysis_id}/candidates/{candidate_id}",
          {
            params: {
              path: {
                project_id: projectId,
                analysis_id: analysisId,
                candidate_id: body.candidateId,
              },
            },
            body: { decision: body.decision, reviewed_by: "web" },
          },
        ),
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["impact-analyses", projectId] }),
  });
}

export function useContextPackages(projectId: string | null) {
  return useQuery({
    queryKey: ["context-packages", projectId],
    queryFn: async (): Promise<ContextPackage[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/context-packages", {
          params: { path: { project_id: projectId! } },
        }),
      ),
    enabled: Boolean(projectId),
  });
}

export function useBuildContextPackage(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { analysisId: string; tokenBudget: number }): Promise<ContextPackage> => {
      if (!projectId) throw new Error("Select a project first");
      return unwrap(
        await api.POST(
          "/api/projects/{project_id}/impact-analyses/{analysis_id}/context-packages",
          {
            params: { path: { project_id: projectId, analysis_id: body.analysisId } },
            body: { token_budget: body.tokenBudget, created_by: "web" },
          },
        ),
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["context-packages", projectId] }),
  });
}

export function useChangeSets(projectId: string | null) {
  return useQuery({
    queryKey: ["change-sets", projectId],
    queryFn: async (): Promise<ChangeSet[]> =>
      unwrap(
        await api.GET("/api/projects/{project_id}/change-sets", {
          params: { path: { project_id: projectId! } },
        }),
      ),
    enabled: Boolean(projectId),
  });
}

export interface ArtifactFilters {
  type?: ArtifactType;
  status?: ArtifactStatus;
}

export function useArtifacts(filters: ArtifactFilters = {}, projectId?: string | null) {
  return useQuery({
    queryKey: ["artifacts", projectId, filters],
    queryFn: async (): Promise<Artifact[]> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/artifacts", {
              params: {
                path: { project_id: projectId },
                query: { ...filters, limit: 500 },
              },
            }),
          )
        : unwrap(
            await api.GET("/api/artifacts", {
              params: { query: { ...filters, limit: 500 } },
            }),
          ),
  });
}

export function useArtifact(id: string, projectId?: string | null) {
  return useQuery({
    queryKey: ["artifact", projectId, id],
    queryFn: async (): Promise<Artifact> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/artifacts/{artifact_id}", {
              params: { path: { project_id: projectId, artifact_id: id } },
            }),
          )
        : unwrap(
            await api.GET("/api/artifacts/{artifact_id}", {
              params: { path: { artifact_id: id } },
            }),
          ),
    enabled: Boolean(id),
  });
}

export function useArtifactVersions(id: string, projectId?: string | null) {
  return useQuery({
    queryKey: ["versions", projectId, id],
    queryFn: async (): Promise<ArtifactVersion[]> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/artifacts/{artifact_id}/versions", {
              params: { path: { project_id: projectId, artifact_id: id } },
            }),
          )
        : unwrap(
            await api.GET("/api/artifacts/{artifact_id}/versions", {
              params: { path: { artifact_id: id } },
            }),
          ),
    enabled: Boolean(id),
  });
}

export function useArtifactLinks(id: string, projectId?: string | null) {
  return useQuery({
    queryKey: ["links", projectId, id],
    queryFn: async (): Promise<Link[]> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/artifacts/{artifact_id}/links", {
              params: { path: { project_id: projectId, artifact_id: id } },
            }),
          )
        : unwrap(
            await api.GET("/api/artifacts/{artifact_id}/links", {
              params: { path: { artifact_id: id } },
            }),
          ),
    enabled: Boolean(id),
  });
}

export function useAllLinks(projectId?: string | null) {
  return useQuery({
    queryKey: ["all-links", projectId],
    queryFn: async (): Promise<Link[]> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/links", {
              params: { path: { project_id: projectId } },
            }),
          )
        : unwrap(await api.GET("/api/links")),
  });
}

export function useCreateArtifact(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      type: ArtifactType;
      title: string;
      content: string;
      status?: ArtifactStatus | null;
      source_ref?: string | null;
    }): Promise<Artifact> =>
      projectId
        ? unwrap(
            await api.POST("/api/projects/{project_id}/artifacts", {
              params: { path: { project_id: projectId } },
              body: { ...body, created_by: "web" },
            }),
          )
        : unwrap(await api.POST("/api/artifacts", { body: { ...body, created_by: "web" } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifacts"] });
    },
  });
}

export function useUpdateArtifact(id: string, projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      title?: string | null;
      content?: string | null;
      status?: ArtifactStatus | null;
      source_ref?: string | null;
      reason?: string | null;
    }): Promise<Artifact> =>
      projectId
        ? unwrap(
            await api.PATCH("/api/projects/{project_id}/artifacts/{artifact_id}", {
              params: { path: { project_id: projectId, artifact_id: id } },
              body: { ...body, updated_by: "web" },
            }),
          )
        : unwrap(
            await api.PATCH("/api/artifacts/{artifact_id}", {
              params: { path: { artifact_id: id } },
              body: { ...body, updated_by: "web" },
            }),
          ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifact", id] });
      qc.invalidateQueries({ queryKey: ["versions", id] });
      qc.invalidateQueries({ queryKey: ["artifacts"] });
      qc.invalidateQueries({ queryKey: ["consistency"] });
    },
  });
}

export function useDeleteArtifact(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const { error } = projectId
        ? await api.DELETE("/api/projects/{project_id}/artifacts/{artifact_id}", {
            params: { path: { project_id: projectId, artifact_id: id } },
          })
        : await api.DELETE("/api/artifacts/{artifact_id}", {
            params: { path: { artifact_id: id } },
          });
      if (error) throw new Error("Delete failed");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifacts"] });
      qc.invalidateQueries({ queryKey: ["all-links"] });
      qc.invalidateQueries({ queryKey: ["consistency"] });
    },
  });
}

export function useCreateLink(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      source_id: string;
      target_id: string;
      type: Link["type"];
    }): Promise<Link> =>
      projectId
        ? unwrap(
            await api.POST("/api/projects/{project_id}/links", {
              params: { path: { project_id: projectId } },
              body: { ...body, created_by: "web" },
            }),
          )
        : unwrap(await api.POST("/api/links", { body: { ...body, created_by: "web" } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["all-links"] });
      // Prefix invalidation covers both source and target artifacts, not just the current one.
      qc.invalidateQueries({ queryKey: ["links"] });
      qc.invalidateQueries({ queryKey: ["consistency"] });
    },
  });
}

export function useFormalize(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (description: string) =>
      projectId
        ? unwrap(
            await api.POST("/api/projects/{project_id}/workflows/formalize", {
              params: { path: { project_id: projectId } },
              body: { description, created_by: "web" },
            }),
          )
        : unwrap(
            await api.POST("/api/workflows/formalize", {
              body: { description, created_by: "web" },
            }),
          ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifacts"] });
      qc.invalidateQueries({ queryKey: ["all-links"] });
    },
  });
}

export function useConsistency(projectId?: string | null) {
  return useQuery({
    queryKey: ["consistency", projectId],
    queryFn: async (): Promise<ConsistencyReport> =>
      projectId
        ? unwrap(
            await api.GET("/api/projects/{project_id}/consistency", {
              params: { path: { project_id: projectId } },
            }),
          )
        : unwrap(await api.GET("/api/consistency")),
  });
}

export function useChangeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) =>
      unwrap(
        await api.POST("/api/workflows/change-request", {
          body: { text, created_by: "web", max_impacted: 8 },
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifacts"] });
      qc.invalidateQueries({ queryKey: ["all-links"] });
    },
  });
}
