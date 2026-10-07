import { Camera, ExternalLink, Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { readDocument } from "../image.js";
import { Alert, Button, Field, Input, Select, Textarea } from "./ui.jsx";

const HAS_CAMERA = typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches;

// mode: "" = kein Lieferschein, "new" = neuen anlegen, sonst die Nummer (id) eines vorhandenen
export const EMPTY_NOTE = { mode: "", partner: "", number: "", file: null, fileName: "" };

// Legt den neuen Lieferschein an (samt Anhang) bzw. liefert die id des gewählten. null = keiner.
export async function ensureDeliveryNote(value, kind, projectId) {
  if (!value.mode) return null;
  if (value.mode !== "new") return Number(value.mode);
  const note = await api.post("/delivery-notes", { kind, partner: value.partner, number: value.number, project_id: projectId });
  if (value.file) await api.put(`/delivery-notes/${note.id}/file`, { data: value.file, name: value.fileName });
  return note.id;
}

// Auswahl im Buchungsformular: kind = "eingang" (Beleg des Lieferanten) oder "ausgang" (eigener Lieferschein).
export default function DeliveryNotePicker({ kind, value, onChange, notes }) {
  const fileInput = useRef(null);
  const cameraInput = useRef(null);
  const [error, setError] = useState("");
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });

  async function picked(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    try { onChange({ ...value, file: await readDocument(file), fileName: file.name }); }
    catch { setError("Die Datei konnte nicht gelesen werden."); }
  }

  return (
    <div className="space-y-3 rounded-lg border border-stone-200 p-3 dark:border-stone-700">
      <Field label="Lieferschein">
        <Select value={value.mode} onChange={(e) => onChange({ ...EMPTY_NOTE, mode: e.target.value })}>
          <option value="">{t("– keiner –")}</option>
          <option value="new">{t("+ Neuer Lieferschein")}</option>
          {notes.map((n) => <option key={n.id} value={n.id}>{[n.number || `#${n.id}`, n.partner.split("\n")[0]].filter(Boolean).join(" · ")}</option>)}
        </Select>
      </Field>

      {value.mode === "new" && kind === "eingang" && <>
        <Field label="Lieferant"><Input value={value.partner} onChange={set("partner")} maxLength={300} /></Field>
        <Field label="Lieferschein-Nr. des Lieferanten"><Input value={value.number} onChange={set("number")} maxLength={50} /></Field>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            {HAS_CAMERA && <Button variant="secondary" onClick={() => cameraInput.current.click()}><Camera size={16} /> Foto aufnehmen</Button>}
            <Button variant="secondary" onClick={() => fileInput.current.click()}><Paperclip size={16} /> Beleg anhängen</Button>
            {value.file && <Button variant="ghost" className="px-2" aria-label="Anhang entfernen" onClick={() => onChange({ ...value, file: null, fileName: "" })}><X size={16} /></Button>}
          </div>
          <p className="mt-1 text-xs text-stone-500">{value.file ? value.fileName : t("Foto oder PDF, höchstens 5 MB")}</p>
          <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={picked} />
          <input ref={fileInput} type="file" accept="image/*,application/pdf" hidden onChange={picked} />
        </div>
        <Alert>{error}</Alert>
      </>}

      {value.mode === "new" && kind === "ausgang" && (
        <Field label="Empfänger" hint="Leer lassen = Kunde und Adresse des Projekts. Die Nummer wird automatisch vergeben.">
          <Textarea value={value.partner} onChange={set("partner")} maxLength={300} />
        </Field>
      )}

      {value.mode && value.mode !== "new" && (
        <Link to={`/lieferscheine/${value.mode}`} className="inline-flex items-center gap-1 text-sm text-accent-hover hover:underline dark:text-accent-soft">
          <ExternalLink size={14} /> {t("Lieferschein öffnen")}
        </Link>
      )}
    </div>
  );
}
