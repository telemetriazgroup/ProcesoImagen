import type { ImagenPropuesta, Registro, RegistroList } from "../types";

const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export function apiUrl(path: string): string {
  if (!path) return API_URL;
  if (path.startsWith("http")) return path;
  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((d: { msg?: string }) => d.msg ?? JSON.stringify(d))
        .join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return `Error HTTP ${res.status}`;
  }
}

export async function checkHealth(): Promise<string> {
  const res = await fetch(apiUrl("/api/health"));
  if (!res.ok) throw new Error(await readError(res));
  const data = await res.json();
  return `${data.status} · fase ${data.phase}`;
}

export async function uploadImagen(file: File): Promise<ImagenPropuesta> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(apiUrl("/api/imagenes"), { method: "POST", body });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as ImagenPropuesta;
  return { ...data, nombre_archivo: file.name };
}

export async function crearRegistro(payload: {
  imagen_id: string;
  codigo: string;
  tipo?: string;
}): Promise<Registro> {
  const res = await fetch(apiUrl("/api/registros"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function listarRegistros(params: {
  codigo?: string;
  tipo?: string;
  validado_manual?: boolean | "";
  limit?: number;
  offset?: number;
}): Promise<RegistroList> {
  const q = new URLSearchParams();
  if (params.codigo) q.set("codigo", params.codigo);
  if (params.tipo) q.set("tipo", params.tipo);
  if (params.validado_manual === true) q.set("validado_manual", "true");
  if (params.validado_manual === false) q.set("validado_manual", "false");
  q.set("limit", String(params.limit ?? 50));
  q.set("offset", String(params.offset ?? 0));
  const res = await fetch(apiUrl(`/api/registros?${q}`));
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getRegistro(id: number): Promise<Registro> {
  const res = await fetch(apiUrl(`/api/registros/${id}`));
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}
