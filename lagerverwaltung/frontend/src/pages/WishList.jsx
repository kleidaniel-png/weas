import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alert, Badge, Button, Checkbox, PageHeader, Select, Table, Td } from "../components/ui.jsx";
import { dateTime } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";
import { WISH_TONES } from "./Wishes.jsx";

// Nur mit dem Recht „Alle Funktionswünsche ansehen und bearbeiten“ (Vorbelegung: Administrator).
export default function WishList() {
  const [wishes, setWishes] = useState([]);
  const [statuses, setStatuses] = useState({});
  const [openOnly, setOpenOnly] = useState(false);
  const [error, setError] = useState("");

  const load = () => api.get("/wishes").then(setWishes).catch((e) => setError(e.message));
  useEffect(() => { load(); api.get("/meta").then((m) => setStatuses(m.wish_statuses)); }, []);
  useLive(load);

  const DONE = ["erledigt", "abgelehnt"];
  const shown = wishes.filter((w) => !openOnly || !DONE.includes(w.status));

  async function setStatus(w, status) {
    setError("");
    try { await api.put(`/wishes/${w.id}`, { status }); load(); } catch (err) { setError(err.message); }
  }

  async function remove(w) {
    if (!window.confirm(t("Diesen Wunsch wirklich löschen?"))) return;
    setError("");
    try { await api.del(`/wishes/${w.id}`); load(); } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Wunschliste" subtitle={t("{0} von {1} Wünschen", shown.length, wishes.length)} />
      <div className="mb-4"><Checkbox label="Nur offene zeigen" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} /></div>
      <div className="mb-4"><Alert>{error}</Alert></div>
      <Table head={["Zeit", "Benutzer", "Wunsch", "Status", ""]} empty="Es wurden noch keine Wünsche eingereicht.">
        {shown.map((w) => (
          <tr key={w.id}>
            <Td className="whitespace-nowrap align-top text-stone-500">{dateTime(w.created_at)}</Td>
            <Td className="whitespace-nowrap align-top font-medium">{w.user}</Td>
            <Td className="whitespace-pre-wrap break-words">{w.text}</Td>
            <Td className="align-top">
              <div className="flex items-center gap-2">
                <Badge tone={WISH_TONES[w.status]}>{statuses[w.status] ?? w.status}</Badge>
                <div className="w-36">
                  <Select value={w.status} onChange={(e) => setStatus(w, e.target.value)} aria-label={t("Status")}>
                    {Object.entries(statuses).map(([key, label]) => <option key={key} value={key}>{t(label)}</option>)}
                  </Select>
                </div>
              </div>
            </Td>
            <Td className="py-2 text-right align-top">
              <Button variant="ghost" className="px-2" onClick={() => remove(w)} aria-label="Löschen"><Trash2 size={16} /></Button>
            </Td>
          </tr>
        ))}
      </Table>
    </>
  );
}
