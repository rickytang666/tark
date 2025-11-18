"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import AreaPreview from "@/components/AreaPreview";
import DownloadButton from "@/components/DownloadButton";

// dynamic import to avoid SSR issues with leaflet
const MapSelector = dynamic(() => import("@/components/MapSelector"), {
  ssr: false,
  loading: () => (
    <div className="h-[500px] w-full rounded border border-neutral-800 bg-neutral-900 flex items-center justify-center">
      <p className="text-sm text-neutral-500">loading map...</p>
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
    <div className="min-h-screen bg-neutral-950 px-4 py-8 text-neutral-100">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="mb-2 text-2xl font-medium">Tark</h1>
          <p className="text-sm text-neutral-500">
            turn locations into 3d meshes for games
          </p>
          <p className="mt-2 text-xs text-neutral-600">
            hold shift and drag to select area
          </p>
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

        <div className="mt-8 border-t border-neutral-800 pt-4 text-xs text-neutral-600">
          <p>fastapi + next.js + mapbox + openstreetmap</p>
        </div>
      </div>
    </div>
  );
}
