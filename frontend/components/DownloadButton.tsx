"use client";

import { useState } from "react";
import { generateMesh, validateBboxSize } from "@/lib/api";

interface DownloadButtonProps {
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  } | null;
}

export default function DownloadButton({ bounds }: DownloadButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validation = bounds ? validateBboxSize(bounds) : { valid: false };
  const isDisabled = !bounds || !validation.valid || isGenerating;

  const handleGenerate = async () => {
    if (!bounds) return;

    setIsGenerating(true);
    setError(null);

    try {
      await generateMesh(bounds);
      // file download happens automatically in generateMesh()
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "failed to generate mesh";
      setError(errorMsg);
      console.error("generation error:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-3">
      <button
        onClick={handleGenerate}
        disabled={isDisabled}
        className={`w-full rounded border px-4 py-3 text-sm font-medium transition-colors ${
          isDisabled
            ? "border-neutral-800 bg-neutral-900 text-neutral-600 cursor-not-allowed"
            : "border-blue-600 bg-blue-600 text-white hover:bg-blue-700"
        }`}
      >
        {isGenerating ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
            generating...
          </span>
        ) : (
          "generate mesh"
        )}
      </button>

      {error && (
        <div className="rounded border border-red-900 bg-red-950 p-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {!bounds && (
        <p className="text-xs text-neutral-600">select an area to generate</p>
      )}
    </div>
  );
}
