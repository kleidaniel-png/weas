import { Camera, ImagePlus, Package, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { shrinkImage } from "../image.js";
import { Alert, Button } from "./ui.jsx";

// Geräte mit Touch-Bedienung (Handy, Tablet) bekommen zusätzlich den Kamera-Knopf.
const HAS_CAMERA = typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches;

// Kleines Vorschaubild; ohne Bild ein Platzhalter.
export function Thumb({ src, size = "size-10", onClick }) {
  const box = `${size} shrink-0 overflow-hidden rounded-lg bg-stone-100 dark:bg-stone-800`;
  if (!src) return <div className={`${box} flex items-center justify-center text-stone-400`}><Package size={18} /></div>;
  const img = <img src={src} alt="" loading="lazy" className="size-full object-cover" />;
  return onClick ? <button type="button" onClick={onClick} className={`${box} block`}>{img}</button> : <div className={box}>{img}</div>;
}

// Bild wählen oder mit der Kamera aufnehmen. value = Adresse/Data-URL oder null.
export default function ImagePicker({ value, onChange }) {
  const fileInput = useRef(null);
  const cameraInput = useRef(null);
  const [error, setError] = useState("");

  async function picked(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // dieselbe Datei erneut wählbar
    if (!file) return;
    setError("");
    try { onChange(await shrinkImage(file)); }
    catch { setError("Das Bild konnte nicht gelesen werden."); }
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <Thumb src={value} size="size-20" />
        <div className="flex flex-wrap gap-2">
          {HAS_CAMERA && <Button variant="secondary" onClick={() => cameraInput.current.click()}><Camera size={16} /> Foto aufnehmen</Button>}
          <Button variant="secondary" onClick={() => fileInput.current.click()}><ImagePlus size={16} /> Bild auswählen</Button>
          {value && <Button variant="ghost" className="px-2" onClick={() => onChange(null)} aria-label="Bild entfernen"><Trash2 size={16} /></Button>}
        </div>
      </div>
      {/* capture öffnet auf dem Handy direkt die Rückkamera */}
      <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={picked} />
      <input ref={fileInput} type="file" accept="image/*" hidden onChange={picked} />
      <div className="mt-2"><Alert>{error}</Alert></div>
    </div>
  );
}
