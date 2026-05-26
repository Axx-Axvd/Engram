import createClient from "openapi-fetch";

import type { paths } from "./generated/schema";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Typed client for the Engram backend. Types are generated via `pnpm gen:api`. */
export const api = createClient<paths>({ baseUrl });
