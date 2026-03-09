"use client";

import { useEffect, useRef } from "react";

/**
 * NoiseBackground — subtle film grain / noise texture overlay.
 * Uses canvas to generate a static noise pattern.
 * mix-blend-mode: soft-light with low opacity for texture.
 */
export function NoiseBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = 256;
    canvas.width = size;
    canvas.height = size;

    const imageData = ctx.createImageData(size, size);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      const val = Math.random() * 255;
      data[i] = val;     // R
      data[i + 1] = val; // G
      data[i + 2] = val; // B
      data[i + 3] = 25;  // Alpha — very subtle
    }

    ctx.putImageData(imageData, 0, 0);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="noise-overlay"
      style={{
        width: "100%",
        height: "100%",
        imageRendering: "pixelated",
      }}
      aria-hidden="true"
    />
  );
}
