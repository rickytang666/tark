"use client";

import { useState, useEffect } from "react";
import {
  generateMesh,
  validateBboxSize,
  getQualityOptions,
  type MeshQuality,
  type QualityOption,
} from "@/lib/api";

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
  const [quality, setQuality] = useState<MeshQuality>("medium");
  const [qualityOptions, setQualityOptions] = useState<QualityOption[]>([]);

  // Fetch quality options on mount
  useEffect(() => {
    getQualityOptions()
      .then((response) => {
        setQualityOptions(response.options);
        setQuality(response.default);
      })
      .catch((err) => {
        console.error("Failed to fetch quality options:", err);
        // Use default options if fetch fails
        setQualityOptions([
          {
            value: "low",
            label: "Low",
            zoom: 11,
            description: "Fast, lower detail",
          },
          {
            value: "medium",
            label: "Medium",
            zoom: 12,
            description: "Balanced",
          },
          {
            value: "high",
            label: "High",
            zoom: 13,
            description: "High detail",
          },
          {
            value: "ultra",
            label: "Ultra",
            zoom: 14,
            description: "Ultra detail",
          },
        ]);
      });
  }, []);

  const validation = bounds ? validateBboxSize(bounds) : { valid: false };
  const isDisabled = !bounds || !validation.valid || isGenerating;

  const handleGenerate = async () => {
    if (!bounds) return;

    setIsGenerating(true);
    setError(null);

    try {
      await generateMesh(bounds, quality);
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

  const selectedOption = qualityOptions.find((opt) => opt.value === quality);

  return (
    <div className="space-y-3">
      {/* Quality Selector */}
      <div className="space-y-2">
        <label
          htmlFor="quality"
          className="text-xs font-medium text-neutral-400"
        >
          detail quality
        </label>
        <select
          id="quality"
          value={quality}
          onChange={(e) => setQuality(e.target.value as MeshQuality)}
          disabled={isGenerating}
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {qualityOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} ({option.description})
            </option>
          ))}
        </select>
        {selectedOption && (
          <p className="text-xs text-neutral-600">
            ~
            {selectedOption.zoom === 11
              ? "60"
              : selectedOption.zoom === 12
              ? "30"
              : selectedOption.zoom === 13
              ? "15"
              : "7.5"}
            m terrain resolution
          </p>
        )}
      </div>

      {/* Generate Button */}
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
