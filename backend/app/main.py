"""
tark backend - fastapi application
generates game-ready 3d meshes from real-world locations
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum
import os
import math
import zipfile
import uuid
from pathlib import Path
from dotenv import load_dotenv
from app.generator import MeshGenerator

# load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="tark api",
    description="generate game-ready 3d meshes from real-world locations",
    version="0.1.0"
)

# cors middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ensure temp directory exists
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# in-memory progress store (use redis in production)
progress_store: Dict[str, Dict[str, any]] = {}


class MeshQuality(str, Enum):
    """mesh detail quality levels (within mapbox free tier limits)"""
    LOW = "low"          # zoom=11, faster, ~60m resolution, 512x512 texture
    MEDIUM = "medium"    # zoom=12, balanced, ~30m resolution, 1024x1024 texture (default)
    HIGH = "high"        # zoom=13, detailed, ~15m resolution, 1280x1280 texture
    ULTRA = "ultra"      # zoom=14, very detailed, ~7.5m resolution, 1280x1280 texture


# quality settings mapping
QUALITY_SETTINGS = {
    MeshQuality.LOW: {
        "zoom": 11,
        "texture_max": 512,
        "description": "fast generation, lower detail (~60m terrain resolution)"
    },
    MeshQuality.MEDIUM: {
        "zoom": 12,
        "texture_max": 1024,
        "description": "balanced speed and detail (~30m terrain resolution)"
    },
    MeshQuality.HIGH: {
        "zoom": 13,
        "texture_max": 1280,
        "description": "high detail, slower generation (~15m terrain resolution)"
    },
    MeshQuality.ULTRA: {
        "zoom": 14,
        "texture_max": 1280,
        "description": "ultra detail, slow generation (~7.5m terrain resolution)"
    },
}


class BoundingBox(BaseModel):
    """geographic bounding box coordinates"""
    north: float = Field(..., ge=-90, le=90, description="north latitude")
    south: float = Field(..., ge=-90, le=90, description="south latitude")
    east: float = Field(..., ge=-180, le=180, description="east longitude")
    west: float = Field(..., ge=-180, le=180, description="west longitude")
    
    def validate_bbox(self):
        """validate bounding box constraints"""
        if self.north <= self.south:
            raise ValueError("north must be greater than south")
        if self.east <= self.west:
            raise ValueError("east must be greater than west")
        
        # calculate approximate dimensions in meters
        # see docs/logic/coordinates.md for math details
        lat_diff = self.north - self.south
        lng_diff = self.east - self.west
        
        # at mid-latitude, convert degrees to meters
        center_lat = (self.north + self.south) / 2
        lat_meters = lat_diff * 111000  # 1 degree lat approx 111km
        lng_meters = lng_diff * 111000 * abs(math.cos(math.radians(center_lat)))
        
        # minimum: 1km x 1km (prevents mapbox tile issues)
        if lat_meters < 1000 or lng_meters < 1000:
            raise ValueError(
                f"area too small: {lat_meters:.0f}m x {lng_meters:.0f}m. "
                "minimum is 1km x 1km to ensure proper terrain representation."
            )
        
        # maximum: 5km x 5km (prevents timeout/memory issues)
        if lat_meters > 5000 or lng_meters > 5000:
            raise ValueError(
                f"area too large: {lat_meters:.0f}m x {lng_meters:.0f}m. "
                "maximum is 5km x 5km."
            )
        
        return True


@app.get("/")
async def root():
    """health check endpoint"""
    return {
        "service": "tark api",
        "status": "operational",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """detailed health check"""
    return {
        "status": "healthy",
        "temp_dir": os.path.exists(TEMP_DIR),
        "temp_dir_path": TEMP_DIR
    }


class GenerateRequest(BaseModel):
    """request body for mesh generation"""
    bbox: BoundingBox
    quality: MeshQuality = Field(
        default=MeshQuality.MEDIUM,
        description="mesh detail quality level"
    )
    job_id: Optional[str] = Field(
        default=None,
        description="optional job id for progress tracking"
    )


@app.get("/quality-options")
async def get_quality_options():
    """
    get available quality options with descriptions
    
    returns:
        dictionary of quality levels and their settings
    """
    return {
        "options": [
            {
                "value": quality.value,
                "label": quality.value.title(),
                "zoom": settings["zoom"],
                "description": settings["description"]
            }
            for quality, settings in QUALITY_SETTINGS.items()
        ],
        "default": MeshQuality.MEDIUM.value
    }


@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """
    get progress for a generation job
    
    args:
        job_id: job identifier
    
    returns:
        progress information (percent, message, status)
    """
    if job_id not in progress_store:
        raise HTTPException(status_code=404, detail="job not found")
    
    return progress_store[job_id]


@app.post("/generate")
async def generate_mesh(request: GenerateRequest):
    """
    generate 3d mesh for the specified bounding box
    
    args:
        request: contains bounding box and quality settings
    
    returns:
        zip file containing .obj, .mtl, and texture .png files
    """
    try:
        # validate bounding box
        request.bbox.validate_bbox()
        
        # get quality settings
        quality_config = QUALITY_SETTINGS[request.quality]
        
        # get mapbox token
        mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
        if not mapbox_token:
            raise HTTPException(
                status_code=500,
                detail="MAPBOX_ACCESS_TOKEN not configured"
            )
        
        # create or use provided job id
        job_id = request.job_id or str(uuid.uuid4())
        
        # initialize progress
        progress_store[job_id] = {
            "percent": 0,
            "message": "starting...",
            "status": "processing"
        }
        
        # progress callback
        def update_progress(percent: int, message: str):
            progress_store[job_id] = {
                "percent": percent,
                "message": message,
                "status": "processing"
            }
        
        # generate mesh with quality settings
        # see docs/logic/mesh_pipeline.md for full pipeline details
        generator = MeshGenerator(TEMP_DIR, mapbox_token)
        obj_path, mtl_path, texture_files = generator.generate(
            north=request.bbox.north,
            south=request.bbox.south,
            east=request.bbox.east,
            west=request.bbox.west,
            include_buildings=True,
            include_textures=True,
            zoom_level=quality_config["zoom"],
            texture_max_dimension=quality_config["texture_max"],
            progress_callback=update_progress
        )
        
        # verify obj file exists
        if not os.path.exists(obj_path):
            raise HTTPException(status_code=500, detail="generated file not found")
        
        # collect all files to include in zip
        files_to_zip = [obj_path]
        
        if mtl_path and os.path.exists(mtl_path):
            files_to_zip.append(mtl_path)
        
        # add texture files
        for texture_path in texture_files:
            if os.path.exists(texture_path):
                files_to_zip.append(texture_path)
        
        # check for material_0.png (created by trimesh)
        obj_dir = os.path.dirname(obj_path)
        material_png = os.path.join(obj_dir, "material_0.png")
        if os.path.exists(material_png) and material_png not in files_to_zip:
            files_to_zip.append(material_png)
        
        # create zip file
        zip_path = os.path.join(TEMP_DIR, "geomesh.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_zip:
                # add file with just its basename (no directory structure)
                zipf.write(file_path, arcname=os.path.basename(file_path))
        
        # mark as complete
        progress_store[job_id] = {
            "percent": 100,
            "message": "complete!",
            "status": "complete"
        }
        
        # return zip file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="tark.zip"
        )
        
    except ValueError as e:
        if request.job_id:
            progress_store[request.job_id] = {
                "percent": 0,
                "message": str(e),
                "status": "error"
            }
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if request.job_id:
            progress_store[request.job_id] = {
                "percent": 0,
                "message": f"error: {str(e)}",
                "status": "error"
            }
        raise HTTPException(status_code=500, detail=f"internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

