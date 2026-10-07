import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import MovementTable from "../components/MovementTable.jsx";
import { Heading, PageHeader, Stat, Table, Td } from "../components/ui.jsx";
import { qty } from "../format.js";
import { t } from "../i18n.js";
import { useLive } from "../live.js";

function Tile({ label, value, to }) {
  return <Link to={to} className="block rounded-xl transition hover:ring-2 hover:ring-accent/50"><Stat label={label} value={value} /></Link>;
}

export default function Dashboard() {
  const { user, can } = useAuth();
  const [articles, setArticles] = useState(null);
  const [projects, setProjects] = useState(null);
  const [movements, setMovements] = useState(null);

  const load = () => {
    if (can("articles.view")) {
      api.get("/articles").then((a) => setArticles(a.filter((x) => x.active))).catch(() => {});
      api.get("/movements?limit=8").then(setMovements).catch(() => {});
    }
    if (can("projects.view")) api.get("/projects").then(setProjects).catch(() => {});
  };
  useEffect(load, []);
  useLive(load);

  const low = articles?.filter((a) => a.low) ?? [];
  const stay = user.idle_timeout_seconds === null;

  return (
    <>
      <PageHeader title={t("Willkommen, {0}", user.full_name || user.username)}
                  subtitle={`${t("Angemeldet als {0}", user.role)} · ${stay ? t("bleibt angemeldet") : t("automatische Abmeldung nach {0} Minuten ohne Eingabe", Math.round(user.idle_timeout_seconds / 60))}`} />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        {articles && <Tile label="Artikel im Lager" value={articles.length} to="/artikel" />}
        {articles && <Tile label="Unter Mindestbestand" value={low.length} to="/artikel" />}
        {projects && <Tile label="Aktive Projekte" value={projects.filter((p) => p.status === "aktiv").length} to="/projekte" />}
      </div>

      {low.length > 0 && <>
        <Heading>Nachbestellen</Heading>
        <div className="mb-6">
          <Table head={["Nr.", "Artikel", "Bestand", "Mindestbestand"]} right={[2, 3]}>
            {low.map((a) => (
              <tr key={a.id}>
                <Td className="text-stone-500">{a.number}</Td>
                <Td className="font-medium">{a.name}</Td>
                <Td className="text-right font-semibold tabular-nums text-red-600 dark:text-red-400">{qty(a.stock, a.unit)}</Td>
                <Td className="text-right tabular-nums">{qty(a.min_stock, a.unit)}</Td>
              </tr>
            ))}
          </Table>
        </div>
      </>}

      {movements && <>
        <Heading>Letzte Buchungen</Heading>
        <MovementTable movements={movements} />
      </>}
    </>
  );
}
