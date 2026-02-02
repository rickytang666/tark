"""
tark backend - fastapi application
generates game-ready 3d meshes from real-world locations
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum
import os
import math
import zipfile
import uuid
import traceback
from pathlib import Path
from dotenv import load_dotenv
from app.generator import MeshGenerator
import redis
import json
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from pythonjsonlogger import jsonlogger
from prometheus_fastapi_instrumentator import Instrumentator

# load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="tark api",
    description="generate game-ready 3d meshes from real-world locations",
    version="0.1.0"
)

# setup metrics
Instrumentator().instrument(app).expose(app)

# setup json logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(message)s %(module)s"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# setup rate limiter
def rate_limit_key(request: Request):
    """
    custom key for rate limiting
    exempts localhost ('owner')
    """
    if request.client.host in ["127.0.0.1", "localhost", "::1"]:
        # allow mocking ip for testing (only from localhost)
        mock_ip = request.headers.get("x-mock-ip")
        if mock_ip:
            return mock_ip
        return None
    return get_remote_address(request)

limiter = Limiter(key_func=rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# cors middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

import tempfile

# system temp dir prevents workspace clutter
TEMP_DIR = os.path.join(tempfile.gettempdir(), "tark_gen")
os.makedirs(TEMP_DIR, exist_ok=True)

# redis setup
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

def set_job_progress(job_id: str, data: dict):
    """save job progress to redis (1h expiry)"""
    # serializing as json preserves types (int vs str)
    redis_client.setex(f"job:{job_id}", 3600, json.dumps(data))

def get_job_progress(job_id: str) -> Optional[dict]:
    """get job progress from redis"""
    data = redis_client.get(f"job:{job_id}")
    if data:
        return json.loads(data)
    return None


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
        progress information (percent, message, status, download_url)
    """
    progress = get_job_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="job not found")
    
    return progress


@app.get("/download/{job_id}")
async def download_mesh(job_id: str, background_tasks: BackgroundTasks):
    """
    download result for a completed job
    
    args:
        job_id: job identifier
        background_tasks: fastapi background task handler
    
    returns:
        zip file if job is complete
    """
    progress = get_job_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="job not found")
    
    job = progress
    
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="job not complete")
    
    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="result file not found")
    
    # schedule file deletion after response is sent
    background_tasks.add_task(os.remove, file_path)
    
    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename="tark.zip"
    )


def _run_generation_sync(job_id: str, bbox: BoundingBox, quality: MeshQuality, mapbox_token: str):
    """
    sync worker for mesh generation (CPU bound)
    """
    import shutil
    import time
    import trimesh
    
    start_time = time.time()
    
    # create job-specific temp dir to avoid collisions
    job_dir = os.path.join(TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    try:
        # get quality settings
        quality_config = QUALITY_SETTINGS[quality]
        
        # progress callback
        def update_progress(percent: int, message: str):
            set_job_progress(job_id, {
                "percent": percent,
                "message": message,
                "message": message,
                "status": "processing"
            })
            
        logger.info("job_started", extra={"job_id": job_id, "bbox": bbox.dict()})
        
        # generate mesh
        # use job_dir to avoid collisions
        generator = MeshGenerator(job_dir, mapbox_token)
        obj_path, mtl_path, texture_files = generator.generate(
            north=bbox.north,
            south=bbox.south,
            east=bbox.east,
            west=bbox.west,
            include_buildings=True,
            include_textures=True,
            zoom_level=quality_config["zoom"],
            texture_max_dimension=quality_config["texture_max"],
            progress_callback=update_progress
        )
        
        # verify obj file exists
        if not os.path.exists(obj_path):
            raise Exception("generated file not found")
            
        # calculate stats
        try:
            mesh = trimesh.load(obj_path)
            # trimesh.load might return Scene or Trimesh
            if isinstance(mesh, trimesh.Scene):
                vertex_count = sum(len(g.vertices) for g in mesh.geometry.values())
            else:
                vertex_count = len(mesh.vertices)
        except Exception as e:
            logger.warning("stats_calc_failed", extra={"error": str(e)})
            vertex_count = 0
        
        # collect all files to include in zip
        files_to_zip = [obj_path]
        
        if mtl_path and os.path.exists(mtl_path):
            files_to_zip.append(mtl_path)
        
        # add texture files
        for texture_path in texture_files:
            if os.path.exists(texture_path):
                files_to_zip.append(texture_path)
        
        # ensure all mtl and png files are included
        # trimesh may auto-generate materials with unpredictable names
        obj_dir = os.path.dirname(obj_path)
        for f in os.listdir(obj_dir):
            full_path = os.path.join(obj_dir, f)
            if full_path in files_to_zip:
                continue
                
            # include mtl files and material pngs
            if f.endswith('.mtl') or (f.endswith('.png') and 'material' in f):
                files_to_zip.append(full_path)
        
        # create zip in main temp dir
        zip_filename = f"tark_{job_id}.zip"
        zip_path = os.path.join(TEMP_DIR, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_zip:
                # add file with just its basename (no directory structure)
                zipf.write(file_path, arcname=os.path.basename(file_path))
        
        # cleanup raw files
        try:
            shutil.rmtree(job_dir)
        except Exception as e:
            logger.warning("cleanup_warning", extra={"job_id": job_id, "error": str(e)})
        
        # mark as complete
        # mark as complete
        set_job_progress(job_id, {
            "percent": 100,
            "message": "complete!",
            "status": "complete",
            "file_path": zip_path
        })
        
        elapsed = time.time() - start_time
        
        logger.info("job_completed", extra={
            "job_id": job_id,
            "zip_path": zip_path,
            "duration_seconds": round(elapsed, 2),
            "vertex_count": vertex_count
        })
        
    except Exception as e:
        logger.error("job_failed", extra={"job_id": job_id, "error": str(e)})
        traceback.print_exc()
        set_job_progress(job_id, {
            "percent": 0,
            "message": f"error: {str(e)}",
            "status": "error"
        })
        # attempt cleanup on failure too
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
            except:
                pass



async def run_generation_task(job_id: str, bbox: BoundingBox, quality: MeshQuality, mapbox_token: str):
    """
    async wrapper for background generation
    """
    await asyncio.to_thread(
        _run_generation_sync, 
        job_id, 
        bbox, 
        quality, 
        mapbox_token
    )


@app.post("/generate")
@limiter.limit("5/minute")
async def generate_mesh(
    request: Request,
    body: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    start background job to generate 3d mesh
    
    args:
        request: fastapi request object (required for ratelimit)
        body: contains bounding box and quality settings
        background_tasks: fastapi background task handler
    
    returns:
        json object with job_id
    """
    try:
        # validate bounding box immediately
        body.bbox.validate_bbox()
        
        # get mapbox token
        mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
        if not mapbox_token:
            raise HTTPException(
                status_code=500,
                detail="MAPBOX_ACCESS_TOKEN not configured"
            )
        
        # create or use provided job id
        job_id = body.job_id or str(uuid.uuid4())
        
        # initialize progress
        set_job_progress(job_id, {
            "percent": 0,
            "message": "queued",
            "status": "queued"
        })
        
        # schedule background task
        background_tasks.add_task(
            run_generation_task,
            job_id,
            body.bbox,
            body.quality,
            mapbox_token
        )
        
        return {
            "job_id": job_id,
            "message": "job started",
            "status": "queued"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

