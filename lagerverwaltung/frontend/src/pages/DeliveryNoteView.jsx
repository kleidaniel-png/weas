import { ArrowLeft, ExternalLink, Paperclip, Pencil, Printer, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import DeliveryNoteDocument from "../components/DeliveryNoteDocument.jsx";
import { Alert, Badge, Button, Card, Field, FormActions, Heading, Input, Modal, PageHeader, Table, Td, Textarea } from "../components/ui.jsx";
import { dateTime, qty } from "../format.js";
import { t } from "../i18n.js";
import { readDocument } from "../image.js";
import { useLive } from "../live.js";

// Ein Lieferschein: eigener (Ausgang) als druckbares Blatt, fremder (Eingang) mit Anhang und Positionen.
export default function DeliveryNoteView() {
  const { id } = useParams();
  const { can } = useAuth();
  const fileInput = useRef(null);
  const [data, setData] = useState(null);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = () => api.get(`/delivery-notes/${id}`).then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [id]);
  useLive(load);

  const back = <Link to="/lieferscheine" className="no-print inline-flex items-center gap-1 text-sm text-accent-hover hover:underline dark:text-accent-soft"><ArrowLeft size={16} /> {t("Alle Lieferscheine")}</Link>;
  if (!data) return <>{back}<div className="mt-4"><Alert>{error}</Alert></div></>;
  const { note, lines, template } = data;
  const own = note.kind === "ausgang";
  const mayEdit = can("delivery.manage") || can(own ? "movements.out" : "movements.in");

  async function attach(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    try { await api.put(`/delivery-notes/${id}/file`, { data: await readDocument(file), name: file.name }); load(); }
    catch (err) { setError(err.message || "Die Datei konnte nicht gelesen werden."); }
  }

  async function removeFile() {
    if (!window.confirm(t("Anhang wirklich entfernen?"))) return;
    try { await api.del(`/delivery-notes/${id}/file`); load(); } catch (err) { setError(err.message); }
  }

  async function save(e) {
    e.preventDefault();
    try { await api.put(`/delivery-notes/${id}`, editing); setEditing(null); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      {can("delivery.view") && back}
      <div className="no-print mt-3">
        <PageHeader title={`${t("Lieferschein")} ${note.number || "#" + note.id}`}
                    subtitle={`${t(note.kind_label)} · ${dateTime(note.created_at)} · ${note.user}`}
                    action={<div className="flex flex-wrap gap-2">
                      {own && <Button onClick={() => window.print()}><Printer size={16} /> Drucken / PDF</Button>}
                      {mayEdit && <Button variant="secondary" onClick={() => setEditing({ partner: note.partner, number: note.number, note: note.note })}><Pencil size={16} /> Bearbeiten</Button>}
                      {mayEdit && <Button variant="secondary" onClick={() => fileInput.current.click()}><Paperclip size={16} /> {own ? "Unterschriebenes Exemplar anhängen" : "Beleg anhängen"}</Button>}
                    </div>} />
        <input ref={fileInput} type="file" accept="image/*,application/pdf" hidden onChange={attach} />
        <div className="mb-4"><Alert>{error}</Alert></div>
        {note.file && (
          <Card className="mb-6 flex flex-wrap items-center gap-3 p-4">
            <Paperclip size={18} className="text-stone-500" />
            <a href={note.file} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-accent-hover hover:underline dark:text-accent-soft">
              {t("Anhang öffnen")} <ExternalLink size={14} />
            </a>
            <Badge>{note.file_type === "application/pdf" ? "PDF" : t("Bild")}</Badge>
            {mayEdit && <Button variant="ghost" className="ml-auto px-2" onClick={removeFile} aria-label="Anhang entfernen"><Trash2 size={16} /></Button>}
          </Card>
        )}
      </div>

      {own ? <DeliveryNoteDocument note={note} lines={lines} template={template} /> : (
        <>
          <Card className="mb-6 grid gap-4 p-5 sm:grid-cols-3">
            <div><div className="text-sm text-stone-500">{t("Lieferant")}</div><div className="whitespace-pre-line font-medium">{note.partner || "–"}</div></div>
            <div><div className="text-sm text-stone-500">{t("Lieferschein-Nr. des Lieferanten")}</div><div className="font-medium">{note.number || "–"}</div></div>
            <div><div className="text-sm text-stone-500">{t("Bemerkung")}</div><div className="whitespace-pre-line">{note.note || "–"}</div></div>
          </Card>
          {note.file && note.file_type !== "application/pdf" && <img src={note.file} alt="" className="mb-6 max-h-[70vh] rounded-lg border border-stone-300" />}
          <Heading>Gebuchte Positionen</Heading>
          <Table head={["Nr.", "Artikel", "Menge"]} right={[2]} empty="Auf diesen Lieferschein wurde noch nichts gebucht.">
            {lines.map((line, i) => (
              <tr key={i}>
                <Td className="text-stone-500">{line.article_number}</Td>
                <Td className="font-medium">{line.name}</Td>
                <Td className="text-right tabular-nums">{qty(line.quantity, line.unit)}</Td>
              </tr>
            ))}
          </Table>
        </>
      )}

      {editing && (
        <Modal title="Lieferschein bearbeiten" onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Field label={own ? "Empfänger" : "Lieferant"}><Textarea value={editing.partner} onChange={(e) => setEditing({ ...editing, partner: e.target.value })} maxLength={300} rows={3} /></Field>
            {!own && <Field label="Lieferschein-Nr. des Lieferanten"><Input value={editing.number} onChange={(e) => setEditing({ ...editing, number: e.target.value })} maxLength={50} /></Field>}
            <Field label="Bemerkung"><Textarea value={editing.note} onChange={(e) => setEditing({ ...editing, note: e.target.value })} maxLength={500} /></Field>
            <FormActions onCancel={() => setEditing(null)} />
          </form>
        </Modal>
      )}
    </>
  );
}
