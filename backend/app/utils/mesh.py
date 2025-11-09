"""
Mesh utility functions
Helper functions for mesh operations and export
"""
import trimesh
from typing import List
import os


def merge_meshes(meshes: List[trimesh.Trimesh]) -> trimesh.Trimesh:
    """
    Merge multiple meshes into a single mesh
    
    Args:
        meshes: List of trimesh.Trimesh objects
    
    Returns:
        Single merged trimesh.Trimesh
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
    Export mesh to OBJ format with MTL
    
    Args:
        mesh: trimesh.Trimesh object
        output_path: Path for output .obj file (without extension)
        include_normals: Whether to include vertex normals
    
    Returns:
        Path to the exported .obj file
    """
    obj_path = f"{output_path}.obj"
    
    # Export with trimesh
    mesh.export(obj_path, file_type='obj', include_normals=include_normals)
    
    return obj_path


def optimize_mesh(
    mesh: trimesh.Trimesh,
    target_faces: int = None,
    merge_vertices: bool = True
) -> trimesh.Trimesh:
    """
    Optimize mesh for game engine use
    
    Args:
        mesh: Input mesh
        target_faces: Target face count (None = no decimation)
        merge_vertices: Whether to merge duplicate vertices
    
    Returns:
        Optimized mesh
    """
    # Merge duplicate vertices
    if merge_vertices:
        mesh.merge_vertices()
    
    # Remove degenerate faces
    mesh.remove_degenerate_faces()
    
    # Remove duplicate faces
    mesh.remove_duplicate_faces()
    
    # TODO: Add mesh decimation if target_faces is specified
    # This requires additional libraries like pymeshlab
    
    return mesh

