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
        color: "#3b82f6",
        weight: 2,
        fillOpacity: 0.1,
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
      <div className="h-[500px] w-full rounded border border-neutral-800 bg-neutral-900 flex items-center justify-center">
        <p className="text-sm text-neutral-500">loading map...</p>
      </div>
    );
  }

  return (
    <div className="h-[500px] w-full rounded border border-neutral-800 overflow-hidden">
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
