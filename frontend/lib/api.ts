/**
 * API client for Tark backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface GenerateResponse {
  message?: string;
  bbox?: BoundingBox;
  status?: string;
  download_url?: string;
}

/**
 * Check if the backend is healthy
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch (error) {
    console.error("Health check failed:", error);
    return false;
  }
}

/**
 * Generate mesh for the given bounding box and trigger download
 */
export async function generateMesh(bbox: BoundingBox): Promise<void> {
  const response = await fetch(`${API_URL}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(bbox),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to generate mesh" }));
    throw new Error(error.detail || "Failed to generate mesh");
  }

  // Get filename from response headers or use default
  const contentDisposition = response.headers.get("content-disposition");
  const filenameMatch = contentDisposition?.match(/filename="?(.+)"?/i);
  const filename = filenameMatch ? filenameMatch[1] : "tark.obj";

  // Download file
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Calculate approximate area dimensions in meters
 */
export function calculateAreaSize(bbox: BoundingBox): {
  width: number;
  height: number;
  area: number;
} {
  const centerLat = (bbox.north + bbox.south) / 2;
  
  // 1 degree latitude ≈ 111km
  const latMeters = (bbox.north - bbox.south) * 111000;
  
  // 1 degree longitude varies by latitude
  const lngMeters =
    (bbox.east - bbox.west) * 111000 * Math.abs(Math.cos(centerLat * (Math.PI / 180)));

  return {
    width: Math.round(lngMeters),
    height: Math.round(latMeters),
    area: Math.round(latMeters * lngMeters) / 1_000_000, // km²
  };
}

/**
 * Validate bounding box size
 */
export function validateBboxSize(bbox: BoundingBox): {
  valid: boolean;
  error?: string;
} {
  const { width, height } = calculateAreaSize(bbox);

  // Minimum 1km × 1km
  if (width < 1000 || height < 1000) {
    return {
      valid: false,
      error: `Area too small: ${(width / 1000).toFixed(1)}km × ${(height / 1000).toFixed(1)}km. Minimum is 1km × 1km.`,
    };
  }

  // Maximum 5km × 5km
  if (width > 5000 || height > 5000) {
    return {
      valid: false,
      error: `Area too large: ${(width / 1000).toFixed(1)}km × ${(height / 1000).toFixed(1)}km. Maximum is 5km × 5km.`,
    };
  }

  return { valid: true };
}

