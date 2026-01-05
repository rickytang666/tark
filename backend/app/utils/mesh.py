"""
mesh utility functions
helper functions for mesh operations and export
"""
import trimesh
from typing import List
import os


def merge_meshes(meshes: List[trimesh.Trimesh]) -> trimesh.Trimesh:
    """
    merge multiple meshes into a single mesh
    
    args:
        meshes: list of trimesh.trimesh objects
    
    returns:
        single merged trimesh.trimesh
    """
    if not meshes:
        raise ValueError("No meshes to merge")
    
    if len(meshes) == 1:
        return meshes[0]
    
    return trimesh.util.concatenate(meshes)


def export_obj(
    mesh: trimesh.Trimesh,
    output_path: str,
    include_normals: bool = True
) -> str:
    """
    export mesh to obj format with mtl
    
    args:
        mesh: trimesh.trimesh object
        output_path: path for output .obj file (without extension)
        include_normals: whether to include vertex normals
    
    returns:
        path to the exported .obj file
    """
    obj_path = f"{output_path}.obj"
    
    print(f"      📝 Exporting to: {obj_path}")
    
    # export with trimesh
    # if a filename is provided, trimesh writes to disk and returns the exported bytes or None
    result = mesh.export(obj_path, file_type='obj', include_normals=include_normals)
    
    # Check if MTL was expected
    if hasattr(mesh.visual, 'material'):
        print(f"      🎨 Mesh has material: {type(mesh.visual.material)}")
        
        # Determine expected MTL filename
        # Trimesh typically names it based on the obj filename or 'material.mtl'
        # We can check the directory
        base_dir = os.path.dirname(obj_path)
        mtl_candidates = [f for f in os.listdir(base_dir) if f.endswith('.mtl')]
        print(f"      📂 MTL files in output dir: {mtl_candidates}")
    else:
        print("      ⚠️  Mesh has NO material attached!")
    
    return obj_path


def optimize_mesh(
    mesh: trimesh.Trimesh,
    target_faces: int = None,
    merge_vertices: bool = True
) -> trimesh.Trimesh:
    """
    optimize mesh for game engine use
    
    args:
        mesh: input mesh
        target_faces: target face count (none = no decimation)
        merge_vertices: whether to merge duplicate vertices
    
    returns:
        optimized mesh
    """
    # merge duplicate vertices
    if merge_vertices:
        mesh.merge_vertices()
    
    # remove degenerate faces
    mesh.remove_degenerate_faces()
    
    # remove duplicate faces
    mesh.remove_duplicate_faces()
    
    # todo: add mesh decimation if target_faces is specified
    # this requires additional libraries like pymeshlab
    
    return mesh

