import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import DeliveryNotePicker, { EMPTY_NOTE, ensureDeliveryNote } from "../components/DeliveryNotePicker.jsx";
import MovementTable from "../components/MovementTable.jsx";
import { Alert, Button, Card, Field, Heading, Input, PageHeader, Select } from "../components/ui.jsx";
import { qty } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

export default function Movements() {
  const { can } = useAuth();
  const [params] = useSearchParams();
  const [types, setTypes] = useState({});
  const [articles, setArticles] = useState([]);
  const [projects, setProjects] = useState([]);
  const [movements, setMovements] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ type: "", article_id: params.get("artikel") ?? "", quantity: "", project_id: "", note: "" });
  const [delivery, setDelivery] = useState(EMPTY_NOTE); // Lieferschein zur Buchung
  const [notes, setNotes] = useState([]);              // zuletzt angelegte Lieferscheine dieser Art
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  const allowed = Object.entries(types).filter(([, t]) => can(t.permission));
  const type = types[form.type];
  const article = articles.find((a) => a.id === Number(form.article_id));
  const isCorrection = form.type === "correction";

  const loadData = () =>
    Promise.all([api.get("/articles"), api.get("/movements?limit=100")])
      .then(([a, m]) => { setArticles(a.filter((x) => x.active)); setMovements(m); });

  useEffect(() => {
    api.get("/meta").then((m) => {
      setTypes(m.movement_types);
      const first = Object.entries(m.movement_types).find(([, t]) => can(t.permission));
      setForm((f) => ({ ...f, type: first?.[0] ?? "" }));
    });
    if (can("movements.out") || can("projects.view"))
      api.get("/projects").then((p) => setProjects(p.filter((x) => x.status === "aktiv")));
    loadData().catch((e) => setError(e.message));
  }, []);

  useLive(() => loadData().catch(() => {}));

  const loadNotes = (kind) => api.get(`/delivery-notes?kind=${kind}&recent=1`).then(setNotes).catch(() => setNotes([]));
  useEffect(() => {  // Art der Buchung gewechselt: Lieferschein-Auswahl zurücksetzen
    setDelivery(EMPTY_NOTE);
    if (type?.delivery) loadNotes(type.delivery); else setNotes([]);
  }, [form.type, type?.delivery]);

  function chooseDelivery(value) {
    setDelivery(value);
    // Gehört der gewählte Lieferschein zu einem Projekt, dieses gleich übernehmen
    const chosen = notes.find((n) => String(n.id) === value.mode);
    if (chosen?.project_id) setForm((f) => ({ ...f, project_id: String(chosen.project_id) }));
  }

  const text = search.trim().toLowerCase();
  const options = articles.filter((a) => !text || a.id === article?.id || `${a.number} ${a.name}`.toLowerCase().includes(text));
  const set = (key) => (e) => { setDone(""); setForm({ ...form, [key]: e.target.value }); };

  async function submit(e) {
    e.preventDefault();
    setError("");
    setDone("");
    try {
      const projectId = type.project && form.project_id ? Number(form.project_id) : null;
      // Lieferschein zuerst anlegen; er bleibt für die nächsten Artikel ausgewählt
      const noteId = type.delivery ? await ensureDeliveryNote(delivery, type.delivery, projectId) : null;
      if (noteId && delivery.mode === "new") {
        setDelivery({ ...EMPTY_NOTE, mode: String(noteId) });
        loadNotes(type.delivery);
      }
      const m = await api.post("/movements", {
        type: form.type, article_id: Number(form.article_id), quantity: Number(form.quantity),
        project_id: projectId, note: form.note, delivery_note_id: noteId,
      });
      setForm({ ...form, quantity: "", note: "" });
      await loadData();
      setDone(t("Gebucht: {0} – {1}.", t(m.type_label), m.article_name));
    } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Warenbewegungen" subtitle="Eingang, Ausgang, Rückgabe und Bestandskorrektur buchen" />
      <div className="grid items-start gap-6 xl:grid-cols-[22rem_1fr]">
        {allowed.length > 0 && (
          <Card className="p-5">
            <form onSubmit={submit} className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                {allowed.map(([key, t]) => (
                  <Button key={key} variant={form.type === key ? "primary" : "secondary"}
                          onClick={() => { setDone(""); setForm({ ...form, type: key, quantity: "" }); }}>{t.label}</Button>
                ))}
              </div>
              <Alert>{error}</Alert>
              <Alert kind="info">{done}</Alert>
              <Field label="Artikel">
                <div className="space-y-2">
                  <Input placeholder="Artikel suchen …" value={search} onChange={(e) => setSearch(e.target.value)} />
                  <Select value={form.article_id} onChange={set("article_id")} required size={6}>
                    {options.map((a) => <option key={a.id} value={a.id}>{a.number} · {a.name}</option>)}
                  </Select>
                </div>
              </Field>
              {article && (
                <p className="text-sm text-stone-600 dark:text-stone-400">
                  {t("Aktueller Bestand:")} <strong>{qty(article.stock, article.unit)}</strong>
                  {article.location && <> · {t("Lagerort:")} {article.location}</>}
                </p>
              )}
              <Field label={isCorrection ? t("Gezählter Bestand (neu)") : t("Menge") + (article ? ` (${article.unit})` : "")}>
                <Input type="number" step="any" min={isCorrection ? 0 : undefined} value={form.quantity} onChange={set("quantity")} required />
              </Field>
              {type?.project && (
                <Field label="Projekt">
                  <Select value={form.project_id} onChange={set("project_id")}>
                    <option value="">{t("– ohne Projekt –")}</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.number} · {p.name}</option>)}
                  </Select>
                </Field>
              )}
              {type?.delivery && <DeliveryNotePicker kind={type.delivery} value={delivery} onChange={chooseDelivery} notes={notes} />}
              <Field label="Bemerkung"><Input value={form.note} onChange={set("note")} maxLength={300} /></Field>
              <Button type="submit" className="w-full" disabled={!form.article_id}>{t("{0} buchen", t(type?.label ?? ""))}</Button>
            </form>
          </Card>
        )}
        <div className="min-w-0">
          <Heading>Letzte Buchungen</Heading>
          <MovementTable movements={movements} />
        </div>
      </div>
    </>
  );
}
