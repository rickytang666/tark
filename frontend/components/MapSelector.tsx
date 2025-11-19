"use client";

import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Rectangle,
  useMapEvents,
} from "react-leaflet";
import { LatLngBounds, LatLng } from "leaflet";
import "leaflet/dist/leaflet.css";

interface MapSelectorProps {
  onBoundsChange?: (bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  }) => void;
}

function BoundsSelector({ onBoundsChange }: MapSelectorProps) {
  const [bounds, setBounds] = useState<LatLngBounds | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<LatLng | null>(null);

  const map = useMapEvents({
    mousedown: (e) => {
      // only draw rectangle if shift or ctrl is pressed
      if (e.originalEvent.shiftKey || e.originalEvent.ctrlKey) {
        e.originalEvent.preventDefault();
        map.dragging.disable();
        setIsDrawing(true);
        setStartPoint(e.latlng);
        setBounds(null);
      }
    },
    mousemove: (e) => {
      if (isDrawing && startPoint) {
        const newBounds = new LatLngBounds(startPoint, e.latlng);
        setBounds(newBounds);
      }
    },
    mouseup: (e) => {
      if (isDrawing && startPoint) {
        const finalBounds = new LatLngBounds(startPoint, e.latlng);
        setBounds(finalBounds);

        if (onBoundsChange) {
          onBoundsChange({
            north: finalBounds.getNorth(),
            south: finalBounds.getSouth(),
            east: finalBounds.getEast(),
            west: finalBounds.getWest(),
          });
        }
      }
      setIsDrawing(false);
      setStartPoint(null);
      map.dragging.enable();
    },
  });

  return bounds ? (
    <Rectangle
      bounds={bounds}
      pathOptions={{
        color: "#60a5fa",
        weight: 2,
        fillOpacity: 0.15,
      }}
    />
  ) : null;
}

export default function MapSelector({ onBoundsChange }: MapSelectorProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // mount check for leaflet (client-side only)
    const timer = setTimeout(() => setIsMounted(true), 0);
    return () => clearTimeout(timer);
  }, []);

  if (!isMounted) {
    return (
      <div className="h-[500px] w-full rounded-lg border border-neutral-800 bg-neutral-900/50 backdrop-blur flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-600 border-t-neutral-400"></div>
          <p className="text-sm text-neutral-400">loading map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="group relative h-[500px] w-full rounded-lg overflow-hidden border border-neutral-800 shadow-2xl transition-all hover:border-neutral-700 hover:shadow-blue-900/20">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"></div>
      <MapContainer
        center={[43.4722, -80.5439]} // uwaterloo
        zoom={12}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <BoundsSelector onBoundsChange={onBoundsChange} />
      </MapContainer>
    </div>
  );
}
