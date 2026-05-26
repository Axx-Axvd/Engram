import type { components } from "@/lib/api/generated/schema";

export type Artifact = components["schemas"]["ArtifactRead"];
export type Link = components["schemas"]["LinkRead"];
export type FormalizeResult = components["schemas"]["FormalizeResult"];
export type ArtifactType = Artifact["type"];
export type LinkType = Link["type"];

export const ARTIFACT_TYPE_LABEL: Record<ArtifactType, string> = {
  requirement: "Requirement",
  user_story: "User story",
  task: "Task",
  test_case: "Test case",
  change_request: "Change request",
};

export const ARTIFACT_TYPE_COLOR: Record<ArtifactType, string> = {
  requirement: "#6366f1", // indigo
  user_story: "#0ea5e9", // sky
  task: "#10b981", // emerald
  test_case: "#f59e0b", // amber
  change_request: "#ef4444", // red
};
