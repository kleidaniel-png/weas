// Der eigene Lieferschein als Blatt (Bildschirm-Vorschau und Ausdruck).
// Aufbau und Texte kommen aus der Vorlage (Lieferscheine > Vorlage).
// Die Beschriftungen auf dem Blatt sind bewusst deutsch – unabhängig von der Sprache des Benutzers.
const LOGO_HEIGHT = { small: "14mm", medium: "22mm", large: "32mm" };
const number = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 3 });
const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
const Lines = ({ text, className = "" }) => text ? <div className={`whitespace-pre-line ${className}`}>{text}</div> : null;

export default function DeliveryNoteDocument({ note, lines, template: tp }) {
  const date = new Date(note.created_at * 1000).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
  const logo = tp.logo && <img src={tp.logo} alt="" style={{ height: LOGO_HEIGHT[tp.logo_size] ?? LOGO_HEIGHT.medium }} className="max-w-[70mm] object-contain" />;
  const centered = tp.logo_position === "center";
  const company = (
    <div className={centered ? "text-center" : tp.logo_position === "right" ? "" : "text-right"}>
      <div className="text-[13pt] font-bold">{tp.company_name}</div>
      <Lines text={tp.company_address} />
      <Lines text={tp.company_contact} className="mt-1 text-[9pt] text-neutral-600" />
    </div>
  );
  const total = lines.reduce((sum, line) => sum + line.total, 0);
  const th = "border-b-2 border-black px-2 py-1.5 text-left text-[9pt] font-semibold uppercase tracking-wide";
  const td = "border-b border-neutral-300 px-2 py-1.5 align-top";

  return (
    <div className="print-sheet mx-auto w-full max-w-[210mm] bg-white p-6 text-[11pt] leading-snug text-black shadow-lg ring-1 ring-black/10 sm:p-[15mm]">
      {centered
        ? <div className="flex flex-col items-center gap-3">{logo}{company}</div>
        : <div className={`flex items-start justify-between gap-6 ${tp.logo_position === "right" ? "flex-row-reverse" : ""}`}>{logo ?? <div />}{company}</div>}

      <div className="mt-10 flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="text-[8pt] uppercase tracking-wide text-neutral-500">Empfänger</div>
          <Lines text={note.partner || "–"} />
        </div>
        <table className="shrink-0 text-right">
          <tbody>
            <tr><td colSpan={2} className="pb-1 text-[18pt] font-bold">{tp.title}</td></tr>
            <tr><td className="pr-3 text-neutral-500">Nr.</td><td className="font-semibold">{note.number}</td></tr>
            <tr><td className="pr-3 text-neutral-500">Datum</td><td>{date}</td></tr>
            {tp.show_project && note.project && <tr><td className="pr-3 text-neutral-500">Projekt</td><td>{note.project}</td></tr>}
          </tbody>
        </table>
      </div>

      <Lines text={tp.intro_text} className="mt-8" />

      <table className="mt-6 w-full border-collapse">
        <thead>
          <tr>
            <th className={`${th} w-10`}>Pos.</th>
            {tp.show_article_number && <th className={th}>Art.-Nr.</th>}
            <th className={th}>Bezeichnung</th>
            <th className={`${th} text-right`}>Menge</th>
            <th className={th}>Einheit</th>
            {tp.show_prices && <><th className={`${th} text-right`}>Einzelpreis</th><th className={`${th} text-right`}>Gesamt</th></>}
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr key={i}>
              <td className={td}>{i + 1}</td>
              {tp.show_article_number && <td className={`${td} whitespace-nowrap`}>{line.article_number}</td>}
              <td className={td}>{line.name}</td>
              <td className={`${td} text-right tabular-nums`}>{number.format(line.quantity)}</td>
              <td className={td}>{line.unit}</td>
              {tp.show_prices && <><td className={`${td} text-right tabular-nums`}>{euro.format(line.unit_price)}</td>
                <td className={`${td} text-right tabular-nums`}>{euro.format(line.total)}</td></>}
            </tr>
          ))}
          {lines.length === 0 && <tr><td className={`${td} py-6 text-center text-neutral-500`} colSpan={7}>Noch keine Positionen gebucht.</td></tr>}
        </tbody>
        {tp.show_prices && lines.length > 0 && (
          <tfoot>
            <tr><td colSpan={tp.show_article_number ? 6 : 5} className="px-2 pt-2 text-right font-semibold">Summe</td>
              <td className="px-2 pt-2 text-right font-semibold tabular-nums">{euro.format(total)}</td></tr>
          </tfoot>
        )}
      </table>

      {note.note && <div className="mt-6"><span className="text-neutral-500">Bemerkung: </span><span className="whitespace-pre-line">{note.note}</span></div>}
      <Lines text={tp.footer_text} className="mt-8 text-[10pt]" />

      {tp.show_signatures && (
        <div className="mt-20 grid grid-cols-2 gap-12 text-[9pt] text-neutral-600">
          <div className="border-t border-black pt-1">Ware übergeben (Datum, Unterschrift)</div>
          <div className="border-t border-black pt-1">Ware erhalten (Datum, Unterschrift)</div>
        </div>
      )}
    </div>
  );
}
