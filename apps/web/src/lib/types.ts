import type { components } from "@/lib/api/generated/schema";

export type Artifact = components["schemas"]["ArtifactRead"];
export type ArtifactVersion = components["schemas"]["ArtifactVersionRead"];
export type ArtifactItem = components["schemas"]["ArtifactItem"];
export type ItemRef = components["schemas"]["ItemRef"];
export type Link = components["schemas"]["LinkRead"];
export type FormalizeResult = components["schemas"]["FormalizeResult"];
export type ChangeImpactResult = components["schemas"]["ChangeImpactResult"];
export type ImpactedArtifact = components["schemas"]["ImpactedArtifact"];
export type ArtifactType = Artifact["type"];
export type ArtifactStatus = Artifact["status"];
export type LinkType = Link["type"];

export const ARTIFACT_TYPE_ORDER: ArtifactType[] = [
  "project_brief",
  "requirement",
  "user_story",
  "task",
  "test_case",
  "change_request",
];

export const ARTIFACT_TYPE_LABEL: Record<ArtifactType, string> = {
  project_brief: "Project brief",
  requirement: "Requirements",
  user_story: "User stories",
  task: "Tasks",
  test_case: "Test cases",
  change_request: "Change request",
};

export const ARTIFACT_TYPE_COLOR: Record<ArtifactType, string> = {
  project_brief: "#64748b", // slate (source root)
  requirement: "#6366f1", // indigo
  user_story: "#0ea5e9", // sky
  task: "#10b981", // emerald
  test_case: "#f59e0b", // amber
  change_request: "#ef4444", // red
};

/** Tailwind classes for a soft type chip. */
export const ARTIFACT_TYPE_CHIP: Record<ArtifactType, string> = {
  project_brief: "bg-slate-100 text-slate-700 ring-slate-200",
  requirement: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  user_story: "bg-sky-50 text-sky-700 ring-sky-200",
  task: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  test_case: "bg-amber-50 text-amber-700 ring-amber-200",
  change_request: "bg-red-50 text-red-700 ring-red-200",
};

/** Allowed statuses per artifact type (matches the backend status sets). */
export const STATUSES_FOR_TYPE: Record<ArtifactType, ArtifactStatus[]> = {
  project_brief: ["draft", "approved", "archived"],
  requirement: ["draft", "reviewed", "approved", "changed", "archived"],
  change_request: ["proposed", "in_review", "approved", "rejected", "applied"],
  user_story: ["draft", "active", "archived"],
  task: ["draft", "active", "archived"],
  test_case: ["draft", "active", "archived"],
};

export const LINK_TYPES: LinkType[] = [
  "refines",
  "implements",
  "tests",
  "changes",
  "depends_on",
  "derived_from",
  "related_to",
];

/** Tailwind chip classes by status family. */
export function statusChip(status: ArtifactStatus): string {
  switch (status) {
    case "approved":
    case "active":
    case "applied":
      return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    case "reviewed":
    case "in_review":
    case "proposed":
      return "bg-sky-50 text-sky-700 ring-sky-200";
    case "changed":
      return "bg-amber-50 text-amber-700 ring-amber-200";
    case "rejected":
      return "bg-red-50 text-red-700 ring-red-200";
    case "archived":
      return "bg-neutral-100 text-neutral-500 ring-neutral-200";
    default: // draft
      return "bg-neutral-100 text-neutral-600 ring-neutral-200";
  }
}
