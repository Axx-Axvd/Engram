"use client";

import { TextSelection } from "@tiptap/pm/state";
import type { EditorView } from "@tiptap/pm/view";
import {
  Node,
  NodeViewContent,
  NodeViewWrapper,
  ReactNodeViewRenderer,
  mergeAttributes,
  type NodeViewProps,
} from "@tiptap/react";
import { useEffect, useRef } from "react";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    details: {
      /** Insert a collapsible toggle block. */
      setDetails: () => ReturnType;
    };
  }
}

// Focus the title input of the toggle whose node begins at detailsPos. Returns false
// when there is no such input (e.g. read-only render).
function focusToggleTitle(view: EditorView, detailsPos: number): boolean {
  const dom = view.nodeDOM(detailsPos);
  const input =
    dom instanceof HTMLElement
      ? dom.querySelector<HTMLInputElement>(".tiptap-details-summary-input")
      : null;
  if (!input) return false;
  input.focus();
  return true;
}

// Focus a toggle title that may not be in the DOM yet (its React node view renders
// asynchronously after the insert), retrying across a few animation frames.
function focusToggleTitleWhenReady(view: EditorView, detailsPos: number) {
  let tries = 0;
  const grab = () => {
    if (focusToggleTitle(view, detailsPos) || tries++ > 20) return;
    requestAnimationFrame(grab);
  };
  requestAnimationFrame(grab);
}

function DetailsView({ node, updateAttributes, editor, getPos }: NodeViewProps) {
  const open = Boolean(node.attrs.open);
  const summary = (node.attrs.summary as string) ?? "";
  const inputRef = useRef<HTMLInputElement>(null);

  // The toggle body holds nothing but a single empty paragraph: show the "/" hint there.
  const bodyEmpty =
    node.childCount === 1 &&
    node.firstChild?.type.name === "paragraph" &&
    node.firstChild.content.size === 0;

  // Move the caret to the start of the toggle body, expanding it first if collapsed.
  function moveCaretIntoBody() {
    const pos = typeof getPos === "function" ? getPos() : null;
    if (typeof pos !== "number") return;
    const { state, view } = editor;
    let tr = state.tr;
    if (!open) tr = tr.setNodeMarkup(pos, undefined, { ...node.attrs, open: true });
    tr = tr.setSelection(TextSelection.near(tr.doc.resolve(pos + 1), 1)).scrollIntoView();
    view.dispatch(tr);
    view.focus();
  }

  // Insert a fresh collapsed toggle right after this one and focus its title — so
  // repeated Enter on collapsed toggles chains them like list items.
  function createToggleAfter() {
    const pos = typeof getPos === "function" ? getPos() : null;
    if (typeof pos !== "number") return;
    const { state, view } = editor;
    const detailsType = state.schema.nodes.details;
    const paragraph = state.schema.nodes.paragraph;
    if (!detailsType || !paragraph) return;
    const end = pos + node.nodeSize;
    const fresh = detailsType.create({ open: false, summary: "" }, paragraph.create());
    // Don't move the doc selection into the new (hidden) body — that would make
    // ProseMirror pull DOM focus into the editor and fight the title focus below.
    view.dispatch(state.tr.insert(end, fresh));
    focusToggleTitleWhenReady(view, end);
  }

  // Replace the toggle with its own content (plain blocks); caret to the start.
  function unwrapToggle() {
    const pos = typeof getPos === "function" ? getPos() : null;
    if (typeof pos !== "number") return;
    const { state, view } = editor;
    const current = state.doc.nodeAt(pos);
    if (!current) return;
    const tr = state.tr.replaceWith(pos, pos + current.nodeSize, current.content);
    tr.setSelection(TextSelection.create(tr.doc, pos + 1));
    view.dispatch(tr);
    view.focus();
  }

  // ArrowUp from the title leaves upward — to the previous toggle's title, or the block above.
  function exitTitleUpward() {
    const pos = typeof getPos === "function" ? getPos() : null;
    if (typeof pos !== "number" || pos === 0) return;
    const { state, view } = editor;
    const before = state.doc.resolve(pos).nodeBefore;
    if (before?.type.name === "details" && focusToggleTitle(view, pos - before.nodeSize)) return;
    view.dispatch(state.tr.setSelection(TextSelection.near(state.doc.resolve(pos), -1)).scrollIntoView());
    view.focus();
  }

  // ArrowDown from the title leaves downward — into the body if open, else to the next
  // toggle's title or the block below.
  function exitTitleDownward() {
    const pos = typeof getPos === "function" ? getPos() : null;
    if (typeof pos !== "number") return;
    const { state, view } = editor;
    if (open) {
      view.dispatch(
        state.tr.setSelection(TextSelection.near(state.doc.resolve(pos + 1), 1)).scrollIntoView(),
      );
      view.focus();
      return;
    }
    const end = pos + node.nodeSize;
    const after = state.doc.resolve(end).nodeAfter;
    if (after?.type.name === "details" && focusToggleTitle(view, end)) return;
    if (!after) return;
    view.dispatch(state.tr.setSelection(TextSelection.near(state.doc.resolve(end), 1)).scrollIntoView());
    view.focus();
  }

  // The title input owns its own keys via a native listener: ProseMirror's keymap is
  // registered on an ancestor element, so without stopping propagation it would also
  // react to keystrokes typed in the title.
  const keyHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  // Keep the handler fresh (it closes over open/summary/bodyEmpty) without re-binding
  // the native listener on every keystroke.
  useEffect(() => {
    keyHandlerRef.current = (e: KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === "Enter") {
        e.preventDefault();
        if (open) moveCaretIntoBody();
        else if (summary.length === 0 && bodyEmpty) unwrapToggle();
        else createToggleAfter();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        exitTitleUpward();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        exitTitleDownward();
      } else if (e.key === "Backspace" && summary.length === 0) {
        e.preventDefault();
        unwrapToggle();
      }
    };
  });
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    const listener = (e: KeyboardEvent) => keyHandlerRef.current(e);
    el.addEventListener("keydown", listener);
    return () => el.removeEventListener("keydown", listener);
  }, []);

  return (
    <NodeViewWrapper className="tiptap-details" data-open={open}>
      <div className="tiptap-details-header" contentEditable={false}>
        <button
          type="button"
          className="tiptap-details-toggle"
          onClick={() => updateAttributes({ open: !open })}
          aria-label={open ? "Collapse" : "Expand"}
        >
          ▸
        </button>
        {editor.isEditable ? (
          <input
            ref={inputRef}
            className="tiptap-details-summary-input"
            value={summary}
            placeholder="Toggle title"
            onChange={(e) => updateAttributes({ summary: e.target.value })}
          />
        ) : (
          <span className="tiptap-details-summary">{summary || "Toggle"}</span>
        )}
      </div>
      <div className="tiptap-details-body" style={{ display: open ? "block" : "none" }}>
        {editor.isEditable && bodyEmpty && (
          <span className="tiptap-details-placeholder" contentEditable={false} aria-hidden="true">
            Write, or press &apos;/&apos; for commands…
          </span>
        )}
        <NodeViewContent className="tiptap-details-content" />
      </div>
    </NodeViewWrapper>
  );
}

export const Details = Node.create({
  name: "details",
  group: "block",
  content: "block+",
  defining: true,

  addAttributes() {
    return {
      open: {
        default: true,
        parseHTML: (el) => (el as HTMLElement).hasAttribute("open"),
        renderHTML: (attrs) => (attrs.open ? { open: "open" } : {}),
      },
      summary: {
        default: "",
        parseHTML: (el) => (el as HTMLElement).querySelector(":scope > summary")?.textContent ?? "",
        renderHTML: () => ({}),
      },
    };
  },

  parseHTML() {
    return [{ tag: "details" }];
  },

  renderHTML({ HTMLAttributes, node }) {
    return [
      "details",
      mergeAttributes(HTMLAttributes),
      ["summary", {}, (node.attrs.summary as string) || "Toggle"],
      ["div", { class: "tiptap-details-content" }, 0],
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(DetailsView);
  },

  addKeyboardShortcuts() {
    return {
      // The toggle title lives outside the document, so the editor has to hand focus
      // to/from it explicitly when the caret crosses a toggle boundary vertically.
      ArrowUp: ({ editor }) => {
        const { state, view } = editor;
        const { selection } = state;
        if (!selection.empty || !view.endOfTextblock("up")) return false;
        const { $from } = selection;
        // Leaving a toggle body upward from its first block → that toggle's title.
        for (let d = $from.depth; d > 0; d--) {
          if ($from.node(d).type.name === "details") {
            if ($from.index(d) !== 0) return false;
            return focusToggleTitle(view, $from.before(d));
          }
        }
        // Top-level block whose previous sibling is a toggle → that toggle's title.
        if ($from.depth === 1) {
          const index = $from.index(0);
          const prev = index > 0 ? $from.node(0).child(index - 1) : null;
          if (prev?.type.name === "details") {
            return focusToggleTitle(view, $from.before(1) - prev.nodeSize);
          }
        }
        return false;
      },
      // Top-level block whose next sibling is a toggle → that toggle's title.
      ArrowDown: ({ editor }) => {
        const { state, view } = editor;
        const { selection } = state;
        if (!selection.empty || !view.endOfTextblock("down")) return false;
        const { $from } = selection;
        if ($from.depth !== 1) return false;
        const next = $from.node(0).maybeChild($from.index(0) + 1);
        if (next?.type.name !== "details") return false;
        return focusToggleTitle(view, $from.after(1));
      },
    };
  },

  addCommands() {
    return {
      setDetails:
        () =>
        ({ commands, can }) => {
          const attrs = { open: true, summary: "" };
          // Wrap the current block(s) so existing text becomes the toggle body…
          if (can().wrapIn(this.name, attrs)) {
            return commands.wrapIn(this.name, attrs);
          }
          // …otherwise (nothing wrappable) drop in an empty toggle.
          return commands.insertContent({
            type: this.name,
            attrs,
            content: [{ type: "paragraph" }],
          });
        },
    };
  },
});
