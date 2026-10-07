// Dunkles Design sofort anwenden (vor dem ersten Zeichnen). Eigene Datei, damit die
// Seite ohne eingebettete Skripte auskommt (strenge Content-Security-Policy).
try { if (localStorage.getItem("theme") === "dark") document.documentElement.classList.add("dark"); } catch (e) {}
