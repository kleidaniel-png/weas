import { Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { t } from "../i18n.js";
import { useLive } from "../live.js";
import { Alert, Badge, Button, Field, FormActions, Input, Modal, PageHeader, Select, Table, Td, Textarea } from "../components/ui.jsx";

const EMPTY = { number: "", name: "", customer: "", address: "", status: "aktiv", note: "" };

export default function Projects() {
  const { can } = useAuth();
  const [projects, setProjects] = useState([]);
  const [statuses, setStatuses] = useState({});
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  const load = () => api.get("/projects").then(setProjects).catch((e) => setError(e.message));
  useLive(load);
  useEffect(() => { load(); api.get("/meta").then((m) => setStatuses(m.project_statuses)); }, []);

  const open = (p) => { setFormError(""); setEditing(p ? { ...p } : { ...EMPTY }); };
  const set = (key) => (e) => setEditing({ ...editing, [key]: e.target.value });

  async function save(e) {
    e.preventDefault();
    try {
      await (editing.id ? api.put(`/projects/${editing.id}`, editing) : api.post("/projects", editing));
      setEditing(null);
      load();
    } catch (err) { setFormError(err.message); }
  }

  async function remove(p) {
    if (!window.confirm(t("Projekt „{0}“ wirklich löschen?", p.name))) return;
    setError("");
    try { await api.del(`/projects/${p.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Projekte" subtitle="Baustellen und Aufträge, auf die Ware gebucht wird"
                  action={can("projects.manage") && <Button onClick={() => open(null)}><Plus size={16} /> Neues Projekt</Button>} />
      <div className="mb-4"><Alert>{error}</Alert></div>
      <Table head={["Nr.", "Projekt", "Kunde", "Adresse", "Status", ""]} empty="Noch keine Projekte angelegt.">
        {projects.map((p) => (
          <tr key={p.id}>
            <Td className="whitespace-nowrap text-stone-500">{p.number}</Td>
            <Td className="font-medium">
              {can("projects.view") ? <Link to={`/projekte/${p.id}`} className="text-accent-hover hover:underline dark:text-accent-soft">{p.name}</Link> : p.name}
            </Td>
            <Td>{p.customer}</Td>
            <Td>{p.address}</Td>
            <Td><Badge tone={p.status === "aktiv" ? "green" : "neutral"}>{statuses[p.status] ?? p.status}</Badge></Td>
            <Td className="py-2 text-right whitespace-nowrap">
              {can("projects.manage") && <>
                <Button variant="ghost" className="px-2" onClick={() => open(p)} aria-label="Bearbeiten"><Pencil size={16} /></Button>
                <Button variant="ghost" className="px-2" onClick={() => remove(p)} aria-label="Löschen"><Trash2 size={16} /></Button>
              </>}
            </Td>
          </tr>
        ))}
      </Table>

      {editing && (
        <Modal title={editing.id ? "Projekt bearbeiten" : "Neues Projekt"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Alert>{formError}</Alert>
            <Field label="Projektname"><Input value={editing.name} onChange={set("name")} required autoFocus /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Projektnummer" hint="Leer lassen = automatisch"><Input value={editing.number} onChange={set("number")} /></Field>
              <Field label="Status">
                <Select value={editing.status} onChange={set("status")}>
                  {Object.entries(statuses).map(([k, label]) => <option key={k} value={k}>{t(label)}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Kunde"><Input value={editing.customer} onChange={set("customer")} /></Field>
            <Field label="Adresse der Baustelle"><Input value={editing.address} onChange={set("address")} /></Field>
            <Field label="Bemerkung"><Textarea value={editing.note} onChange={set("note")} /></Field>
            <FormActions onCancel={() => setEditing(null)} />
          </form>
        </Modal>
      )}
    </>
  );
}
