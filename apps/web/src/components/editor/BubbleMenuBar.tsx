"use client";

import type { Editor } from "@tiptap/react";
import { useRef, useState, type ReactNode } from "react";

import { Popover } from "@/components/overlay/Popover";

import { ColorPalette } from "./ColorPalette";

function B({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  title: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      aria-pressed={active}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className={`inline-flex h-7 min-w-7 items-center justify-center rounded px-1.5 text-sm transition-colors ${
        active
          ? "bg-primary/15 text-ink ring-1 ring-inset ring-primary/30"
          : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function ColorMenu({ editor }: { editor: Editor }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Apply but keep the popover open, so text + background can be chosen in one go.
  const applyText = (v: string | null) => {
    const c = editor.chain().focus();
    (v ? c.setColor(v) : c.unsetColor()).run();
  };
  const applyBg = (v: string | null) => {
    const c = editor.chain().focus();
    (v ? c.setHighlight({ color: v }) : c.unsetHighlight()).run();
  };
  const resetAll = () => editor.chain().focus().unsetColor().unsetHighlight().run();

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        title="Color"
        aria-label="Text and background color"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex h-7 items-center gap-0.5 rounded px-1.5 text-sm transition-colors ${
          open
            ? "bg-primary/15 text-ink ring-1 ring-inset ring-primary/30"
            : "text-ink-mute hover:bg-canvas-soft hover:text-ink"
        }`}
      >
        <span className="font-medium">A</span>
        <span className="text-[9px] opacity-70">▾</span>
      </button>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        containerRef={ref}
        className="absolute left-0 top-full z-50 mt-1.5 w-56 rounded-lg border border-hairline bg-canvas p-2 shadow-float"
      >
        <ColorPalette onText={applyText} onBg={applyBg} onReset={resetAll} />
      </Popover>
    </div>
  );
}

export function BubbleMenuBar({ editor }: { editor: Editor }) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-hairline bg-canvas p-1 shadow-float">
      <B title="Bold" active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()}>
        <span className="font-bold">B</span>
      </B>
      <B title="Italic" active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()}>
        <span className="italic">I</span>
      </B>
      <B
        title="Underline"
        active={editor.isActive("underline")}
        onClick={() => editor.chain().focus().toggleUnderline().run()}
      >
        <span className="underline">U</span>
      </B>
      <B title="Strikethrough" active={editor.isActive("strike")} onClick={() => editor.chain().focus().toggleStrike().run()}>
        <span className="line-through">S</span>
      </B>

      <span className="mx-1 h-5 w-px self-center bg-hairline" />

      <ColorMenu editor={editor} />
    </div>
  );
}
