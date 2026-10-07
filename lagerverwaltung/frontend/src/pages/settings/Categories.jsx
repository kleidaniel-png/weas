import { Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { t } from "../../i18n.js";
import { useLive } from "../../live.js";
import { Alert, Button, Field, FormActions, Input, Modal, PageHeader, Select, Table, Td } from "../../components/ui.jsx";

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [kinds, setKinds] = useState({});
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  const load = () => api.get("/categories").then(setCategories).catch((e) => setError(e.message));
  useLive(load);
  useEffect(() => { load(); api.get("/meta").then((m) => setKinds(m.category_kinds)); }, []);

  const open = (c) => { setFormError(""); setEditing(c ? { ...c } : { name: "", kind: "material" }); };

  async function save(e) {
    e.preventDefault();
    const body = { name: editing.name, kind: editing.kind };
    try {
      await (editing.id ? api.put(`/categories/${editing.id}`, body) : api.post("/categories", body));
      setEditing(null);
      load();
    } catch (err) { setFormError(err.message); }
  }

  async function remove(c) {
    if (!window.confirm(t("Kategorie „{0}“ wirklich löschen?", c.name))) return;
    setError("");
    try { await api.del(`/categories/${c.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Kategorien" subtitle="Warengruppen für Artikel"
                  action={<Button onClick={() => open(null)}><Plus size={16} /> Neue Kategorie</Button>} />
      <div className="mb-4"><Alert>{error}</Alert></div>
      <Table head={["Kategorie", "Art", "Artikel", ""]} right={[2]}>
        {categories.map((c) => (
          <tr key={c.id}>
            <Td className="font-medium">{c.name}</Td>
            <Td>{t(kinds[c.kind] ?? c.kind)}</Td>
            <Td className="text-right tabular-nums">{c.article_count}</Td>
            <Td className="py-2 text-right whitespace-nowrap">
              <Button variant="ghost" className="px-2" onClick={() => open(c)} aria-label="Bearbeiten"><Pencil size={16} /></Button>
              <Button variant="ghost" className="px-2" onClick={() => remove(c)} aria-label="Löschen"><Trash2 size={16} /></Button>
            </Td>
          </tr>
        ))}
      </Table>

      {editing && (
        <Modal title={editing.id ? "Kategorie bearbeiten" : "Neue Kategorie"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Alert>{formError}</Alert>
            <Field label="Name"><Input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} required minLength={2} autoFocus /></Field>
            <Field label="Art" hint="Material zählt zu den Projektkosten, Werkzeug wird nur ausgeliehen.">
              <Select value={editing.kind} onChange={(e) => setEditing({ ...editing, kind: e.target.value })}>
                {Object.entries(kinds).map(([k, label]) => <option key={k} value={k}>{t(label)}</option>)}
              </Select>
            </Field>
            <FormActions onCancel={() => setEditing(null)} />
          </form>
        </Modal>
      )}
    </>
  );
}
