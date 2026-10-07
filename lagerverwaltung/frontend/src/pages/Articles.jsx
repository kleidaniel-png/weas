import { ArrowLeftRight, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import ImagePicker, { Thumb } from "../components/ImagePicker.jsx";
import { Alert, Badge, Button, Checkbox, Field, FormActions, Input, Modal, PageHeader, Select, Table, Td, Textarea } from "../components/ui.jsx";
import { money, qty } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

const EMPTY = { image: null, number: "", name: "", category_id: "", unit: "Stück", min_stock: 0, location: "", price: 0, active: true, note: "", initial_stock: 0 };

export default function Articles() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const [articles, setArticles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [units, setUnits] = useState([]);
  const [filter, setFilter] = useState({ text: "", category: "", lowOnly: false, inactive: false });
  const [editing, setEditing] = useState(null);
  const [preview, setPreview] = useState(null); // großes Bild
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const canBook = can("movements.in") || can("movements.out") || can("movements.correct");

  const load = () =>
    Promise.all([api.get("/articles"), api.get("/categories"), api.get("/meta")])
      .then(([a, c, m]) => { setArticles(a); setCategories(c); setUnits(m.units); })
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  useLive(load);

  const text = filter.text.trim().toLowerCase();
  const shown = articles.filter((a) =>
    (filter.inactive || a.active) &&
    (!filter.category || a.category_id === Number(filter.category)) &&
    (!filter.lowOnly || a.low) &&
    (!text || [a.name, a.number, a.location].some((v) => v.toLowerCase().includes(text))));

  const open = (a) => { setFormError(""); setEditing(a ? { ...a, initial_stock: 0 } : { ...EMPTY, category_id: categories[0]?.id ?? "" }); };
  const set = (key) => (e) => setEditing({ ...editing, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function save(e) {
    e.preventDefault();
    const body = { ...editing };
    for (const k of ["category_id", "min_stock", "price", "initial_stock"]) body[k] = Number(body[k]) || 0;
    try {
      const saved = await (editing.id ? api.put(`/articles/${editing.id}`, body) : api.post("/articles", body));
      // Bild: neu gewählt (Data-URL) -> hochladen, entfernt (null) -> löschen, sonst unverändert
      if (editing.image?.startsWith("data:")) await api.put(`/articles/${saved.id}/image`, { data: editing.image });
      else if (!editing.image && saved.image) await api.del(`/articles/${saved.id}/image`);
      setEditing(null);
      load();
    } catch (err) { setFormError(err.message); }
  }

  async function remove(a) {
    if (!window.confirm(t("Artikel „{0}“ wirklich löschen?", a.name))) return;
    setError("");
    try { await api.del(`/articles/${a.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Artikel" subtitle={t("{0} von {1} Artikeln", shown.length, articles.length)}
                  action={can("articles.manage") && <Button onClick={() => open(null)}><Plus size={16} /> Neuer Artikel</Button>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="w-full sm:w-72"><Input placeholder="Suchen: Name, Nummer, Lagerort" value={filter.text}
                                     onChange={(e) => setFilter({ ...filter, text: e.target.value })} /></div>
        <div className="w-full sm:w-48">
          <Select value={filter.category} onChange={(e) => setFilter({ ...filter, category: e.target.value })}>
            <option value="">{t("Alle Kategorien")}</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </div>
        <Checkbox label="Nur unter Mindestbestand" checked={filter.lowOnly}
                  onChange={(e) => setFilter({ ...filter, lowOnly: e.target.checked })} />
        <Checkbox label="Deaktivierte zeigen" checked={filter.inactive}
                  onChange={(e) => setFilter({ ...filter, inactive: e.target.checked })} />
      </div>
      <div className="mb-4"><Alert>{error}</Alert></div>

      <Table head={["", "Nr.", "Artikel", "Kategorie", "Bestand", "Mindestbestand", "Lagerort", "Preis", ""]} right={[4, 5, 7]}
             empty={articles.length ? "Kein Artikel passt zum Filter." : "Noch keine Artikel angelegt."}>
        {shown.map((a) => (
          <tr key={a.id} className={a.active ? "" : "opacity-50"}>
            <Td className="py-2 pr-0"><Thumb src={a.image} onClick={a.image ? () => setPreview(a) : undefined} /></Td>
            <Td className="whitespace-nowrap text-stone-500">{a.number}</Td>
            <Td className="font-medium">
              {a.name} {!a.active && <Badge>Deaktiviert</Badge>}
              {/* Handy: Bestand direkt unter dem Namen, damit man nicht seitlich wischen muss */}
              <div className={`text-xs font-normal sm:hidden ${a.low ? "text-red-600 dark:text-red-400" : "text-stone-500"}`}>{t("Bestand:")} {qty(a.stock, a.unit)}</div>
            </Td>
            <Td>{a.category}</Td>
            <Td className="whitespace-nowrap text-right font-semibold tabular-nums">
              {a.low && <Badge tone="red">Niedrig</Badge>} {qty(a.stock, a.unit)}
            </Td>
            <Td className="text-right tabular-nums text-stone-500">{a.min_stock ? qty(a.min_stock) : "–"}</Td>
            <Td>{a.location}</Td>
            <Td className="whitespace-nowrap text-right tabular-nums">{money(a.price)}</Td>
            <Td className="py-2 text-right whitespace-nowrap">
              {canBook && a.active && (
                <Button variant="ghost" className="px-2" title="Buchen" aria-label="Buchen"
                        onClick={() => navigate(`/bewegungen?artikel=${a.id}`)}><ArrowLeftRight size={16} /></Button>
              )}
              {can("articles.manage") && <>
                <Button variant="ghost" className="px-2" onClick={() => open(a)} aria-label="Bearbeiten"><Pencil size={16} /></Button>
                <Button variant="ghost" className="px-2" onClick={() => remove(a)} aria-label="Löschen"><Trash2 size={16} /></Button>
              </>}
            </Td>
          </tr>
        ))}
      </Table>

      {editing && (
        <Modal title={editing.id ? "Artikel bearbeiten" : "Neuer Artikel"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Alert>{formError}</Alert>
            <Field label="Bezeichnung"><Input value={editing.name} onChange={set("name")} required autoFocus /></Field>
            <div>
              <span className="mb-1 block text-sm font-medium text-stone-700 dark:text-stone-300">{t("Bild")}</span>
              <ImagePicker value={editing.image} onChange={(image) => setEditing({ ...editing, image })} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Artikelnummer" hint="Leer lassen = automatisch"><Input value={editing.number} onChange={set("number")} /></Field>
              <Field label="Kategorie">
                <Select value={editing.category_id} onChange={set("category_id")} required>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </Select>
              </Field>
              <Field label="Einheit">
                <Input value={editing.unit} onChange={set("unit")} list="units" required />
                <datalist id="units">{units.map((u) => <option key={u} value={u} />)}</datalist>
              </Field>
              <Field label="Preis je Einheit (€)"><Input type="number" min="0" step="0.01" value={editing.price} onChange={set("price")} /></Field>
              <Field label="Mindestbestand" hint="0 = keine Warnung"><Input type="number" min="0" step="any" value={editing.min_stock} onChange={set("min_stock")} /></Field>
              {editing.id
                ? <Field label="Bestand" hint="Änderung über „Buchen“"><Input value={qty(editing.stock, editing.unit)} disabled /></Field>
                : <Field label="Anfangsbestand"><Input type="number" min="0" step="any" value={editing.initial_stock} onChange={set("initial_stock")} /></Field>}
            </div>
            <Field label="Lagerort"><Input value={editing.location} onChange={set("location")} /></Field>
            <Field label="Bemerkung"><Textarea value={editing.note} onChange={set("note")} /></Field>
            <Checkbox label="Artikel ist aktiv" checked={editing.active} onChange={set("active")} />
            <FormActions onCancel={() => setEditing(null)} />
          </form>
        </Modal>
      )}

      {preview && (
        <Modal title={preview.name} onClose={() => setPreview(null)}>
          <img src={preview.image} alt={preview.name} className="w-full rounded-lg" />
        </Modal>
      )}
    </>
  );
}
