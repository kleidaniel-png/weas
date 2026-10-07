import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, setUnauthorizedHandler } from "./api.js";
import { getLanguage, setLanguage } from "./i18n.js";
import { startLive, stopLive, useLive } from "./live.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

const ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "wheel", "touchstart"];

export function AuthProvider({ children }) {
  const [state, setState] = useState("loading"); // loading | setup | anon | authed
  const [user, setUser] = useState(null);
  const [company, setCompany] = useState("");
  const [product, setProduct] = useState({ name: "WEAS", long_name: "Warenerfassungs- und Analysesystem" });
  const [notice, setNotice] = useState("");
  const [languages, setLanguages] = useState({ de: "Deutsch" });
  const [setupCodeRequired, setSetupCodeRequired] = useState(false);
  const [language, setLanguageState] = useState(getLanguage());
  const [secondsLeft, setSecondsLeft] = useState(null);
  const lastActivity = useRef(Date.now());

  // Sprache wechseln; alle Seiten zeichnen sich danach neu
  const changeLanguage = useCallback((code) => { setLanguage(code); setLanguageState(getLanguage()); }, []);
  const updateUser = useCallback((me) => { setUser(me); changeLanguage(me.language); }, [changeLanguage]);

  const refresh = useCallback(async () => {
    try {
      const status = await api.get("/auth/status");
      setCompany(status.company_name);
      setProduct(status.product);
      setLanguages(status.languages);
      setSetupCodeRequired(!!status.setup_code_required);
      if (status.needs_setup) return setState("setup");
      try {
        updateUser(await api.get("/auth/me"));
        lastActivity.current = Date.now();
        setState("authed");
      } catch {
        setUser(null);
        setState("anon");
      }
    } catch {
      setNotice("Der Server ist nicht erreichbar.");
      setState("anon");
    }
  }, [updateUser]);

  const logout = useCallback(async (reason = "") => {
    try { await api.post("/auth/logout"); } catch { /* Sitzung evtl. schon beendet */ }
    setUser(null);
    setNotice(reason);
    setState("anon");
  }, []);

  const signIn = useCallback((me) => {
    lastActivity.current = Date.now();
    setNotice("");
    updateUser(me);
    setState("authed");
  }, [updateUser]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setNotice("Ihre Sitzung ist abgelaufen. Bitte erneut anmelden.");
      setState("anon");
    });
  }, []);

  // Live-Abgleich: läuft nur, solange jemand angemeldet ist
  useEffect(() => {
    if (state !== "authed") return;
    startLive();
    return stopLive;
  }, [state]);

  // Geänderte Rechte, Rollen oder Einstellungen sofort übernehmen
  useLive(({ resource }) => {
    if (state !== "authed" || !["roles", "users", "settings", "*"].includes(resource)) return;
    api.get("/auth/me").then(updateUser).catch((e) => {
      if (e.status !== 401) return;
      setUser(null);
      setNotice("Ihre Sitzung wurde beendet. Bitte erneut anmelden.");
      setState("anon");
    });
    if (resource !== "users") api.get("/auth/status").then((s) => setCompany(s.company_name)).catch(() => {});
  });

  // Automatische Abmeldung bei Inaktivität
  const timeout = user?.idle_timeout_seconds ?? null;
  useEffect(() => {
    if (state !== "authed" || timeout === null) return setSecondsLeft(null);
    const touch = () => (lastActivity.current = Date.now());
    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, touch, { passive: true }));
    const timer = setInterval(() => {
      const left = Math.ceil(timeout - (Date.now() - lastActivity.current) / 1000);
      if (left <= 0) logout("Sie wurden wegen Inaktivität automatisch abgemeldet.");
      else setSecondsLeft(left);
    }, 1000);
    return () => {
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, touch));
      clearInterval(timer);
    };
  }, [state, timeout, logout]);

  const can = useCallback((perm) => !perm || !!user?.permissions.includes(perm), [user]);
  // Darf der Benutzer diese Seite sehen? (Recht vorhanden und Programmteil eingeschaltet)
  const allows = useCallback((route) => can(route.permission) && (!route.feature || !!user?.features[route.feature]), [can, user]);

  return (
    <AuthContext.Provider value={{ state, user, company, product, notice, secondsLeft, language, languages, setupCodeRequired, can, allows, signIn, logout, refresh, changeLanguage, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}
