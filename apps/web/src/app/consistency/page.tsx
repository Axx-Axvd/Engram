"use client";

import Link from "next/link";

import { Button, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { useConsistency } from "@/lib/queries";
import type { ConsistencyIssue } from "@/lib/types";

function IssueRow({ issue }: { issue: ConsistencyIssue }) {
  const isError = issue.severity === "error";
  return (
    <div
      className={`flex items-start gap-3 border-l-2 px-4 py-3 ${
        isError ? "border-red-500" : "border-amber-400"
      }`}
    >
      <span
        className={`mt-0.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
          isError
            ? "bg-red-50 text-red-700 ring-red-200"
            : "bg-amber-50 text-amber-700 ring-amber-200"
        }`}
      >
        {issue.severity}
      </span>
      <div className="flex-1 text-sm text-ink">
        <p>{issue.message}</p>
        {issue.artifact_id && (
          <Link
            href={`/artifacts/${issue.artifact_id}`}
            className="text-xs text-ink-secondary underline-offset-2 hover:text-primary-deep hover:underline"
          >
            {issue.artifact_title ?? "Open artifact"}
            {issue.item_key ? ` · ${issue.item_key}` : ""} →
          </Link>
        )}
      </div>
    </div>
  );
}

export default function ConsistencyPage() {
  const { data, isLoading, isError, refetch, isFetching } = useConsistency();

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
      <PageHeader
        title="Consistency"
        description="Checks across the whole project memory — coverage, references, and links."
        actions={
          <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? "Checking…" : "Re-check"}
          </Button>
        }
      />

      {isLoading && <Spinner label="Running checks…" />}
      {isError && <p className="text-sm text-red-500">Backend offline — start the API server.</p>}

      {data && (
        <>
          <Card className="flex items-center gap-4 p-4">
            <span
              className={`flex size-10 items-center justify-center rounded-full text-lg ${
                data.ok
                  ? "bg-primary/15 text-primary-deep"
                  : "bg-red-50 text-red-600"
              }`}
            >
              {data.ok ? "✓" : "!"}
            </span>
            <div className="text-sm">
              <p className="font-medium text-ink">
                {data.ok ? "All checks passed" : "Issues found"}
              </p>
              <p className="text-ink-mute">
                {data.errors} errors · {data.warnings} warnings · {data.checked_artifacts} documents
                checked
              </p>
            </div>
          </Card>

          {data.issues.length === 0 ? (
            <EmptyState
              title="No issues"
              hint="Every requirement is covered by a task and a test, references resolve, and change requests touch something."
            />
          ) : (
            <Card className="divide-y divide-hairline-cool">
              {[...data.issues]
                .sort((a, b) => (a.severity === b.severity ? 0 : a.severity === "error" ? -1 : 1))
                .map((issue, idx) => (
                  <IssueRow key={`${issue.code}-${idx}`} issue={issue} />
                ))}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
