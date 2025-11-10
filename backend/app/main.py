"""
GeoMesh Backend - FastAPI Application
Generates game-ready 3D meshes from real-world locations
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="GeoMesh API",
    description="Generate game-ready 3D meshes from real-world locations",
    version="0.1.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)


class BoundingBox(BaseModel):
    """Geographic bounding box coordinates"""
    north: float = Field(..., ge=-90, le=90, description="North latitude")
    south: float = Field(..., ge=-90, le=90, description="South latitude")
    east: float = Field(..., ge=-180, le=180, description="East longitude")
    west: float = Field(..., ge=-180, le=180, description="West longitude")
    
    def validate_bbox(self):
        """Validate bounding box constraints"""
        if self.north <= self.south:
            raise ValueError("North must be greater than south")
        if self.east <= self.west:
            raise ValueError("East must be greater than west")
        
        # Calculate approximate area (rough estimate)
        lat_diff = self.north - self.south
        lng_diff = self.east - self.west
        # Rough conversion: 1 degree ≈ 111 km
        area_km2 = (lat_diff * 111) * (lng_diff * 111)
        
        # Max area: 5km x 5km = 25 km²
        if area_km2 > 25:
            raise ValueError(f"Area too large: {area_km2:.2f} km². Maximum is 25 km² (5km x 5km)")
        
        return True


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "GeoMesh API",
        "status": "operational",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "temp_dir": os.path.exists(TEMP_DIR),
        "temp_dir_path": TEMP_DIR
    }


@app.post("/generate")
async def generate_mesh(bbox: BoundingBox):
    """
    Generate 3D mesh for the specified bounding box
    
    Args:
        bbox: Geographic bounding box (north, south, east, west)
    
    Returns:
        File stream with .obj mesh (MVP: direct response)
        Future: { job_id, status } for async processing
    """
    try:
        # Validate bounding box
        bbox.validate_bbox()
        
        # TODO: Implement mesh generation pipeline
        # 1. Fetch elevation data (Mapbox Terrain-RGB)
        # 2. Fetch building footprints (Overpass API)
        # 3. Generate terrain mesh
        # 4. Extrude buildings
        # 5. Merge and export
        
        return {
            "message": "Mesh generation not yet implemented",
            "bbox": bbox.dict(),
            "status": "pending"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

