import { Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { t } from "../../i18n.js";
import { useLive } from "../../live.js";
import { Alert, Badge, Button, Card, Field, Input, Modal, PageHeader } from "../../components/ui.jsx";

export default function Roles() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  const load = () =>
    Promise.all([api.get("/roles"), api.get("/permissions")])
      .then(([r, p]) => { setRoles(r); setPermissions(p); })
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  useLive(load);

  const groups = [...new Set(permissions.map((p) => p.group))];
  const open = (r) => { setFormError(""); setEditing(r ? { ...r } : { name: "", permissions: [] }); };
  const toggle = (key) =>
    setEditing({
      ...editing,
      permissions: editing.permissions.includes(key)
        ? editing.permissions.filter((k) => k !== key)
        : [...editing.permissions, key],
    });

  async function save(e) {
    e.preventDefault();
    const body = { name: editing.name, permissions: editing.permissions };
    try {
      await (editing.id ? api.put(`/roles/${editing.id}`, body) : api.post("/roles", body));
      setEditing(null);
      load();
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function remove(r) {
    if (!window.confirm(t("Rolle „{0}“ wirklich löschen?", r.name))) return;
    setError("");
    try { await api.del(`/roles/${r.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Rollen & Rechte" subtitle="Legt fest, wer was im Programm darf"
                  action={<Button onClick={() => open(null)}><Plus size={16} /> Neue Rolle</Button>} />
      <div className="mb-4"><Alert>{error}</Alert></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {roles.map((r) => (
          <Card key={r.id} className="flex flex-col p-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold">{r.name}</h2>
                <p className="text-xs text-stone-500">{t("{0} Benutzer", r.user_count)}</p>
              </div>
              {r.is_system ? <Badge tone="amber">Systemrolle</Badge> : (
                <div className="whitespace-nowrap">
                  <Button variant="ghost" className="px-2" onClick={() => open(r)} aria-label="Bearbeiten"><Pencil size={16} /></Button>
                  <Button variant="ghost" className="px-2" onClick={() => remove(r)} aria-label="Löschen"><Trash2 size={16} /></Button>
                </div>
              )}
            </div>
            <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
              {r.is_system ? t("Alle Rechte (nicht änderbar)") : t("{0} von {1} Rechten", r.permissions.length, permissions.length)}
            </p>
          </Card>
        ))}
      </div>

      {editing && (
        <Modal title={editing.id ? "Rolle bearbeiten" : "Neue Rolle"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Alert>{formError}</Alert>
            <Field label="Name der Rolle">
              <Input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                     required minLength={2} autoFocus />
            </Field>
            {groups.map((group) => (
              <fieldset key={group}>
                <legend className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{t(group)}</legend>
                {permissions.filter((p) => p.group === group).map((p) => (
                  <label key={p.key} className="flex items-center gap-2 py-1 text-sm">
                    <input type="checkbox" className="size-4 accent-accent"
                           checked={editing.permissions.includes(p.key)} onChange={() => toggle(p.key)} />
                    {t(p.label)}
                  </label>
                ))}
              </fieldset>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setEditing(null)}>Abbrechen</Button>
              <Button type="submit">Speichern</Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
