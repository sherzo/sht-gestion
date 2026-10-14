// Reduce las fotos en el navegador antes de subirlas (research R9): una foto de teléfono
// de varios MB queda en un JPEG de lado mayor 1.600 px, que sube rápido con datos móviles.
// El servidor la normaliza después a WebP de 1.200 px. Si algo falla, se envía el original
// y el servidor decide.

const MAX_SIDE = 1600;
const JPEG_QUALITY = 0.85;

export async function resizeForUpload(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    // Una imagen chica no se toca: así un PNG con transparencia la conserva.
    if (scale === 1 && file.size <= 1024 * 1024) {
      bitmap.close();
      return file;
    }
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
    return blob ?? file;
  } catch {
    return file;
  }
}
