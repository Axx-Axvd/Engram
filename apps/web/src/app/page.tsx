"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await api.GET("/health");
      if (error) throw new Error("Backend unreachable");
      return data;
    },
    retry: false,
  });
}

export default function Home() {
  const { data, isLoading, isError } = useHealth();

  const status = isLoading
    ? { label: "Connecting…", color: "bg-amber-400" }
    : isError
      ? { label: "Backend unreachable", color: "bg-red-500" }
      : { label: `Connected · ${data?.service} v${data?.version}`, color: "bg-emerald-500" };

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8 text-center">
      <h1 className="text-5xl font-semibold tracking-tight">Engram</h1>
      <p className="max-w-md text-balance text-neutral-500">
        Project-memory platform for long AI projects — connected, versioned artifacts with
        minimal-context retrieval.
      </p>
      <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 px-4 py-2 text-sm dark:border-neutral-800">
        <span className={`size-2 rounded-full ${status.color}`} />
        {status.label}
      </div>
    </main>
  );
}
