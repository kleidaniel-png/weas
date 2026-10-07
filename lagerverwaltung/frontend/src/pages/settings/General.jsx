import { DatabaseBackup } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api.js";
import { useAuth } from "../../auth.jsx";
import { Alert, Button, Card, Checkbox, Field, Input, PageHeader, Select } from "../../components/ui.jsx";
import { dateTime, fileSize } from "../../format.js";
import { t } from "../../i18n.js";

// Ein Eingabefeld je Art der Einstellung (text | number | bool | select).
function SettingInput({ setting, value, onChange }) {
  if (setting.type === "bool")
    return <Checkbox label={setting.label} checked={!!value} onChange={(e) => onChange(e.target.checked)} />;
  if (setting.type === "select")
    return (
      <Field label={setting.label}>
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
          {Object.entries(setting.options).map(([key, label]) => <option key={key} value={key}>{t(label)}</option>)}
        </Select>
      </Field>
    );
  return (
    <Field label={setting.label}>
      <Input type={setting.type} min={setting.min} max={setting.max} required value={value ?? ""}
             onChange={(e) => onChange(e.target.value)} />
    </Field>
  );
}

function Backups() {
  const [info, setInfo] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { api.get("/backup").then(setInfo).catch((e) => setError(e.message)); }, []);

  async function backupNow() {
    setError("");
    setMessage("");
    try { setInfo(await api.post("/backup")); setMessage("Die Sicherung wurde erstellt."); }
    catch (err) { setError(err.message); }
  }

  const latest = info?.backups[0];
  return (
    <Card className="max-w-md p-6">
      <h2 className="font-semibold">{t("Datensicherung")}</h2>
      <p className="mt-1 text-sm text-stone-500">{t("Die Datenbank wird täglich automatisch gesichert.")}</p>
      <div className="mt-4 space-y-3">
        <Alert>{error}</Alert>
        <Alert kind="info">{message}</Alert>
        {info && (
          <dl className="space-y-2 text-sm">
            <div><dt className="text-stone-500">{t("Letzte Sicherung")}</dt>
              <dd>{latest ? `${dateTime(latest.created)} · ${fileSize(latest.size)}` : t("Noch keine Sicherung vorhanden.")}</dd></div>
            <div><dt className="text-stone-500">{t("Vorhandene Sicherungen")}</dt><dd>{info.backups.length}</dd></div>
            <div><dt className="text-stone-500">{t("Sicherungsordner")}</dt><dd className="break-all font-mono text-xs">{info.directory}</dd></div>
          </dl>
        )}
        <Button variant="secondary" onClick={backupNow}><DatabaseBackup size={16} /> Jetzt sichern</Button>
      </div>
    </Card>
  );
}

// Das Formular entsteht automatisch aus der Einstellungsliste des Servers (registry.py).
export default function General() {
  const { refresh } = useAuth();
  const [settings, setSettings] = useState([]);
  const [values, setValues] = useState({});
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const apply = (list) => {
    setSettings(list);
    setValues(Object.fromEntries(list.map((s) => [s.key, s.value])));
  };
  useEffect(() => { api.get("/settings").then(apply).catch((e) => setError(e.message)); }, []);

  async function save(e) {
    e.preventDefault();
    setError("");
    setDone(false);
    try {
      apply(await api.put("/settings", values));
      setDone(true);
      refresh(); // Firmenname, Abmeldezeit und Scanner-Tab sofort übernehmen
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHeader title="Allgemein" subtitle="Grundeinstellungen des Programms" />
      <div className="space-y-6">
        <Card className="max-w-md p-6">
          <form onSubmit={save} className="space-y-4">
            <Alert>{error}</Alert>
            <Alert kind="info">{done && "Die Einstellungen wurden gespeichert."}</Alert>
            {settings.map((s) => (
              <SettingInput key={s.key} setting={s} value={values[s.key]}
                            onChange={(value) => setValues({ ...values, [s.key]: value })} />
            ))}
            <Button type="submit">Speichern</Button>
          </form>
        </Card>
        <Backups />
      </div>
    </>
  );
}
