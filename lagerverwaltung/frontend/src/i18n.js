// Mehrsprachigkeit. Deutsch ist die Ausgangssprache: t("Speichern") liefert den
// Text in der aktuellen Sprache. Die Übersetzungen stehen in locales/<sprache>.js.
// Neue Sprache: Datei in locales/ anlegen, hier eintragen und im Server in
// registry.py (LANGUAGES) ergänzen.
import en from "./locales/en.js";
import ru from "./locales/ru.js";
import uk from "./locales/uk.js";

const DICTIONARIES = { en, ru, uk };
export const LOCALES = { de: "de-DE", en: "en-GB", ru: "ru-RU", uk: "uk-UA" }; // Zahlen- und Datumsformat

let language = "de";
try { language = localStorage.getItem("lang") || "de"; } catch { /* ohne Speicher: Deutsch */ }
if (!(language in LOCALES)) language = "de";
document.documentElement.lang = language;

export const getLanguage = () => language;
export const locale = () => LOCALES[language];

export function setLanguage(code) {
  language = code in LOCALES ? code : "de";
  document.documentElement.lang = language;
  try { localStorage.setItem("lang", language); } catch { /* optional */ }
}

// Texte mit Platzhaltern erkennen, die der Server schon ausgefüllt hat
// (z. B. „Nicht genug Bestand: verfügbar sind 5 Sack.“).
const patternCache = new Map();
function patterns(dict) {
  if (!patternCache.has(dict)) {
    patternCache.set(dict, Object.keys(dict).filter((key) => key.includes("{0}")).map((key) => {
      const source = key.replace(/[.*+?^$()|[\]\\]/g, "\\$&").replace(/\{\d\}/g, "(.+)");
      return [new RegExp(`^${source}$`), key];
    }));
  }
  return patternCache.get(dict);
}

function lookup(dict, text) {
  if (text in dict) return dict[text];
  for (const [regex, key] of patterns(dict)) {
    const match = text.match(regex);
    if (match) {
      const order = [...key.matchAll(/\{(\d)\}/g)].map((m) => Number(m[1]));
      const values = [];
      order.forEach((index, i) => { values[index] = dict[match[i + 1]] ?? match[i + 1]; });
      return dict[key].replace(/\{(\d)\}/g, (_, i) => values[i]);
    }
  }
  return null;
}

export function t(text, ...args) {
  let result = text;
  if (language !== "de" && typeof text === "string") result = lookup(DICTIONARIES[language], text) ?? text;
  return args.length ? result.replace(/\{(\d)\}/g, (_, i) => args[i]) : result;
}

// Für die Bausteine in ui.jsx: übersetzt Text, lässt alles andere (Symbole, Zahlen) unverändert.
export function tr(node) {
  if (typeof node === "string") {
    const core = node.trim();
    return core ? node.replace(core, () => t(core)) : node;
  }
  return Array.isArray(node) ? node.map(tr) : node;
}
