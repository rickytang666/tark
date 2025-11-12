"use client";

import { calculateAreaSize, validateBboxSize } from "@/lib/api";

interface AreaPreviewProps {
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  } | null;
}

export default function AreaPreview({ bounds }: AreaPreviewProps) {
  if (!bounds) {
    return (
      <div className="rounded border border-neutral-800 bg-neutral-900 p-6">
        <p className="text-sm text-neutral-500">
          click and drag on the map to select an area
        </p>
      </div>
    );
  }

  const { width, height, area } = calculateAreaSize(bounds);
  const validation = validateBboxSize(bounds);

  return (
    <div className="rounded border border-neutral-800 bg-neutral-900 p-6 space-y-4">
      <div>
        <h3 className="text-sm font-medium text-neutral-300 mb-3">area size</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-neutral-500">width</span>
            <span className="text-neutral-300">
              {(width / 1000).toFixed(2)} km
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-neutral-500">height</span>
            <span className="text-neutral-300">
              {(height / 1000).toFixed(2)} km
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-neutral-500">total</span>
            <span className="text-neutral-300">{area.toFixed(2)} km²</span>
          </div>
        </div>
      </div>

      {!validation.valid && (
        <div className="pt-3 border-t border-neutral-800">
          <p className="text-xs text-red-400">{validation.error}</p>
        </div>
      )}

      {validation.valid && (
        <div className="pt-3 border-t border-neutral-800">
          <p className="text-xs text-green-400">✓ valid size</p>
        </div>
      )}
    </div>
  );
}
