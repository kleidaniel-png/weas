// Bilder vor dem Hochladen im Browser verkleinern (spart Speicher und Datenvolumen).
export const IMAGE_MAX_SIZE = 800;   // längste Kante in Pixeln
export const IMAGE_QUALITY = 0.8;    // JPEG-Qualität

async function decode(file) {
  if ("createImageBitmap" in window) {
    try { return await createImageBitmap(file, { imageOrientation: "from-image" }); } catch { /* weiter unten */ }
  }
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

// Liefert das Bild als Data-URL (JPEG), höchstens IMAGE_MAX_SIZE Pixel groß.
export async function shrinkImage(file, maxSize = IMAGE_MAX_SIZE) {
  const source = await decode(file);
  const scale = Math.min(1, maxSize / Math.max(source.width, source.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(source.width * scale));
  canvas.height = Math.max(1, Math.round(source.height * scale));
  const context = canvas.getContext("2d");
  context.fillStyle = "#fff"; // durchsichtige Bilder bekommen einen weißen Hintergrund
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", IMAGE_QUALITY);
}

export const DOCUMENT_MAX_SIZE = 1600; // Fotos von Belegen: größer, damit Text lesbar bleibt

// Beleg zum Anhängen vorbereiten: Fotos werden verkleinert, PDF-Dateien unverändert gelesen.
export async function readDocument(file) {
  if (file.type === "application/pdf") {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
  return shrinkImage(file, DOCUMENT_MAX_SIZE);
}
