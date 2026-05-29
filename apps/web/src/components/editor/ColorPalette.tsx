"use client";

export const TEXT_COLORS: { name: string; value: string | null }[] = [
  { name: "Default", value: null },
  { name: "Gray", value: "#787774" },
  { name: "Brown", value: "#9f6b53" },
  { name: "Orange", value: "#d9730d" },
  { name: "Yellow", value: "#cb912f" },
  { name: "Green", value: "#448361" },
  { name: "Blue", value: "#337ea9" },
  { name: "Purple", value: "#9065b0" },
  { name: "Pink", value: "#c14c8a" },
  { name: "Red", value: "#d44c47" },
];

export const BG_COLORS: { name: string; value: string | null }[] = [
  { name: "Default", value: null },
  { name: "Gray", value: "#e5e7eb" },
  { name: "Brown", value: "#e8c9a8" },
  { name: "Orange", value: "#fed7aa" },
  { name: "Yellow", value: "#fef08a" },
  { name: "Green", value: "#bbf7d0" },
  { name: "Blue", value: "#bfdbfe" },
  { name: "Purple", value: "#e9d5ff" },
  { name: "Pink", value: "#fbcfe8" },
  { name: "Red", value: "#fecaca" },
];

export function ColorPalette({
  onText,
  onBg,
  onReset,
}: {
  onText: (value: string | null) => void;
  onBg: (value: string | null) => void;
  onReset: () => void;
}) {
  return (
    <div>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={onReset}
        className="mb-1 flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-ink-mute transition-colors hover:bg-canvas-soft hover:text-ink"
      >
        <span aria-hidden>↺</span> Reset to default
      </button>

      <p className="px-1 pb-1.5 pt-1 text-xs font-medium text-ink-faint">Text color</p>
      <div className="grid grid-cols-5 gap-1">
        {TEXT_COLORS.map((c) => (
          <button
            key={`t-${c.name}`}
            type="button"
            title={c.name}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onText(c.value)}
            className="flex h-8 w-8 items-center justify-center rounded border border-hairline transition-colors hover:bg-canvas-soft"
          >
            <span className="text-sm font-semibold" style={{ color: c.value ?? "var(--color-ink)" }}>
              A
            </span>
          </button>
        ))}
      </div>

      <p className="px-1 pb-1.5 pt-2.5 text-xs font-medium text-ink-faint">Background</p>
      <div className="grid grid-cols-5 gap-1">
        {BG_COLORS.map((c) => (
          <button
            key={`b-${c.name}`}
            type="button"
            title={c.name}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onBg(c.value)}
            className="flex h-8 w-8 items-center justify-center rounded border border-hairline transition-shadow hover:ring-2 hover:ring-primary/30"
            style={{ background: c.value ?? "transparent" }}
          >
            <span className="text-sm font-semibold" style={{ color: c.value ? "#1f1f1f" : "var(--color-ink)" }}>
              A
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
