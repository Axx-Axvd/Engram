import type { components } from "@/lib/api/generated/schema";

export type Artifact = components["schemas"]["ArtifactRead"];
export type ArtifactVersion = components["schemas"]["ArtifactVersionRead"];
export type ArtifactItem = components["schemas"]["ArtifactItem"];
export type ItemRef = components["schemas"]["ItemRef"];
export type Link = components["schemas"]["LinkRead"];
export type FormalizeResult = components["schemas"]["FormalizeResult"];
export type ChangeImpactResult = components["schemas"]["ChangeImpactResult"];
export type ImpactedArtifact = components["schemas"]["ImpactedArtifact"];
export type ConsistencyReport = components["schemas"]["ConsistencyReport"];
export type ConsistencyIssue = components["schemas"]["ConsistencyIssue"];
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

// Graph / category accents. These are the data-viz exception to the otherwise
// monochrome brand; `task` is anchored on the brand emerald.
export const ARTIFACT_TYPE_COLOR: Record<ArtifactType, string> = {
  project_brief: "#64748b", // slate (source root)
  requirement: "#8b5cf6", // violet
  user_story: "#0ea5e9", // sky
  task: "#3ecf8e", // brand emerald
  test_case: "#f59e0b", // amber
  change_request: "#ef4444", // red
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
