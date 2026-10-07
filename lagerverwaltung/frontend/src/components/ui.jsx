// Wiederverwendbare Bausteine. Aussehen hier ändern = überall geändert.
// Texte (Beschriftungen, Überschriften, Meldungen) werden hier automatisch in die
// Sprache des Benutzers übersetzt – Seiten schreiben einfach den deutschen Text.
import { X } from "lucide-react";
import { t, tr } from "../i18n.js";

const TEXT_PROPS = ["title", "aria-label", "placeholder"];
function translated(props) {
  const result = { ...props };
  for (const key of TEXT_PROPS) if (typeof result[key] === "string") result[key] = t(result[key]);
  return result;
}

const variants = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  secondary: "border border-stone-300 bg-white text-stone-800 hover:bg-stone-100 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-100 dark:hover:bg-stone-700",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "text-stone-600 hover:bg-stone-300/60 dark:text-stone-300 dark:hover:bg-stone-800",
};

export function Button({ variant = "primary", className = "", children, ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition
        focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2
        dark:focus-visible:ring-offset-stone-900 disabled:opacity-50 ${variants[variant]} ${className}`}
      {...translated(props)}
    >{tr(children)}</button>
  );
}

const inputClass =
  // text-base auf dem Handy: verhindert, dass iOS beim Antippen hineinzoomt
  "w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-base sm:text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30 dark:border-stone-700 dark:bg-stone-900";

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-stone-700 dark:text-stone-300">{tr(label)}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-stone-500">{tr(hint)}</span>}
    </label>
  );
}

export const Input = (props) => <input className={inputClass} {...translated(props)} />;
export const Select = (props) => <select className={inputClass} {...props} />;
export const Textarea = (props) => <textarea rows={2} className={inputClass} {...translated(props)} />;

export function Checkbox({ label, ...props }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" className="size-4 accent-accent" {...props} />
      {tr(label)}
    </label>
  );
}

export function Card({ className = "", ...props }) {
  return (
    <div
      className={`rounded-xl border border-stone-300/70 bg-white shadow-sm dark:border-stone-700 dark:bg-stone-900 ${className}`}
      {...props}
    />
  );
}

export function Alert({ children, kind = "error" }) {
  if (!children) return null;
  const style = kind === "error"
    ? "border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
    : "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200";
  return <div role="alert" className={`rounded-lg border px-3 py-2 text-sm ${style}`}>{tr(children)}</div>;
}

export function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
    green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    red: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{tr(children)}</span>;
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold">{tr(title)}</h1>
        {subtitle && <p className="mt-1 text-sm text-stone-500">{tr(subtitle)}</p>}
      </div>
      {action}
    </div>
  );
}

// Zwischenüberschrift über Tabellen und Abschnitten
export const Heading = ({ children, className = "mb-2" }) =>
  <h2 className={`text-sm font-semibold text-stone-500 ${className}`}>{tr(children)}</h2>;

// Kennzahl-Kachel
export function Stat({ label, value }) {
  return (
    <Card className="p-5">
      <div className="text-sm text-stone-500">{tr(label)}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </Card>
  );
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onMouseDown={onClose}>
      <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto p-6" onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{tr(title)}</h2>
          <button onClick={onClose} aria-label={t("Schließen")} className="rounded p-1 hover:bg-stone-200 dark:hover:bg-stone-800">
            <X size={18} />
          </button>
        </div>
        {children}
      </Card>
    </div>
  );
}

// Tabelle: head = Spaltenüberschriften ("" für Aktionsspalten), right = rechtsbündige Spalten (Index)
export function Table({ head, right = [], empty = "Keine Einträge vorhanden.", children }) {
  const rows = Array.isArray(children) ? children.flat().filter(Boolean) : children ? [children] : [];
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-stone-200 text-left text-xs uppercase tracking-wide text-stone-500 dark:border-stone-800">
          <tr>{head.map((h, i) => <th key={i} className={`px-4 py-3 font-semibold ${right.includes(i) ? "text-right" : ""}`}>{t(h)}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
          {rows.length ? rows : (
            <tr><td colSpan={head.length} className="px-4 py-8 text-center text-stone-500">{t(empty)}</td></tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}

export const Td = ({ className = "", ...props }) => <td className={`px-4 py-3 ${className}`} {...props} />;

export function FormActions({ onCancel }) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <Button variant="secondary" onClick={onCancel}>Abbrechen</Button>
      <Button type="submit">Speichern</Button>
    </div>
  );
}
