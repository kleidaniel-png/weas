import { useEffect, useState } from "react";
import { api } from "../api.js";
import DeliveryNoteDocument from "../components/DeliveryNoteDocument.jsx";
import ImagePicker from "../components/ImagePicker.jsx";
import { Alert, Button, Card, Checkbox, Field, Heading, Input, Select, Textarea } from "../components/ui.jsx";
import { t } from "../i18n.js";

// Beispieldaten für die Vorschau
const SAMPLE_NOTE = { number: "LS-2026-0042", created_at: Date.now() / 1000, partner: "Familie Mustermann\nLindenweg 4\n50667 Köln",
                      project: "Badsanierung Mustermann", note: "" };
const SAMPLE_LINES = [
  { article_number: "A-0003", name: "Fliesenkleber flex", quantity: 6, unit: "Sack", unit_price: 12.8, total: 76.8 },
  { article_number: "A-0005", name: "Silikon transparent", quantity: 4, unit: "Stück", unit_price: 6.2, total: 24.8 },
  { article_number: "A-0002", name: "Gipskartonplatte 12,5 mm", quantity: 18, unit: "Stück", unit_price: 3.9, total: 70.2 },
];
const POSITIONS = { left: "Links", center: "Mitte", right: "Rechts" };
const SIZES = { small: "Klein", medium: "Mittel", large: "Groß" };
const OPTIONS = [["show_article_number", "Artikelnummer anzeigen"], ["show_prices", "Preise und Summe anzeigen"],
                 ["show_project", "Projekt anzeigen"], ["show_signatures", "Unterschriftsfelder anzeigen"]];

// Vorlage des eigenen Lieferscheins bearbeiten – links die Einstellungen, rechts sofort die Vorschau.
export default function DeliveryTemplate() {
  const [tp, setTp] = useState(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => { api.get("/delivery-template").then(setTp).catch((e) => setError(e.message)); }, []);
  if (!tp) return <Alert>{error}</Alert>;

  const change = (key, value) => { setDone(false); setTp({ ...tp, [key]: value }); };
  const text = (key) => ({ value: tp[key], onChange: (e) => change(key, e.target.value) });

  async function save(e) {
    e.preventDefault();
    setError("");
    try { setTp({ ...(await api.put("/delivery-template", tp)) }); setDone(true); }
    catch (err) { setError(err.message); }
  }

  // Das Logo wird sofort gespeichert; die übrigen Eingaben bleiben dabei erhalten
  async function changeLogo(image) {
    setError("");
    try {
      const saved = image ? await api.put("/delivery-template/logo", { data: image, name: "logo" }) : await api.del("/delivery-template/logo");
      setTp({ ...tp, logo: saved?.logo ?? null });
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="grid items-start gap-6 xl:grid-cols-[24rem_1fr]">
      <Card className="p-5">
        <form onSubmit={save} className="space-y-4">
          <Alert>{error}</Alert>
          <Alert kind="info">{done && "Die Vorlage wurde gespeichert."}</Alert>
          <div>
            <span className="mb-1 block text-sm font-medium text-stone-700 dark:text-stone-300">{t("Logo")}</span>
            <ImagePicker value={tp.logo} onChange={changeLogo} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Position des Logos">
              <Select value={tp.logo_position} onChange={(e) => change("logo_position", e.target.value)}>
                {Object.entries(POSITIONS).map(([key, label]) => <option key={key} value={key}>{t(label)}</option>)}
              </Select>
            </Field>
            <Field label="Größe des Logos">
              <Select value={tp.logo_size} onChange={(e) => change("logo_size", e.target.value)}>
                {Object.entries(SIZES).map(([key, label]) => <option key={key} value={key}>{t(label)}</option>)}
              </Select>
            </Field>
          </div>
          <Field label="Firmenname"><Input {...text("company_name")} maxLength={200} /></Field>
          <Field label="Anschrift"><Textarea {...text("company_address")} rows={3} maxLength={1000} /></Field>
          <Field label="Kontakt" hint="Telefon, E-Mail, Internetseite"><Textarea {...text("company_contact")} rows={2} maxLength={1000} /></Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Überschrift"><Input {...text("title")} maxLength={50} required /></Field>
            <Field label="Nummernkreis" hint="z. B. LS- ergibt LS-2026-0001"><Input {...text("number_prefix")} maxLength={10} /></Field>
          </div>
          <Field label="Text über den Positionen"><Textarea {...text("intro_text")} rows={2} maxLength={1000} /></Field>
          <Field label="Text unter den Positionen"><Textarea {...text("footer_text")} rows={3} maxLength={1000} /></Field>
          <div className="space-y-2">
            {OPTIONS.map(([key, label]) => <Checkbox key={key} label={label} checked={tp[key]} onChange={(e) => change(key, e.target.checked)} />)}
          </div>
          <Button type="submit">Speichern</Button>
        </form>
      </Card>
      <div className="min-w-0">
        <Heading>Vorschau</Heading>
        <DeliveryNoteDocument note={SAMPLE_NOTE} lines={SAMPLE_LINES} template={tp} />
      </div>
    </div>
  );
}
