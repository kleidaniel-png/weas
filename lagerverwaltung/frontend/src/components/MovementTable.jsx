import { Link } from "react-router-dom";
import { dateTime, signedQty } from "../format.js";
import { Badge, Table, Td } from "./ui.jsx";

const tones = { in: "green", out: "amber", return: "green", correction: "neutral" };

// Liste von Buchungen – wird auf mehreren Seiten verwendet.
export default function MovementTable({ movements, showProject = true }) {
  const head = ["Zeit", "Art", "Artikel", "Menge", ...(showProject ? ["Projekt"] : []), "Benutzer", "Bemerkung"];
  return (
    <Table head={head} right={[3]} empty="Noch keine Buchungen.">
      {movements.map((m) => (
        <tr key={m.id}>
          <Td className="whitespace-nowrap text-stone-500">{dateTime(m.created_at)}</Td>
          <Td><Badge tone={tones[m.type]}>{m.type_label}</Badge></Td>
          <Td><span className="font-medium">{m.article_name}</span> <span className="text-stone-500">{m.article_number}</span></Td>
          <Td className="whitespace-nowrap text-right font-medium tabular-nums">{signedQty(m.quantity, m.unit)}</Td>
          {showProject && <Td>{m.project}</Td>}
          <Td>{m.user}</Td>
          <Td className="text-stone-500">
            {m.note}
            {m.delivery_note && <Link to={`/lieferscheine/${m.delivery_note_id}`} className="ml-1 whitespace-nowrap text-accent-hover hover:underline dark:text-accent-soft">{m.delivery_note}</Link>}
          </Td>
        </tr>
      ))}
    </Table>
  );
}
