import { Paperclip, Printer, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Alert, Badge, Button, Input, PageHeader, Select, Table, Td } from "../components/ui.jsx";
import { dateTime } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";
import DeliveryTemplate from "./DeliveryTemplate.jsx";

// Lieferscheine: Übersicht aller Belege und (mit Verwaltungsrecht) die Vorlage des eigenen Lieferscheins.
export default function DeliveryNotes() {
  const { can } = useAuth();
  const [tab, setTab] = useState("list");
  const [notes, setNotes] = useState([]);
  const [kinds, setKinds] = useState({});
  const [filter, setFilter] = useState({ kind: "", text: "" });
  const [error, setError] = useState("");

  const load = () => api.get("/delivery-notes").then(setNotes).catch((e) => setError(e.message));
  useEffect(() => { load(); api.get("/meta").then((m) => setKinds(m.delivery_kinds)); }, []);
  useLive(load);

  const text = filter.text.trim().toLowerCase();
  const shown = notes.filter((n) => (!filter.kind || n.kind === filter.kind) &&
    (!text || [n.number, n.partner, n.project, n.user].some((v) => v.toLowerCase().includes(text))));

  async function remove(n) {
    if (!window.confirm(t("Lieferschein „{0}“ wirklich löschen? Die Buchungen bleiben erhalten.", n.number || "#" + n.id))) return;
    setError("");
    try { await api.del(`/delivery-notes/${n.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Lieferscheine" subtitle="Belege der Lieferanten und eigene Lieferscheine"
                  action={can("delivery.manage") && (
                    <div className="flex gap-2">
                      <Button variant={tab === "list" ? "primary" : "secondary"} onClick={() => setTab("list")}>Übersicht</Button>
                      <Button variant={tab === "template" ? "primary" : "secondary"} onClick={() => setTab("template")}>Vorlage</Button>
                    </div>)} />
      {tab === "template" ? <DeliveryTemplate /> : <>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="w-full sm:w-72"><Input placeholder="Suchen: Nummer, Lieferant, Empfänger, Projekt" value={filter.text}
                                                 onChange={(e) => setFilter({ ...filter, text: e.target.value })} /></div>
          <div className="w-full sm:w-48">
            <Select value={filter.kind} onChange={(e) => setFilter({ ...filter, kind: e.target.value })}>
              <option value="">{t("Eingang und Ausgang")}</option>
              {Object.entries(kinds).map(([key, label]) => <option key={key} value={key}>{t(label)}</option>)}
            </Select>
          </div>
        </div>
        <div className="mb-4"><Alert>{error}</Alert></div>
        <Table head={["Nr.", "Art", "Zeit", "Lieferant / Empfänger", "Projekt", "Positionen", "Anhang", ""]} right={[5]}
               empty={notes.length ? "Kein Lieferschein passt zum Filter." : "Noch keine Lieferscheine vorhanden. Sie entstehen beim Buchen von Wareneingang und Warenausgang."}>
          {shown.map((n) => (
            <tr key={n.id}>
              <Td className="whitespace-nowrap font-medium"><Link to={`/lieferscheine/${n.id}`} className="text-accent-hover hover:underline dark:text-accent-soft">{n.number || "#" + n.id}</Link></Td>
              <Td><Badge tone={n.kind === "eingang" ? "green" : "amber"}>{n.kind_label}</Badge></Td>
              <Td className="whitespace-nowrap text-stone-500">{dateTime(n.created_at)}</Td>
              <Td>{n.partner.split("\n")[0]}</Td>
              <Td>{n.project}</Td>
              <Td className="text-right tabular-nums">{n.item_count}</Td>
              <Td>{n.file && <a href={n.file} target="_blank" rel="noreferrer" title={t("Anhang öffnen")} className="inline-flex text-accent-hover dark:text-accent-soft"><Paperclip size={16} /></a>}</Td>
              <Td className="py-2 text-right whitespace-nowrap">
                {n.kind === "ausgang" && <Link to={`/lieferscheine/${n.id}`} title={t("Drucken / PDF")} className="inline-flex rounded-lg p-2 text-stone-600 hover:bg-stone-300/60 dark:text-stone-300 dark:hover:bg-stone-800"><Printer size={16} /></Link>}
                {can("delivery.manage") && <Button variant="ghost" className="px-2" onClick={() => remove(n)} aria-label="Löschen"><Trash2 size={16} /></Button>}
              </Td>
            </tr>
          ))}
        </Table>
      </>}
    </>
  );
}
