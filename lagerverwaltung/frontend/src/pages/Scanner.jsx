import { ScanBarcode } from "lucide-react";
import { Card, PageHeader } from "../components/ui.jsx";
import { t } from "../i18n.js";

// Platzhalter: Die Scanner-Anbindung wird hier eingebaut.
// Ein-/Ausblenden des Tabs: Einstellungen > Allgemein > „Scanner-Tab anzeigen“.
export default function Scanner() {
  return (
    <>
      <PageHeader title="Scanner" />
      <Card className="flex flex-col items-center px-6 py-16 text-center">
        <span className="mb-4 rounded-2xl bg-stone-100 p-4 text-stone-500 dark:bg-stone-800"><ScanBarcode size={40} /></span>
        <p className="text-lg font-semibold">{t("Diese Funktion ist noch in der Entwicklung.")}</p>
        <p className="mt-2 max-w-md text-sm text-stone-500">{t("Hier werden künftig Artikel per Barcode-Scanner erfasst und gebucht.")}</p>
      </Card>
    </>
  );
}
