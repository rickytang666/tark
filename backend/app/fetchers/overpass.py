"""
Overpass API fetcher for OpenStreetMap data
Fetches building footprints and other features
"""
import requests
from typing import List, Dict, Any, Optional


class OverpassFetcher:
    """
    Fetches OSM data via Overpass API
    """
    
    def __init__(self, timeout: int = 25):
        """
        Initialize Overpass fetcher
        
        Args:
            timeout: Query timeout in seconds
        """
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.timeout = timeout
    
    def fetch_buildings(
        self,
        north: float,
        south: float,
        east: float,
        west: float
    ) -> List[Dict[str, Any]]:
        """
        Fetch building footprints from OSM
        
        Args:
            north: North latitude
            south: South latitude
            east: East longitude
            west: West longitude
        
        Returns:
            List of building dictionaries with footprints and metadata
        """
        # 1. Build query
        query = self._build_query(north, south, east, west)
        
        # 2. Send request
        try:
            response = requests.post(
                self.base_url,
                data={"data": query},
                timeout=self.timeout + 5
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Overpass API request failed: {e}")
        
        # 3. Parse response
        buildings = self._parse_response(data)
        
        return buildings
    
    def _build_query(self, north: float, south: float, east: float, west: float) -> str:
        """
        Build Overpass QL query for buildings
        
        Args:
            north, south, east, west: Bounding box coordinates
        
        Returns:
            Overpass QL query string
        """
        bbox = f"{south},{west},{north},{east}"
        
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
          way["building"]({bbox});
          relation["building"]({bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        return query
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Overpass API response into building data
        
        Args:
            data: JSON response from Overpass API
        
        Returns:
            List of building dictionaries
        """
        elements = data.get("elements", [])
        
        # Separate nodes, ways, and relations
        nodes = {elem["id"]: elem for elem in elements if elem["type"] == "node"}
        ways = [elem for elem in elements if elem["type"] == "way" and "tags" in elem]
        relations = [elem for elem in elements if elem["type"] == "relation" and "tags" in elem]
        
        buildings = []
        
        # Process ways (most buildings are ways)
        for way in ways:
            building = self._parse_way(way, nodes)
            if building:
                buildings.append(building)
        
        # Process relations (complex buildings)
        for relation in relations:
            building = self._parse_relation(relation, nodes, {w["id"]: w for w in ways})
            if building:
                buildings.append(building)
        
        return buildings
    
    def _parse_way(self, way: Dict[str, Any], nodes: Dict[int, Dict]) -> Optional[Dict[str, Any]]:
        """
        Parse a way (simple building) into building data
        
        Args:
            way: Way element from OSM
            nodes: Dictionary of node_id -> node data
        
        Returns:
            Building dictionary or None if invalid
        """
        tags = way.get("tags", {})
        node_ids = way.get("nodes", [])
        
        # Get coordinates for all nodes
        coordinates = []
        for node_id in node_ids:
            if node_id in nodes:
                node = nodes[node_id]
                coordinates.append([node["lon"], node["lat"]])
        
        if len(coordinates) < 3:
            return None  # Not a valid polygon
        
        # Extract building metadata
        building_type = tags.get("building", "yes")
        height = self._extract_height(tags)
        levels = self._extract_levels(tags)
        name = tags.get("name", None)
        
        return {
            "id": way["id"],
            "type": "way",
            "coordinates": coordinates,
            "building_type": building_type,
            "height": height,
            "levels": levels,
            "name": name,
            "tags": tags
        }
    
    def _parse_relation(
        self,
        relation: Dict[str, Any],
        nodes: Dict[int, Dict],
        ways: Dict[int, Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a relation (complex building) into building data
        
        Args:
            relation: Relation element from OSM
            nodes: Dictionary of node_id -> node data
            ways: Dictionary of way_id -> way data
        
        Returns:
            Building dictionary or None if invalid
        """
        tags = relation.get("tags", {})
        members = relation.get("members", [])
        
        # Get outer way coordinates
        outer_ways = [m for m in members if m.get("role") == "outer" and m["type"] == "way"]
        
        if not outer_ways:
            return None
        
        # For MVP, just use first outer way
        way_id = outer_ways[0]["ref"]
        if way_id not in ways:
            return None
        
        way = ways[way_id]
        node_ids = way.get("nodes", [])
        
        coordinates = []
        for node_id in node_ids:
            if node_id in nodes:
                node = nodes[node_id]
                coordinates.append([node["lon"], node["lat"]])
        
        if len(coordinates) < 3:
            return None
        
        building_type = tags.get("building", "yes")
        height = self._extract_height(tags)
        levels = self._extract_levels(tags)
        name = tags.get("name", None)
        
        return {
            "id": relation["id"],
            "type": "relation",
            "coordinates": coordinates,
            "building_type": building_type,
            "height": height,
            "levels": levels,
            "name": name,
            "tags": tags
        }
    
    def _extract_height(self, tags: Dict[str, str]) -> Optional[float]:
        """Extract building height from tags"""
        # Try explicit height tag
        if "height" in tags:
            try:
                height_str = tags["height"].replace("m", "").strip()
                return float(height_str)
            except ValueError:
                pass
        
        # Try building:height
        if "building:height" in tags:
            try:
                height_str = tags["building:height"].replace("m", "").strip()
                return float(height_str)
            except ValueError:
                pass
        
        return None
    
    def _extract_levels(self, tags: Dict[str, str]) -> Optional[int]:
        """Extract number of building levels from tags"""
        # Try building:levels
        if "building:levels" in tags:
            try:
                return int(tags["building:levels"])
            except ValueError:
                pass
        
        # Try levels
        if "levels" in tags:
            try:
                return int(tags["levels"])
            except ValueError:
                pass
        
        return None

