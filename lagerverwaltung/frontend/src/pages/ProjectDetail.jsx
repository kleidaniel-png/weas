import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import MovementTable from "../components/MovementTable.jsx";
import { Alert, Badge, Heading, PageHeader, Stat, Table, Td } from "../components/ui.jsx";
import { money, qty } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

export default function ProjectDetail() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [movements, setMovements] = useState([]);
  const [error, setError] = useState("");

  const load = () =>
    Promise.all([api.get(`/projects/${id}/summary`), api.get(`/movements?project_id=${id}&limit=1000`)])
      .then(([s, m]) => { setSummary(s); setMovements(m); })
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, [id]);
  useLive(load);

  const back = <Link to="/projekte" className="inline-flex items-center gap-1 text-sm text-accent-hover hover:underline dark:text-accent-soft"><ArrowLeft size={16} /> {t("Alle Projekte")}</Link>;
  if (error) return <>{back}<div className="mt-4"><Alert>{error}</Alert></div></>;
  if (!summary) return null;

  const { project, items, material_cost } = summary;
  const openTools = items.filter((i) => i.kind === "werkzeug" && i.open > 0);

  return (
    <>
      {back}
      <div className="mt-3" />
      <PageHeader title={project.name}
                  subtitle={[project.number, project.customer, project.address].filter(Boolean).join(" · ")}
                  action={<Badge tone={project.status === "aktiv" ? "green" : "neutral"}>{project.status === "aktiv" ? "Aktiv" : "Abgeschlossen"}</Badge>} />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Stat label="Materialkosten" value={money(material_cost)} />
        <Stat label="Gebuchte Artikel" value={items.length} />
        <Stat label="Werkzeug noch auf der Baustelle" value={openTools.length} />
      </div>

      <Heading>Auf das Projekt gebucht</Heading>
      <Table head={["Nr.", "Artikel", "Ausgegeben", "Zurück", "Offen / verbraucht", "Kosten"]} right={[2, 3, 4, 5]}
             empty="Auf dieses Projekt wurde noch nichts gebucht.">
        {items.map((i) => (
          <tr key={i.article_id}>
            <Td className="whitespace-nowrap text-stone-500">{i.number}</Td>
            <Td className="font-medium">{i.name} {i.kind === "werkzeug" && <Badge>Werkzeug</Badge>}</Td>
            <Td className="text-right tabular-nums">{qty(i.out, i.unit)}</Td>
            <Td className="text-right tabular-nums">{qty(i.returned, i.unit)}</Td>
            <Td className="text-right font-semibold tabular-nums">{qty(i.open, i.unit)}</Td>
            <Td className="text-right tabular-nums">{i.kind === "material" ? money(i.cost) : "–"}</Td>
          </tr>
        ))}
      </Table>

      <Heading className="mb-2 mt-6">Buchungen</Heading>
      <MovementTable movements={movements} showProject={false} />
    </>
  );
}
