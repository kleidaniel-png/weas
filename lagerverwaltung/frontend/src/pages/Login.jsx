import { Warehouse } from "lucide-react";
import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Button, Card, Field, Input, Select } from "../components/ui.jsx";
import { t } from "../i18n.js";

// Anmeldung – und beim allerersten Start die Einrichtung des Administrators.
export default function Login({ setup }) {
  const { company, product, notice, signIn, language, languages, changeLanguage, setupCodeRequired } = useAuth();
  const [form, setForm] = useState({ username: "", full_name: "", password: "", repeat: "", code: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (setup && form.password !== form.repeat) return setError("Die Passwörter stimmen nicht überein.");
    setBusy(true);
    try {
      const { repeat, ...data } = form;
      signIn(await api.post(setup ? "/auth/setup" : "/auth/login", { ...data, language }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="mb-3 rounded-xl bg-accent p-3 text-white"><Warehouse size={28} /></span>
          <h1 className="text-2xl font-bold tracking-wide">{product.name}</h1>
          <p className="text-xs text-stone-500">{product.long_name}</p>
          {company && company !== product.name && <p className="mt-2 text-sm font-medium">{company}</p>}
          <p className="mt-1 text-sm text-stone-500">
            {setup ? t("Ersteinrichtung: Administrator-Konto anlegen") : t("Bitte anmelden")}
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <Alert kind="info">{!error && notice}</Alert>
          <Alert>{error}</Alert>
          {setup && setupCodeRequired && (
            <Field label="Einrichtungscode" hint="Steht am Server in der Datei einrichtungscode.txt im Datenordner.">
              <Input value={form.code} onChange={set("code")} required autoComplete="off" placeholder="XXXX-XXXX" />
            </Field>
          )}
          <Field label="Benutzername">
            <Input value={form.username} onChange={set("username")} autoFocus required autoComplete="username" />
          </Field>
          {setup && (
            <Field label="Vollständiger Name">
              <Input value={form.full_name} onChange={set("full_name")} />
            </Field>
          )}
          <Field label="Passwort" hint={setup ? "Mindestens 8 Zeichen" : undefined}>
            <Input type="password" value={form.password} onChange={set("password")} required
                   autoComplete={setup ? "new-password" : "current-password"} />
          </Field>
          {setup && (
            <Field label="Passwort wiederholen">
              <Input type="password" value={form.repeat} onChange={set("repeat")} required autoComplete="new-password" />
            </Field>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {setup ? "Konto anlegen" : "Anmelden"}
          </Button>
        </form>
        {/* Sprache der Anmeldeseite; nach der Anmeldung gilt die Sprache des Benutzers */}
        <div className="mt-6">
          <Select value={language} onChange={(e) => changeLanguage(e.target.value)} aria-label={t("Sprache")}>
            {Object.entries(languages).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </Select>
        </div>
      </Card>
    </div>
  );
}
