import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import { t } from "./i18n.js";
import { ROUTES } from "./routes.jsx";

export default function App() {
  const { state, allows, language } = useAuth();

  if (state === "loading") return <div className="p-10 text-center text-stone-500">{t("Lädt …")}</div>;
  if (state !== "authed") return <Login setup={state === "setup"} />;

  return (
    <Layout>
      <Routes key={language}>{/* Sprachwechsel zeichnet die Seite neu */}
        {ROUTES.filter(allows).map((r) => (
          <Route key={r.path} path={r.path} element={r.element} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
