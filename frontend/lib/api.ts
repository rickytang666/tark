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

export type MeshQuality = "low" | "medium" | "high" | "ultra";

export interface QualityOption {
  value: MeshQuality;
  label: string;
  zoom: number;
  description: string;
}

export interface QualityOptionsResponse {
  options: QualityOption[];
  default: MeshQuality;
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
 * Get available quality options from backend
 */
export async function getQualityOptions(): Promise<QualityOptionsResponse> {
  const response = await fetch(`${API_URL}/quality-options`);
  
  if (!response.ok) {
    throw new Error("Failed to fetch quality options");
  }
  
  return response.json();
}

export interface ProgressInfo {
  percent: number;
  message: string;
  status: "processing" | "complete" | "error";
}

/**
 * Get progress for a job
 */
export async function getProgress(jobId: string): Promise<ProgressInfo> {
  const response = await fetch(`${API_URL}/progress/${jobId}`);
  
  if (!response.ok) {
    throw new Error("Failed to fetch progress");
  }
  
  return response.json();
}

/**
 * Generate mesh for the given bounding box with progress tracking
 * Calls onProgress callback with updates, then triggers download when complete
 */
export async function generateMesh(
  bbox: BoundingBox, 
  quality: MeshQuality = "medium",
  onProgress?: (progress: ProgressInfo) => void
): Promise<void> {
  // Generate a job ID for progress tracking
  const jobId = Math.random().toString(36).substring(7);
  
  // Start polling for progress if callback provided
  let pollInterval: NodeJS.Timeout | null = null;
  if (onProgress) {
    pollInterval = setInterval(async () => {
      try {
        const progress = await getProgress(jobId);
        onProgress(progress);
        
        // Stop polling when complete or error
        if (progress.status === "complete" || progress.status === "error") {
          if (pollInterval) clearInterval(pollInterval);
        }
      } catch (err) {
        // Silently fail progress updates, generation continues
        console.warn("Progress update failed:", err);
      }
    }, 500); // Poll every 500ms
  }
  
  try {
    const response = await fetch(`${API_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ bbox, quality, job_id: jobId }),
    });

    if (pollInterval) clearInterval(pollInterval);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to generate mesh" }));
      throw new Error(error.detail || "Failed to generate mesh");
    }

    // Get filename from response headers or use default
    const contentDisposition = response.headers.get("content-disposition");
    const filenameMatch = contentDisposition?.match(/filename="?(.+)"?/i);
    const filename = filenameMatch ? filenameMatch[1] : "tark.zip";

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
    
    // Final progress update
    if (onProgress) {
      onProgress({ percent: 100, message: "Download complete!", status: "complete" });
    }
  } catch (error) {
    if (pollInterval) clearInterval(pollInterval);
    throw error;
  }
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

