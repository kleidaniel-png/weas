import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Button, Card, Field, Input, PageHeader, Select } from "../components/ui.jsx";

export default function Account() {
  const { user, languages, updateUser } = useAuth();
  const empty = { current_password: "", new_password: "", repeat: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function changeLanguage(e) {
    setError("");
    try { updateUser(await api.put("/auth/language", { language: e.target.value })); }
    catch (err) { setError(err.message); }
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setDone(false);
    if (form.new_password !== form.repeat) return setError("Die neuen Passwörter stimmen nicht überein.");
    try {
      await api.post("/auth/password", form);
      setForm(empty);
      setDone(true);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHeader title="Mein Konto" subtitle="Sprache und Passwort" />
      <div className="max-w-md space-y-6">
        <Alert>{error}</Alert>
        <Card className="p-6">
          <Field label="Sprache">
            <Select value={user.language} onChange={changeLanguage}>
              {Object.entries(languages).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </Select>
          </Field>
        </Card>
        <Card className="p-6">
          <form onSubmit={submit} className="space-y-4">
            <Alert kind="info">{done && "Das Passwort wurde geändert."}</Alert>
            <Field label="Aktuelles Passwort">
              <Input type="password" value={form.current_password} onChange={set("current_password")} required />
            </Field>
            <Field label="Neues Passwort" hint="Mindestens 8 Zeichen">
              <Input type="password" value={form.new_password} onChange={set("new_password")} required />
            </Field>
            <Field label="Neues Passwort wiederholen">
              <Input type="password" value={form.repeat} onChange={set("repeat")} required />
            </Field>
            <Button type="submit">Passwort ändern</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
