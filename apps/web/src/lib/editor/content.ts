import type { JSONContent } from "@tiptap/core";

export const EMPTY_DOC: JSONContent = { type: "doc", content: [{ type: "paragraph" }] };

export function isTiptapDoc(value: unknown): value is JSONContent {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { type?: unknown }).type === "doc" &&
    Array.isArray((value as { content?: unknown }).content)
  );
}

/** Plain/legacy text → a Tiptap doc, preserving blank-line paragraphs and single line breaks. */
export function plainTextToDoc(text: string): JSONContent {
  const paragraphs = text.replace(/\r\n/g, "\n").split(/\n{2,}/);
  return {
    type: "doc",
    content: paragraphs.map((para) => {
      const lines = para.split("\n");
      const inline: JSONContent[] = [];
      lines.forEach((line, i) => {
        if (i > 0) inline.push({ type: "hardBreak" });
        if (line) inline.push({ type: "text", text: line });
      });
      return inline.length > 0 ? { type: "paragraph", content: inline } : { type: "paragraph" };
    }),
  };
}

/**
 * Tolerant parse of the `content` field. Returns a Tiptap doc whether the stored value is
 * serialized Tiptap JSON (new documents) or raw text (seed data, change-request output).
 */
export function parseDocContent(content: string): JSONContent {
  const trimmed = content?.trim();
  if (!trimmed) return EMPTY_DOC;
  try {
    const parsed = JSON.parse(trimmed);
    if (isTiptapDoc(parsed)) return parsed;
  } catch {
    /* not JSON — treat as plain text */
  }
  return plainTextToDoc(content);
}

export function isEmptyDoc(json: JSONContent | null | undefined): boolean {
  if (!json || !Array.isArray(json.content)) return true;
  return json.content.every(
    (node) => node.type === "paragraph" && (!node.content || node.content.length === 0),
  );
}

/** Serialize for the API. Empty docs become "" so they stay compatible with `content: str`. */
export function serializeDoc(json: JSONContent): string {
  if (isEmptyDoc(json)) return "";
  return JSON.stringify(json);
}
