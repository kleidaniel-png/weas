// EINE Liste für Navigation und Seiten.
// Neue Seite: Datei in pages/ anlegen und hier eine Zeile ergänzen.
// `permission` blendet den Eintrag für Benutzer ohne dieses Recht aus.
// `hidden: true` = Seite ohne Eintrag in der Navigation (z. B. Detailseiten).
// `feature` = nur sichtbar, wenn der Programmteil in den Einstellungen eingeschaltet ist.
// Beschriftungen stehen auf Deutsch hier und werden automatisch übersetzt.
import { ArrowLeftRight, ChartColumn, FileText, HardHat, Home, KeyRound, Lightbulb, ListChecks, Package, ScanBarcode, Settings, ShieldCheck, Tags, Users } from "lucide-react";
import Account from "./pages/Account.jsx";
import Analysis from "./pages/Analysis.jsx";
import Articles from "./pages/Articles.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import DeliveryNotes from "./pages/DeliveryNotes.jsx";
import DeliveryNoteView from "./pages/DeliveryNoteView.jsx";
import Movements from "./pages/Movements.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";
import Projects from "./pages/Projects.jsx";
import Scanner from "./pages/Scanner.jsx";
import Categories from "./pages/settings/Categories.jsx";
import General from "./pages/settings/General.jsx";
import Roles from "./pages/settings/Roles.jsx";
import UsersPage from "./pages/settings/Users.jsx";
import WishList from "./pages/WishList.jsx";
import Wishes from "./pages/Wishes.jsx";

export const ROUTES = [
  { path: "/", label: "Übersicht", icon: Home, element: <Dashboard /> },

  { path: "/artikel", label: "Artikel", icon: Package, element: <Articles />,
    permission: "articles.view", section: "Lager" },
  { path: "/bewegungen", label: "Warenbewegungen", icon: ArrowLeftRight, element: <Movements />,
    permission: "articles.view", section: "Lager" },
  { path: "/projekte", label: "Projekte", icon: HardHat, element: <Projects />,
    permission: "projects.view", section: "Lager" },
  { path: "/lieferscheine", label: "Lieferscheine", icon: FileText, element: <DeliveryNotes />,
    permission: "delivery.view", section: "Lager" },
  { path: "/lieferscheine/:id", element: <DeliveryNoteView />, hidden: true }, // der Server prüft das Recht
  { path: "/analyse", label: "Analyse", icon: ChartColumn, element: <Analysis />,
    permission: "analysis.view", section: "Lager" },
  { path: "/scanner", label: "Scanner", icon: ScanBarcode, element: <Scanner />,
    permission: "articles.view", feature: "scanner", section: "Lager" },
  { path: "/projekte/:id", element: <ProjectDetail />, permission: "projects.view", hidden: true },

  { path: "/einstellungen/kategorien", label: "Kategorien", icon: Tags, element: <Categories />,
    permission: "articles.manage", section: "Einstellungen" },
  { path: "/einstellungen/benutzer", label: "Benutzer", icon: Users, element: <UsersPage />,
    permission: "users.manage", section: "Einstellungen" },
  { path: "/einstellungen/rollen", label: "Rollen & Rechte", icon: ShieldCheck, element: <Roles />,
    permission: "roles.manage", section: "Einstellungen" },
  { path: "/einstellungen/allgemein", label: "Allgemein", icon: Settings, element: <General />,
    permission: "settings.manage", section: "Einstellungen" },

  { path: "/wuensche", label: "Wünsche", icon: Lightbulb, element: <Wishes />,
    permission: "wishes.create", section: "Mitmachen" },
  { path: "/wunschliste", label: "Wunschliste", icon: ListChecks, element: <WishList />,
    permission: "wishes.manage", section: "Mitmachen" },

  { path: "/konto", label: "Mein Konto", icon: KeyRound, element: <Account />, section: "Konto" },
];
