"use client";

import { useState, useEffect } from "react";
import {
  generateMesh,
  validateBboxSize,
  getQualityOptions,
  type MeshQuality,
  type QualityOption,
  type ProgressInfo,
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
  const [progress, setProgress] = useState<ProgressInfo | null>(null);

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
    setProgress({ percent: 0, message: "Starting...", status: "processing" });

    try {
      await generateMesh(bounds, quality, (progressInfo) => {
        setProgress(progressInfo);
      });
      // file download happens automatically in generateMesh()
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "failed to generate mesh";
      setError(errorMsg);
      setProgress(null);
      console.error("generation error:", err);
    } finally {
      setIsGenerating(false);
      // Keep progress visible briefly after completion
      setTimeout(() => setProgress(null), 2000);
    }
  };

  const selectedOption = qualityOptions.find((opt) => opt.value === quality);

  return (
    <div className="space-y-4">
      {/* Quality Selector */}
      <div className="space-y-2.5 rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-900/80 to-neutral-900/50 backdrop-blur p-5 shadow-lg transition-all hover:border-neutral-700">
        <label
          htmlFor="quality"
          className="text-xs font-semibold text-neutral-400 uppercase tracking-wider"
        >
          Detail Quality
        </label>
        <select
          id="quality"
          value={quality}
          onChange={(e) => setQuality(e.target.value as MeshQuality)}
          disabled={isGenerating}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900/90 px-4 py-2.5 text-sm text-neutral-100 transition-all focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:cursor-not-allowed disabled:opacity-50 hover:border-neutral-600"
        >
          {qualityOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {selectedOption && (
          <div className="space-y-2 pt-1">
            <p className="text-xs text-neutral-500">
              {selectedOption.description}
            </p>
            <div className="flex items-center gap-2">
              <svg
                className="w-3 h-3 text-neutral-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-xs text-neutral-600 font-mono">
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
            </div>
          </div>
        )}
      </div>

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={isDisabled}
        className={`w-full rounded-lg px-5 py-4 text-sm font-semibold transition-all duration-200 ${
          isDisabled
            ? "border border-neutral-800 bg-neutral-900/50 text-neutral-600 cursor-not-allowed"
            : "bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:from-blue-500 hover:to-blue-600 shadow-lg shadow-blue-900/30 hover:shadow-xl hover:shadow-blue-900/40 hover:scale-[1.02] active:scale-[0.98]"
        }`}
      >
        {isGenerating ? (
          <span className="flex items-center justify-center gap-2.5">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
            <span>Generating mesh...</span>
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            <span>Generate Mesh</span>
          </span>
        )}
      </button>

      {/* Progress Bar */}
      {progress && (
        <div className="rounded-lg border border-neutral-800 bg-gradient-to-br from-neutral-900/80 to-neutral-900/50 backdrop-blur p-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between text-xs">
            <span className="text-neutral-400">{progress.message}</span>
            <span className="font-mono font-semibold text-neutral-300">
              {progress.percent}%
            </span>
          </div>
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-800">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300 ease-out"
              style={{ width: `${progress.percent}%` }}
            >
              <div className="absolute inset-0 animate-pulse bg-white/20"></div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/50 backdrop-blur p-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-start gap-3">
            <svg
              className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-xs text-red-300 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {!bounds && (
        <div className="flex items-center gap-2 text-xs text-neutral-600">
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Select an area on the map to begin</span>
        </div>
      )}
    </div>
  );
}
