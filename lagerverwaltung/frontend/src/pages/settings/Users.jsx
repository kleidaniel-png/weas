import { Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { t } from "../../i18n.js";
import { useLive } from "../../live.js";
import { useAuth } from "../../auth.jsx";
import { Alert, Badge, Button, Checkbox, Field, FormActions, Input, Modal, PageHeader, Select, Table, Td } from "../../components/ui.jsx";

export default function Users() {
  const { user: me, languages } = useAuth();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [editing, setEditing] = useState(null); // null | Formularobjekt
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");

  const load = () =>
    Promise.all([api.get("/users"), api.get("/roles")])
      .then(([u, r]) => { setUsers(u); setRoles(r); })
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  useLive(load);

  const open = (u) => {
    setFormError("");
    setEditing(u ? { ...u, password: "" }
                 : { username: "", full_name: "", role_id: roles.at(-1)?.id, active: true, language: "de", is_terminal: false, password: "" });
  };
  const set = (key, value) => setEditing({ ...editing, [key]: value });

  async function save(e) {
    e.preventDefault();
    const body = { ...editing, role_id: Number(editing.role_id), password: editing.password || null };
    try {
      await (editing.id ? api.put(`/users/${editing.id}`, body) : api.post("/users", body));
      setEditing(null);
      load();
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function remove(u) {
    if (!window.confirm(t("Benutzer „{0}“ wirklich löschen?", u.username))) return;
    setError("");
    try { await api.del(`/users/${u.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Benutzer" subtitle="Konten anlegen, Rollen zuweisen, sperren"
                  action={<Button onClick={() => open(null)}><Plus size={16} /> Neuer Benutzer</Button>} />
      <div className="mb-4"><Alert>{error}</Alert></div>
      <Table head={["Benutzername", "Vollständiger Name", "Rolle", "Sprache", "Status", ""]}>
        {users.map((u) => (
          <tr key={u.id}>
            <Td className="font-medium">{u.username} {u.is_terminal && <Badge tone="amber">Terminal</Badge>}</Td>
            <Td>{u.full_name}</Td>
            <Td>{u.role}</Td>
            <Td>{languages[u.language] ?? u.language}</Td>
            <Td>{u.active ? <Badge tone="green">Aktiv</Badge> : <Badge>Gesperrt</Badge>}</Td>
            <Td className="py-2 text-right whitespace-nowrap">
              <Button variant="ghost" className="px-2" onClick={() => open(u)} aria-label="Bearbeiten"><Pencil size={16} /></Button>
              {u.id !== me.id && (
                <Button variant="ghost" className="px-2" onClick={() => remove(u)} aria-label="Löschen"><Trash2 size={16} /></Button>
              )}
            </Td>
          </tr>
        ))}
      </Table>

      {editing && (
        <Modal title={editing.id ? "Benutzer bearbeiten" : "Neuer Benutzer"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <Alert>{formError}</Alert>
            <Field label="Benutzername">
              <Input value={editing.username} onChange={(e) => set("username", e.target.value)} required minLength={2} autoFocus />
            </Field>
            <Field label="Vollständiger Name">
              <Input value={editing.full_name} onChange={(e) => set("full_name", e.target.value)} />
            </Field>
            <Field label="Rolle">
              <Select value={editing.role_id} onChange={(e) => set("role_id", e.target.value)}>
                {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </Select>
            </Field>
            <Field label={editing.id ? "Neues Passwort" : "Passwort"}
                   hint={editing.id ? "Leer lassen, um das Passwort nicht zu ändern" : "Mindestens 8 Zeichen"}>
              <Input type="password" value={editing.password} onChange={(e) => set("password", e.target.value)}
                     required={!editing.id} autoComplete="new-password" />
            </Field>
            <Field label="Sprache">
              <Select value={editing.language} onChange={(e) => set("language", e.target.value)}>
                {Object.entries(languages).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
              </Select>
            </Field>
            <div>
              <Checkbox label="Terminal-Benutzer" checked={editing.is_terminal} onChange={(e) => set("is_terminal", e.target.checked)} />
              <p className="mt-1 text-xs text-stone-500">{t("Am Terminal des Servers wird die Tastatur auf die Sprache dieses Benutzers umgestellt.")}</p>
            </div>
            <Checkbox label="Konto ist aktiv" checked={editing.active} onChange={(e) => set("active", e.target.checked)} />
            <FormActions onCancel={() => setEditing(null)} />
          </form>
        </Modal>
      )}
    </>
  );
}
