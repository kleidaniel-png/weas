import { Send } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alert, Badge, Button, Card, Heading, PageHeader, Table, Td, Textarea } from "../components/ui.jsx";
import { dateTime } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

// Farbe je Bearbeitungsstand – gilt auch für die Wunschliste der Verwaltung.
export const WISH_TONES = { neu: "amber", geplant: "neutral", erledigt: "green", abgelehnt: "red" };

// Jeder mit dem Recht „Funktionswünsche einreichen“: Wunsch schreiben, eigene Wünsche sehen.
export default function Wishes() {
  const [wishes, setWishes] = useState([]);
  const [statuses, setStatuses] = useState({});
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const load = () => api.get("/wishes/mine").then(setWishes).catch((e) => setError(e.message));
  useEffect(() => { load(); api.get("/meta").then((m) => setStatuses(m.wish_statuses)); }, []);
  useLive(load);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setDone(false);
    try {
      await api.post("/wishes", { text });
      setText("");
      setDone(true);
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <>
      <PageHeader title="Wünsche" subtitle="Welche Funktion fehlt Ihnen? Schreiben Sie es hier auf." />
      <Card className="mb-6 max-w-2xl p-5">
        <form onSubmit={submit} className="space-y-3">
          <Alert>{error}</Alert>
          <Alert kind="info">{done && "Danke! Ihr Wunsch wurde weitergegeben."}</Alert>
          <Textarea rows={4} value={text} onChange={(e) => { setDone(false); setText(e.target.value); }} required minLength={3} maxLength={2000}
                    placeholder="Was wünschen Sie sich? Wobei würde es helfen?" aria-label="Wünsche" />
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-stone-500 tabular-nums">{text.length} / 2000</span>
            <Button type="submit" disabled={text.trim().length < 3}><Send size={16} /> Wunsch absenden</Button>
          </div>
        </form>
      </Card>

      <Heading>Meine Wünsche</Heading>
      <div className="max-w-2xl">
        <Table head={["Zeit", "Wunsch", "Status"]} empty="Sie haben noch keinen Wunsch eingereicht.">
          {wishes.map((w) => (
            <tr key={w.id}>
              <Td className="whitespace-nowrap align-top text-stone-500">{dateTime(w.created_at)}</Td>
              <Td className="whitespace-pre-wrap break-words">{w.text}</Td>
              <Td className="align-top"><Badge tone={WISH_TONES[w.status]}>{statuses[w.status] ?? w.status}</Badge></Td>
            </tr>
          ))}
        </Table>
      </div>
    </>
  );
}
