"use client";

import type { Editor } from "@tiptap/react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Popover } from "@/components/overlay/Popover";

type Range = { from: number; to: number };

type Cmd = {
  title: string;
  hint?: string;
  keywords: string;
  run: (editor: Editor, range: Range) => void;
};

const COMMANDS: Cmd[] = [
  {
    title: "Heading 1",
    keywords: "h1 title big",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleHeading({ level: 1 }).run(),
  },
  {
    title: "Heading 2",
    keywords: "h2 subtitle",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleHeading({ level: 2 }).run(),
  },
  {
    title: "Heading 3",
    keywords: "h3",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleHeading({ level: 3 }).run(),
  },
  {
    title: "Bulleted list",
    keywords: "ul unordered bullet",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleBulletList().run(),
  },
  {
    title: "Numbered list",
    keywords: "ol ordered number",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleOrderedList().run(),
  },
  {
    title: "Quote",
    keywords: "blockquote citation",
    run: (e, r) => e.chain().focus().deleteRange(r).toggleBlockquote().run(),
  },
  {
    title: "Toggle",
    hint: "collapsible block",
    keywords: "details collapsible expand fold",
    run: (e, r) => e.chain().focus().deleteRange(r).setDetails().run(),
  },
  {
    title: "Table",
    hint: "3×3",
    keywords: "grid rows columns",
    run: (e, r) =>
      e.chain().focus().deleteRange(r).insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  },
  {
    title: "Divider",
    keywords: "hr horizontal rule separator",
    run: (e, r) => e.chain().focus().deleteRange(r).setHorizontalRule().run(),
  },
];

type MenuState = { range: Range; left: number; top: number; query: string };

export function SlashMenu({ editor }: { editor: Editor }) {
  const [state, setState] = useState<MenuState | null>(null);
  const [index, setIndex] = useState(0);

  const items = state
    ? COMMANDS.filter((c) =>
        `${c.title} ${c.keywords}`.toLowerCase().includes(state.query.toLowerCase()),
      )
    : [];

  const itemsRef = useRef(items);
  const indexRef = useRef(index);
  const stateRef = useRef(state);
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    itemsRef.current = items;
    indexRef.current = index;
    stateRef.current = state;
  });

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest" });
  }, [index]);

  useEffect(() => {
    const update = () => {
      if (!editor.isEditable) return setState(null);
      const { selection } = editor.state;
      if (!selection.empty) return setState(null);
      const { $from } = selection;
      const textBefore = $from.parent.textBetween(0, $from.parentOffset, "\n", "￼");
      const match = /(?:^|\s)\/(\w*)$/.exec(textBefore);
      if (!match) return setState(null);
      const query = match[1];
      const to = selection.from;
      const from = to - query.length - 1;
      try {
        const c = editor.view.coordsAtPos(to);
        setState({ range: { from, to }, left: c.left, top: c.bottom, query });
        setIndex(0);
      } catch {
        setState(null);
      }
    };
    editor.on("selectionUpdate", update);
    editor.on("update", update);
    return () => {
      editor.off("selectionUpdate", update);
      editor.off("update", update);
    };
  }, [editor]);

  const exec = useCallback(
    (cmd: Cmd) => {
      const st = stateRef.current;
      if (st) cmd.run(editor, st.range);
      setState(null);
    },
    [editor],
  );

  useEffect(() => {
    if (!state) return;
    const onKey = (ev: KeyboardEvent) => {
      const list = itemsRef.current;
      if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
        setState(null);
        return;
      }
      if (!list.length) return;
      if (ev.key === "ArrowDown") {
        ev.preventDefault();
        ev.stopPropagation();
        setIndex((i) => (i + 1) % list.length);
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        ev.stopPropagation();
        setIndex((i) => (i - 1 + list.length) % list.length);
      } else if (ev.key === "Enter") {
        ev.preventDefault();
        ev.stopPropagation();
        exec(list[indexRef.current] ?? list[0]);
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [state, exec]);

  const open = !!state && items.length > 0;
  // Retain the last visible position + items so the menu can animate out after
  // `state` clears (e.g. selecting a command or the query no longer matching).
  // Set-state-during-render, keyed so it only updates on a real change.
  const [snap, setSnap] = useState<{ key: string; left: number; top: number; list: Cmd[] } | null>(
    null,
  );
  if (open && state) {
    const key = `${state.left}:${state.top}:${state.query}`;
    if (snap?.key !== key) setSnap({ key, left: state.left, top: state.top, list: items });
  }
  if (!snap) return null;

  return (
    <Popover
      open={open}
      onClose={() => setState(null)}
      role="menu"
      className="slash-menu"
      style={{ left: snap.left, top: snap.top + 6 }}
    >
      {snap.list.map((cmd, i) => (
        <button
          key={cmd.title}
          ref={i === index ? activeRef : undefined}
          type="button"
          onMouseDown={(e) => {
            e.preventDefault();
            exec(cmd);
          }}
          onMouseEnter={() => setIndex(i)}
          className={`slash-item ${i === index ? "is-active" : ""}`}
        >
          <span className="font-normal text-ink">{cmd.title}</span>
          {cmd.hint && <span className="text-xs text-ink-faint">{cmd.hint}</span>}
        </button>
      ))}
    </Popover>
  );
}
