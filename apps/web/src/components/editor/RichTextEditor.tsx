"use client";

import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import TextStyle from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import { BubbleMenu, EditorContent, useEditor, type JSONContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

import { parseDocContent } from "@/lib/editor/content";

import { BlockHandle } from "./BlockHandle";
import { BubbleMenuBar } from "./BubbleMenuBar";
import { SlashMenu } from "./SlashMenu";
import { Details } from "./extensions/Details";

const extensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3, 4, 5, 6] } }),
  Underline,
  TextStyle,
  Color,
  Highlight.configure({ multicolor: true }),
  Table.configure({ resizable: true }),
  TableRow,
  TableHeader,
  TableCell,
  Details,
  Placeholder.configure({
    placeholder: ({ node, pos, editor }) => {
      // The toggle renders its own body placeholder, so never let the generic one
      // show on the details node itself (it counts as "empty" when its body is empty)…
      if (node.type.name === "details") return "";
      // …nor on anything nested inside a toggle.
      try {
        const $pos = editor.state.doc.resolve(pos);
        for (let d = $pos.depth; d >= 0; d--) {
          if ($pos.node(d).type.name === "details") return "";
        }
      } catch {
        /* position not resolvable — fall through */
      }
      return node.type.name === "heading" ? "Heading" : "Write, or press '/' for commands…";
    },
  }),
];

export function RichTextEditor({
  value,
  editable,
  onChange,
  blockHandle = true,
}: {
  value: string;
  editable: boolean;
  onChange?: (json: JSONContent) => void;
  blockHandle?: boolean;
}) {
  const editor = useEditor({
    extensions,
    content: parseDocContent(value),
    editable,
    autofocus: editable ? "end" : false,
    immediatelyRender: false,
    editorProps: { attributes: { class: "tiptap" } },
    onUpdate: ({ editor }) => onChange?.(editor.getJSON()),
  });

  useEffect(() => {
    editor?.setEditable(editable);
  }, [editor, editable]);

  // In read-only mode, keep the rendered doc in sync with external value changes
  // (e.g. navigating between documents). We never reset while editing to avoid
  // clobbering in-progress input. setContent runs flushSync internally, so defer
  // it to a microtask — calling it during the effect's commit phase makes React
  // throw "flushSync was called from inside a lifecycle method".
  useEffect(() => {
    if (!editor || editable) return;
    queueMicrotask(() => {
      if (!editor.isDestroyed) {
        editor.commands.setContent(parseDocContent(value));
      }
    });
  }, [editor, value, editable]);

  if (!editor) {
    return <div className="tiptap min-h-[2rem]" />;
  }

  return (
    <div className="relative">
      <EditorContent editor={editor} />
      {editable && (
        <BubbleMenu editor={editor} tippyOptions={{ duration: [150, 120], maxWidth: "none" }}>
          <BubbleMenuBar editor={editor} />
        </BubbleMenu>
      )}
      {editable && <SlashMenu editor={editor} />}
      {editable && blockHandle && <BlockHandle editor={editor} />}
    </div>
  );
}
