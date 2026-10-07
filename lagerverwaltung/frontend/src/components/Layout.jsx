import { LogOut, Menu, Moon, Sun, Timer, Warehouse, X } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { t } from "../i18n.js";
import { ROUTES } from "../routes.jsx";
import { Button } from "./ui.jsx";

function ThemeToggle() {
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("theme", next ? "dark" : "light"); } catch { /* optional */ }
    setDark(next);
  };
  return (
    <Button variant="ghost" onClick={toggle} aria-label="Hell/Dunkel umschalten" className="px-2">
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </Button>
  );
}

function IdleCountdown() {
  const { secondsLeft } = useAuth();
  if (secondsLeft === null) return null;
  const urgent = secondsLeft <= 60;
  const text = `${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, "0")}`;
  return (
    <span
      title={t("Automatische Abmeldung bei Inaktivität")}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium tabular-nums ${
        urgent ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
               : "bg-stone-200 text-stone-600 dark:bg-stone-800 dark:text-stone-400"}`}
    >
      <Timer size={14} /> {text}
    </span>
  );
}

export default function Layout({ children }) {
  const { user, company, product, allows, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false); // nur auf schmalen Bildschirmen von Bedeutung
  const visible = ROUTES.filter((r) => !r.hidden && allows(r));
  const sections = [...new Set(visible.map((r) => r.section ?? ""))];

  return (
    <div className="flex min-h-screen">
      {menuOpen && <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={() => setMenuOpen(false)} />}
      {/* Ab Breite „lg“ feste Seitenleiste, darunter ein Menü, das von links hereinfährt */}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col overflow-y-auto bg-stone-900 text-stone-300 transition-transform
                         lg:static lg:w-60 lg:translate-x-0 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center gap-2 px-5 py-5 text-white">
          <span className="rounded-lg bg-accent p-1.5"><Warehouse size={20} /></span>
          <span className="min-w-0 leading-tight" title={product.long_name}>
            <span className="block font-bold tracking-wide">{product.name}</span>
            {company && company !== product.name && <span className="block truncate text-xs text-stone-400">{company}</span>}
          </span>
          <button onClick={() => setMenuOpen(false)} aria-label={t("Schließen")} className="ml-auto rounded p-1 hover:bg-stone-800 lg:hidden"><X size={20} /></button>
        </div>
        <nav className="flex-1 space-y-4 px-3 py-2">
          {sections.map((section) => (
            <div key={section}>
              {section && <div className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{t(section)}</div>}
              {visible.filter((r) => (r.section ?? "") === section).map(({ path, label, icon: Icon }) => (
                <NavLink
                  key={path} to={path} end={path === "/"} onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition lg:py-2 ${
                      isActive ? "bg-accent text-white" : "hover:bg-stone-800 hover:text-white"}`}
                >
                  <Icon size={18} /> {t(label)}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-stone-200 bg-white px-3 py-2 sm:gap-3 sm:px-6 sm:py-3 dark:border-stone-800 dark:bg-stone-900">
          <Button variant="ghost" className="px-2 lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Menü"><Menu size={22} /></Button>
          <div className="flex-1" />
          <IdleCountdown />
          <div className="hidden text-right text-sm leading-tight sm:block">
            <div className="font-medium">{user.full_name || user.username}</div>
            <div className="text-xs text-stone-500">{user.role}</div>
          </div>
          <ThemeToggle />
          <Button variant="secondary" className="px-3" onClick={() => logout()} aria-label="Abmelden">
            <LogOut size={16} /> <span className="hidden sm:inline">{t("Abmelden")}</span>
          </Button>
        </header>
        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
