"use client";

import type { Editor } from "@tiptap/react";
import { useEffect, useRef, useState } from "react";

import { Popover } from "@/components/overlay/Popover";
import { useDismiss } from "@/lib/ui/useDismiss";

import { ColorPalette } from "./ColorPalette";

type Target = { pos: number; top: number; left: number };

const TURN_INTO: { label: string; run: (e: Editor) => void }[] = [
  { label: "Text", run: (e) => e.chain().focus().setParagraph().run() },
  { label: "Heading 1", run: (e) => e.chain().focus().setHeading({ level: 1 }).run() },
  { label: "Heading 2", run: (e) => e.chain().focus().setHeading({ level: 2 }).run() },
  { label: "Heading 3", run: (e) => e.chain().focus().setHeading({ level: 3 }).run() },
  { label: "Bulleted list", run: (e) => e.chain().focus().toggleBulletList().run() },
  { label: "Numbered list", run: (e) => e.chain().focus().toggleOrderedList().run() },
  { label: "Quote", run: (e) => e.chain().focus().toggleBlockquote().run() },
  { label: "Toggle", run: (e) => e.chain().focus().wrapIn("details").run() },
];

function Row({
  onClick,
  children,
  danger,
  chevron,
}: {
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
  chevron?: boolean;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-canvas-soft ${
        danger ? "text-red-500" : "text-ink"
      }`}
    >
      {children}
      {chevron && <span className="text-ink-faint">›</span>}
    </button>
  );
}

export function BlockHandle({ editor }: { editor: Editor }) {
  const [target, setTarget] = useState<Target | null>(null);
  const [menu, setMenu] = useState(false);
  const [sub, setSub] = useState<null | "turn" | "color">(null);
  const targetRef = useRef<Target | null>(null);
  const menuRef = useRef(menu);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Keep the latest target/menu in refs for the mousemove handler, which is
  // subscribed once and must read current values without re-subscribing.
  useEffect(() => {
    targetRef.current = target;
    menuRef.current = menu;
  });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (menuRef.current || !editor.isEditable) return;
      const dom = editor.view.dom as HTMLElement;
      const rect = dom.getBoundingClientRect();
      const { clientX: x, clientY: y } = e;
      const inBand = x >= rect.left - 48 && x <= rect.right && y >= rect.top && y <= rect.bottom;
      if (!inBand) {
        setTarget(null);
        return;
      }
      const probeX = Math.min(Math.max(x, rect.left + 4), rect.right - 4);
      const info = editor.view.posAtCoords({ left: probeX, top: y });
      if (!info) return;
      const $pos = editor.state.doc.resolve(info.pos);
      if ($pos.depth === 0) return;
      const blockPos = $pos.before(1);
      if (targetRef.current?.pos === blockPos) return;
      const dnode = editor.view.nodeDOM(blockPos);
      if (!dnode || dnode.nodeType !== 1) return;
      const r = (dnode as HTMLElement).getBoundingClientRect();
      setTarget({ pos: blockPos, top: r.top, left: rect.left });
    };
    document.addEventListener("mousemove", onMove);
    return () => document.removeEventListener("mousemove", onMove);
  }, [editor]);

  useDismiss(menu, close, wrapRef);

  function close() {
    setMenu(false);
    setSub(null);
  }

  function focusBlock() {
    const t = targetRef.current;
    if (t) editor.chain().focus().setTextSelection(t.pos + 1).run();
  }

  function turnInto(run: (e: Editor) => void) {
    focusBlock();
    run(editor);
    close();
  }

  function applyColor(kind: "text" | "bg" | "reset", value: string | null) {
    const t = targetRef.current;
    if (!t) return;
    const node = editor.state.doc.nodeAt(t.pos);
    if (!node) return;
    const from = t.pos + 1;
    const to = t.pos + node.nodeSize - 1;
    const chain = editor.chain().focus().setTextSelection({ from, to });
    if (kind === "text") (value ? chain.setColor(value) : chain.unsetColor()).run();
    else if (kind === "bg") (value ? chain.setHighlight({ color: value }) : chain.unsetHighlight()).run();
    else chain.unsetColor().unsetHighlight().run();
  }

  function remove() {
    const t = targetRef.current;
    if (!t) return;
    const node = editor.state.doc.nodeAt(t.pos);
    if (!node) return;
    if (editor.state.doc.childCount <= 1) {
      editor.chain().focus().clearContent(true).run();
    } else {
      editor.chain().focus().deleteRange({ from: t.pos, to: t.pos + node.nodeSize }).run();
    }
    close();
  }

  if (!target) return null;

  return (
    <div ref={wrapRef}>
      <button
        type="button"
        title="Click for actions"
        aria-label="Block actions"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => setMenu((m) => !m)}
        style={{ position: "fixed", left: target.left - 28, top: target.top + 2, zIndex: 40 }}
        className="flex h-6 w-5 items-center justify-center rounded text-base leading-none text-ink-faint transition-colors hover:bg-canvas-soft hover:text-ink"
      >
        ⠿
      </button>

      <Popover
        open={menu}
        onClose={close}
        containerRef={wrapRef}
        style={{ position: "fixed", left: target.left - 28, top: target.top + 30, zIndex: 50 }}
        className="w-56 rounded-lg border border-hairline bg-canvas p-1 shadow-float"
      >
          {sub === null && (
            <>
              <Row chevron onClick={() => setSub("turn")}>
                Turn into
              </Row>
              <Row chevron onClick={() => setSub("color")}>
                Color
              </Row>
              <Row danger onClick={remove}>
                Delete
              </Row>
            </>
          )}

          {sub === "turn" && (
            <>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setSub(null)}
                className="mb-1 flex w-full items-center gap-1 rounded px-2 py-1 text-left text-xs text-ink-faint hover:bg-canvas-soft"
              >
                ‹ Back
              </button>
              {TURN_INTO.map((o) => (
                <Row key={o.label} onClick={() => turnInto(o.run)}>
                  {o.label}
                </Row>
              ))}
            </>
          )}

          {sub === "color" && (
            <>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setSub(null)}
                className="mb-1 flex w-full items-center gap-1 rounded px-2 py-1 text-left text-xs text-ink-faint hover:bg-canvas-soft"
              >
                ‹ Back
              </button>
              <ColorPalette
                onText={(v) => applyColor("text", v)}
                onBg={(v) => applyColor("bg", v)}
                onReset={() => applyColor("reset", null)}
              />
            </>
          )}
      </Popover>
    </div>
  );
}
