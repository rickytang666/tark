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
      <div className="rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-900/80 to-neutral-900/50 backdrop-blur p-6 transition-all hover:border-neutral-700">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 text-neutral-600">
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
              />
            </svg>
          </div>
          <p className="text-sm text-neutral-400 leading-relaxed">
            select an area on the map to see details
          </p>
        </div>
      </div>
    );
  }

  const { width, height, area } = calculateAreaSize(bounds);
  const validation = validateBboxSize(bounds);

  return (
    <div className="rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-900/80 to-neutral-900/50 backdrop-blur p-6 space-y-4 shadow-lg transition-all hover:border-neutral-700 hover:shadow-xl">
      <div>
        <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4">
          Area Size
        </h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between items-center group">
            <span className="text-neutral-500 group-hover:text-neutral-400 transition-colors">
              Width
            </span>
            <span className="font-mono text-neutral-200 font-medium">
              {(width / 1000).toFixed(2)} km
            </span>
          </div>
          <div className="flex justify-between items-center group">
            <span className="text-neutral-500 group-hover:text-neutral-400 transition-colors">
              Height
            </span>
            <span className="font-mono text-neutral-200 font-medium">
              {(height / 1000).toFixed(2)} km
            </span>
          </div>
          <div className="pt-2 border-t border-neutral-800/50"></div>
          <div className="flex justify-between items-center group">
            <span className="text-neutral-400 font-medium group-hover:text-neutral-300 transition-colors">
              Total Area
            </span>
            <span className="font-mono text-neutral-100 font-semibold text-base">
              {area.toFixed(2)} km²
            </span>
          </div>
        </div>
      </div>

      {!validation.valid && (
        <div className="pt-4 border-t border-neutral-800/50">
          <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-red-950/50 border border-red-900/50">
            <svg
              className="w-4 h-4 text-red-400 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-xs text-red-300">{validation.error}</p>
          </div>
        </div>
      )}

      {validation.valid && (
        <div className="pt-4 border-t border-neutral-800/50">
          <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-emerald-950/50 border border-emerald-900/50">
            <svg
              className="w-4 h-4 text-emerald-400 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-xs text-emerald-300 font-medium">Valid size</p>
          </div>
        </div>
      )}
    </div>
  );
}
