export type ImagenPropuesta = {
  imagen_id: string;
  codigo_propuesto: string | null;
  tipo: string;
  confianza: number | null;
  orientacion: string | null;
  bbox: number[][];
  sin_deteccion: boolean;
  mensaje: string;
  url_imagen: string;
  url_thumb: string | null;
  fuente?: string | null;
  observaciones?: string | null;
  tiempo_proceso_s?: number | null;
  pasos?: string[];
  creado_en?: string | null;
  /** Nombre local del archivo (solo cola del cliente) */
  nombre_archivo?: string;
};

export type Registro = {
  id: number;
  imagen_id: string;
  codigo: string;
  tipo_deteccion: string;
  codigo_ocr: string | null;
  confianza: number | null;
  validado_manual: boolean;
  ruta_imagen: string;
  orientacion: string | null;
  fuente?: string | null;
  observaciones?: string | null;
  tiempo_proceso_s?: number | null;
  usuario_id: number | null;
  creado_en: string;
  url_imagen: string;
  url_thumb: string | null;
};

export type RegistroList = {
  total: number;
  items: Registro[];
};

export const PROPUESTA_KEY = "procesoimagen_propuesta";
export const COLA_KEY = "procesoimagen_cola";
export const COLA_INDEX_KEY = "procesoimagen_cola_idx";
export const CONF_THRESHOLD = 0.85;
