// Einheitliche Darstellung von Zahlen, Geld und Datum in der Sprache des Benutzers.
import { locale } from "./i18n.js";

export const qty = (n, unit = "") =>
  new Intl.NumberFormat(locale(), { maximumFractionDigits: 3 }).format(n) + (unit ? " " + unit : "");
export const signedQty = (n, unit) => (n > 0 ? "+" : "") + qty(n, unit);
export const money = (n, digits = 2) =>
  new Intl.NumberFormat(locale(), { style: "currency", currency: "EUR", maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);
export const dateTime = (ts) =>
  new Date(ts * 1000).toLocaleString(locale(), { dateStyle: "short", timeStyle: "short" });
export const fileSize = (bytes) => qty(Math.round(bytes / 1024)) + " kB";
