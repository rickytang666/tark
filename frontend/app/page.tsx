"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import AreaPreview from "@/components/AreaPreview";
import DownloadButton from "@/components/DownloadButton";

// dynamic import to avoid SSR issues with leaflet
const MapSelector = dynamic(() => import("@/components/MapSelector"), {
  ssr: false,
  loading: () => (
    <div className="h-[500px] w-full rounded-lg border border-neutral-800 bg-neutral-900/50 backdrop-blur flex items-center justify-center">
      <div className="flex items-center gap-3">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-600 border-t-neutral-400"></div>
        <p className="text-sm text-neutral-400">loading map...</p>
      </div>
    </div>
  ),
});

export default function Home() {
  const [bounds, setBounds] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
  } | null>(null);

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-950 via-neutral-950 to-neutral-900 px-4 py-12 text-neutral-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="h-8 w-1 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></div>
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-neutral-100 to-neutral-400 bg-clip-text text-transparent">
              Tark
            </h1>
          </div>
          <p className="text-base text-neutral-400 mb-2">
            Google Earth for game developers
          </p>
          <p className="text-sm text-neutral-500">
            real terrain · real buildings · game-ready in seconds
          </p>
          <div className="inline-flex items-center gap-2 mt-3 px-3 py-1.5 rounded-full bg-neutral-900/50 border border-neutral-800">
            <kbd className="px-1.5 py-0.5 text-xs font-mono bg-neutral-800 rounded">
              Shift
            </kbd>
            <span className="text-xs text-neutral-500">
              + drag to select area
            </span>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <MapSelector onBoundsChange={setBounds} />
          </div>

          <div className="space-y-4">
            <AreaPreview bounds={bounds} />
            <DownloadButton bounds={bounds} />
          </div>
        </div>
      </div>
    </div>
  );
}
