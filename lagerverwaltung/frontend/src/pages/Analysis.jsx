import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { BarChart, BarList, StepLineChart } from "../components/charts.jsx";
import MovementTable from "../components/MovementTable.jsx";
import { Alert, Button, Card, Field, Heading, Input, PageHeader, Select, Stat, Table, Td } from "../components/ui.jsx";
import { dateTime, money, qty } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const daysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };

// Schnellwahl für den Zeitraum – hier ergänzen oder ändern.
const RANGES = [
  { label: "30 Tage", from: () => daysAgo(29) },
  { label: "90 Tage", from: () => daysAgo(89) },
  { label: "Dieses Jahr", from: () => `${new Date().getFullYear()}-01-01` },
];
const SERIES = [
  { key: "in", label: "Wareneingang", color: "var(--chart-1)" },
  { key: "out", label: "Warenausgang", color: "var(--chart-2)" },
];
const wholeEuro = (v) => money(v, 0);

function Section({ title, hint, children, className = "" }) {
  return (
    <Card className={`p-5 ${className}`}>
      <h2 className="font-semibold">{t(title)}</h2>
      {hint && <p className="mt-0.5 text-xs text-stone-500">{t(hint)}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

export default function Analysis() {
  const [filters, setFilters] = useState({ from: daysAgo(29), to: iso(new Date()), category_id: "", project_id: "", article_id: "", user: "" });
  const [options, setOptions] = useState({ categories: [], projects: [], articles: [] });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== "")).toString();
  const load = () => api.get(`/analysis?${query}`).then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [query]);
  useLive(load);

  useEffect(() => {
    Promise.all([api.get("/categories"), api.get("/projects"), api.get("/articles")])
      .then(([categories, projects, articles]) => setOptions({ categories, projects, articles }))
      .catch(() => {}); // Filterlisten sind optional (fehlende Rechte)
  }, []);

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });
  const article = options.articles.find((a) => a.id === Number(filters.article_id));

  return (
    <>
      <PageHeader title="Analyse" subtitle="Bewegungen, Verbrauch und Kosten auswerten"
                  action={<a href={`/api/analysis/export.csv?${query}`}><Button variant="secondary"><Download size={16} /> Export für Excel</Button></a>} />

      <Card className="mb-6 p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <Field label="Von"><Input type="date" value={filters.from} onChange={set("from")} /></Field>
          <Field label="Bis"><Input type="date" value={filters.to} onChange={set("to")} /></Field>
          <Field label="Kategorie">
            <Select value={filters.category_id} onChange={set("category_id")}>
              <option value="">{t("Alle")}</option>
              {options.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Field label="Projekt">
            <Select value={filters.project_id} onChange={set("project_id")}>
              <option value="">{t("Alle")}</option>
              {options.projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
          </Field>
          <Field label="Artikel">
            <Select value={filters.article_id} onChange={set("article_id")}>
              <option value="">{t("Alle")}</option>
              {options.articles.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </Field>
          <Field label="Mitarbeiter">
            <Select value={filters.user} onChange={set("user")}>
              <option value="">{t("Alle")}</option>
              {(data?.users ?? []).map((u) => <option key={u} value={u}>{u}</option>)}
            </Select>
          </Field>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {RANGES.map((r) => (
            <Button key={r.label} variant="ghost" className="px-3 py-1" onClick={() => setFilters({ ...filters, from: r.from(), to: iso(new Date()) })}>{r.label}</Button>
          ))}
          <Button variant="ghost" className="px-3 py-1" onClick={() => setFilters({ ...filters, from: "", to: "" })}>Gesamter Zeitraum</Button>
        </div>
      </Card>

      <div className="mb-4"><Alert>{error}</Alert></div>
      {data && <>
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[["Buchungen", data.kpis.count], ["Wareneingang", money(data.kpis.in_value)],
            ["Warenausgang", money(data.kpis.out_value)], ["Ladenhüter", data.kpis.slow_count]].map(([label, value]) => (
            <Stat key={label} label={label} value={value} />
          ))}
        </div>

        <Section title="Warenwert von Eingang und Ausgang" className="mb-6"
                 hint="Menge × Preis zum Zeitpunkt der Buchung. Rückgaben und Korrekturen sind hier nicht enthalten.">
          {data.series.length
            ? <BarChart data={data.series} series={SERIES} format={wholeEuro} />
            : <p className="py-8 text-center text-sm text-stone-500">{t("Keine Buchungen vorhanden.")}</p>}
        </Section>

        {article && (
          <Section title={t("Bestandsverlauf: {0}", article.name)} className="mb-6" hint={t("Bestand in {0} nach jeder Buchung", article.unit)}>
            <StepLineChart points={data.stock_history.map((p) => ({ t: p.t, value: p.stock }))}
                           format={(v) => qty(v, article.unit)} formatTime={dateTime} />
          </Section>
        )}

        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <Section title="Meistbewegte Artikel" hint="Anzahl der Buchungen">
            <BarList items={data.top_articles.map((a) => ({ label: a.name, sub: a.out ? t("· {0} ausgegeben", qty(a.out, a.unit)) : "", value: a.count }))} format={(v) => qty(v)} />
          </Section>
          <Section title="Materialverbrauch nach Projekt" hint="Ausgang abzüglich Rückgaben, ohne Werkzeug">
            <BarList items={data.by_project.map((p) => ({ label: p.name, value: p.cost }))} format={money} empty="Im Zeitraum wurde nichts auf Projekte gebucht." />
          </Section>
          <Section title="Warenausgang nach Kategorie" hint="Warenwert">
            <BarList items={data.by_category.map((c) => ({ label: c.name, value: c.value }))} format={money} />
          </Section>
          <Section title="Buchungen nach Mitarbeiter" hint="Anzahl der Buchungen">
            <BarList items={data.by_user.map((u) => ({ label: u.name, value: u.count }))} format={(v) => qty(v)} />
          </Section>
        </div>

        <Heading className="mb-1">Ladenhüter</Heading>
        <p className="mb-2 text-xs text-stone-500">{t("Material mit Bestand, aber ohne Warenausgang im gewählten Zeitraum")}</p>
        <div className="mb-6">
          <Table head={["Nr.", "Artikel", "Kategorie", "Bestand", "Gebundener Wert", "Letzter Ausgang"]} right={[3, 4]} empty="Keine Ladenhüter im Zeitraum.">
            {data.slow.map((s) => (
              <tr key={s.id}>
                <Td className="text-stone-500">{s.number}</Td>
                <Td className="font-medium">{s.name}</Td>
                <Td>{s.category}</Td>
                <Td className="text-right tabular-nums">{qty(s.stock, s.unit)}</Td>
                <Td className="text-right tabular-nums">{money(s.value)}</Td>
                <Td className="text-stone-500">{s.last_out ? dateTime(s.last_out) : t("noch nie")}</Td>
              </tr>
            ))}
          </Table>
        </div>

        <Heading>{t("Bewegungen im Zeitraum") + (data.kpis.count > 200 ? " " + t("(die letzten 200)") : "")}</Heading>
        <MovementTable movements={data.movements} />
      </>}
    </>
  );
}
