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

export interface ArtifactFilters {
  type?: ArtifactType;
  status?: ArtifactStatus;
}

export function useArtifacts(filters: ArtifactFilters = {}) {
  return useQuery({
    queryKey: ["artifacts", filters],
    queryFn: async (): Promise<Artifact[]> =>
      unwrap(
        await api.GET("/api/artifacts", {
          params: { query: { ...filters, limit: 500 } },
        }),
      ),
  });
}

export function useArtifact(id: string) {
  return useQuery({
    queryKey: ["artifact", id],
    queryFn: async (): Promise<Artifact> =>
      unwrap(await api.GET("/api/artifacts/{artifact_id}", { params: { path: { artifact_id: id } } })),
    enabled: Boolean(id),
  });
}

export function useArtifactVersions(id: string) {
  return useQuery({
    queryKey: ["versions", id],
    queryFn: async (): Promise<ArtifactVersion[]> =>
      unwrap(
        await api.GET("/api/artifacts/{artifact_id}/versions", {
          params: { path: { artifact_id: id } },
        }),
      ),
    enabled: Boolean(id),
  });
}

export function useArtifactLinks(id: string) {
  return useQuery({
    queryKey: ["links", id],
    queryFn: async (): Promise<Link[]> =>
      unwrap(
        await api.GET("/api/artifacts/{artifact_id}/links", {
          params: { path: { artifact_id: id } },
        }),
      ),
    enabled: Boolean(id),
  });
}

export function useAllLinks() {
  return useQuery({
    queryKey: ["all-links"],
    queryFn: async (): Promise<Link[]> => unwrap(await api.GET("/api/links")),
  });
}

export function useCreateArtifact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      type: ArtifactType;
      title: string;
      content: string;
      status?: ArtifactStatus | null;
      source_ref?: string | null;
    }): Promise<Artifact> =>
      unwrap(await api.POST("/api/artifacts", { body: { ...body, created_by: "web" } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifacts"] });
    },
  });
}

export function useUpdateArtifact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      title?: string | null;
      content?: string | null;
      status?: ArtifactStatus | null;
      source_ref?: string | null;
      reason?: string | null;
    }): Promise<Artifact> =>
      unwrap(
        await api.PATCH("/api/artifacts/{artifact_id}", {
          params: { path: { artifact_id: id } },
          body: { ...body, updated_by: "web" },
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["artifact", id] });
      qc.invalidateQueries({ queryKey: ["versions", id] });
      qc.invalidateQueries({ queryKey: ["artifacts"] });
    },
  });
}

export function useCreateLink(artifactId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      source_id: string;
      target_id: string;
      type: Link["type"];
    }): Promise<Link> =>
      unwrap(await api.POST("/api/links", { body: { ...body, created_by: "web" } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["all-links"] });
      if (artifactId) qc.invalidateQueries({ queryKey: ["links", artifactId] });
    },
  });
}

export function useFormalize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (description: string) =>
      unwrap(
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

export function useConsistency() {
  return useQuery({
    queryKey: ["consistency"],
    queryFn: async (): Promise<ConsistencyReport> => unwrap(await api.GET("/api/consistency")),
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
