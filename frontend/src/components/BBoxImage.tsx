import { useEffect, useRef, useState } from "react";

type Props = {
  src: string;
  bbox?: number[][];
  alt?: string;
};

/** Imagen con bounding box OCR escalado al tamaño renderizado. */
export function BBoxImage({ src, bbox = [], alt = "Equipo" }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [box, setBox] = useState<{
    left: number;
    top: number;
    width: number;
    height: number;
  } | null>(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img || !bbox.length) {
      setBox(null);
      return;
    }

    const update = () => {
      const nw = img.naturalWidth;
      const nh = img.naturalHeight;
      if (!nw || !nh) return;
      const rw = img.clientWidth;
      const rh = img.clientHeight;
      const scale = Math.min(rw / nw, rh / nh);
      const dispW = nw * scale;
      const dispH = nh * scale;
      const offsetX = (rw - dispW) / 2;
      const offsetY = (rh - dispH) / 2;

      const xs = bbox.map((p) => Number(p[0]));
      const ys = bbox.map((p) => Number(p[1]));
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);

      setBox({
        left: offsetX + minX * scale,
        top: offsetY + minY * scale,
        width: Math.max(4, (maxX - minX) * scale),
        height: Math.max(4, (maxY - minY) * scale),
      });
    };

    update();
    img.addEventListener("load", update);
    window.addEventListener("resize", update);
    return () => {
      img.removeEventListener("load", update);
      window.removeEventListener("resize", update);
    };
  }, [src, bbox]);

  return (
    <div className="bbox-wrap">
      <img ref={imgRef} src={src} alt={alt} className="bbox-img" />
      {box && (
        <div
          className="bbox-overlay"
          style={{
            left: box.left,
            top: box.top,
            width: box.width,
            height: box.height,
          }}
        />
      )}
    </div>
  );
}
