"""
overpass api fetcher for openstreetmap data
fetches building footprints and other features
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Any, Optional
import time


class OverpassFetcher:
    """
    fetches osm data via overpass api
    """
    
    def __init__(self, timeout: int = 45):
        """
        initialize overpass fetcher
        
        args:
            timeout: query timeout in seconds
        """
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.timeout = timeout
        
        # configure retry strategy
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
    
    def fetch_buildings(
        self,
        north: float,
        south: float,
        east: float,
        west: float
    ) -> List[Dict[str, Any]]:
        """
        fetch building footprints from osm
        
        args:
            north: north latitude
            south: south latitude
            east: east longitude
            west: west longitude
        
        returns:
            list of building dictionaries with footprints and metadata
        """
        # 1. build query
        query = self._build_query(north, south, east, west)
        
        # 2. send request
        try:
            # add user-agent header (good practice for osm)
            headers = {
                "User-Agent": "Tark3DGenerator/0.1.0"
            }
            
            response = self.session.post(
                self.base_url,
                data={"data": query},
                headers=headers,
                timeout=self.timeout + 10  # allow some buffer over the query timeout
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            # try backup server if main one fails
            try:
                print(f"Main Overpass server failed: {e}. Trying backup...")
                backup_url = "https://lz4.overpass-api.de/api/interpreter"
                response = self.session.post(
                    backup_url,
                    data={"data": query},
                    headers=headers,
                    timeout=self.timeout + 10
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e2:
                raise Exception(f"Overpass API request failed (main and backup): {e2}")
        
        # 3. parse response
        buildings = self._parse_response(data)
        
        return buildings
    
    def _build_query(self, north: float, south: float, east: float, west: float) -> str:
        """
        build overpass ql query for buildings
        
        args:
            north, south, east, west: bounding box coordinates
        
        returns:
            overpass ql query string
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
        parse overpass api response into building data
        
        args:
            data: json response from overpass api
        
        returns:
            list of building dictionaries
        """
        elements = data.get("elements", [])
        
        # separate nodes, ways, and relations
        nodes = {elem["id"]: elem for elem in elements if elem["type"] == "node"}
        ways = [elem for elem in elements if elem["type"] == "way" and "tags" in elem]
        relations = [elem for elem in elements if elem["type"] == "relation" and "tags" in elem]
        
        buildings = []
        
        # process ways (most buildings are ways)
        for way in ways:
            building = self._parse_way(way, nodes)
            if building:
                buildings.append(building)
        
        # process relations (complex buildings)
        for relation in relations:
            building = self._parse_relation(relation, nodes, {w["id"]: w for w in ways})
            if building:
                buildings.append(building)
        
        return buildings
    
    def _parse_way(self, way: Dict[str, Any], nodes: Dict[int, Dict]) -> Optional[Dict[str, Any]]:
        """
        parse a way (simple building) into building data
        
        args:
            way: way element from osm
            nodes: dictionary of node_id -> node data
        
        returns:
            building dictionary or none if invalid
        """
        tags = way.get("tags", {})
        node_ids = way.get("nodes", [])
        
        # get coordinates for all nodes
        coordinates = []
        for node_id in node_ids:
            if node_id in nodes:
                node = nodes[node_id]
                coordinates.append([node["lon"], node["lat"]])
        
        if len(coordinates) < 3:
            return None  # not a valid polygon
        
        # extract building metadata
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
        parse a relation (complex building) into building data
        
        handles complex buildings with multiple outer ways (l-shaped, u-shaped, etc.)
        and inner ways (courtyards/holes).
        
        args:
            relation: relation element from osm
            nodes: dictionary of node_id -> node data
            ways: dictionary of way_id -> way data
        
        returns:
            building dictionary or none if invalid
        """
        tags = relation.get("tags", {})
        members = relation.get("members", [])
        
        # get outer and inner ways
        outer_ways = [m for m in members if m.get("role") == "outer" and m["type"] == "way"]
        inner_ways = [m for m in members if m.get("role") == "inner" and m["type"] == "way"]
        
        if not outer_ways:
            return None
        
        # parse all outer ways (not just first!) to preserve complex shapes
        all_outer_coordinates = []
        for outer_way_member in outer_ways:
            way_id = outer_way_member["ref"]
            if way_id not in ways:
                continue
            
            way = ways[way_id]
            node_ids = way.get("nodes", [])
            
            for node_id in node_ids:
                if node_id in nodes:
                    node = nodes[node_id]
                    all_outer_coordinates.append([node["lon"], node["lat"]])
        
        if len(all_outer_coordinates) < 3:
            return None
        
        # remove duplicate consecutive points (where ways connect)
        coordinates = []
        for i, coord in enumerate(all_outer_coordinates):
            if i == 0 or coord != coordinates[-1]:
                coordinates.append(coord)
        
        # parse inner ways (courtyards/holes)
        holes = []
        for inner_way_member in inner_ways:
            way_id = inner_way_member["ref"]
            if way_id not in ways:
                continue
            
            way = ways[way_id]
            node_ids = way.get("nodes", [])
            
            hole_coords = []
            for node_id in node_ids:
                if node_id in nodes:
                    node = nodes[node_id]
                    hole_coords.append([node["lon"], node["lat"]])
            
            if len(hole_coords) >= 3:
                holes.append(hole_coords)
        
        building_type = tags.get("building", "yes")
        height = self._extract_height(tags)
        levels = self._extract_levels(tags)
        name = tags.get("name", None)
        
        return {
            "id": relation["id"],
            "type": "relation",
            "coordinates": coordinates,
            "holes": holes,  # new: support for courtyards
            "building_type": building_type,
            "height": height,
            "levels": levels,
            "name": name,
            "tags": tags
        }
    
    def _extract_height(self, tags: Dict[str, str]) -> Optional[float]:
        """extract building height from tags"""
        # try explicit height tag
        if "height" in tags:
            try:
                height_str = tags["height"].replace("m", "").strip()
                return float(height_str)
            except ValueError:
                pass
        
        # try building:height
        if "building:height" in tags:
            try:
                height_str = tags["building:height"].replace("m", "").strip()
                return float(height_str)
            except ValueError:
                pass
        
        return None
    
    def _extract_levels(self, tags: Dict[str, str]) -> Optional[int]:
        """extract number of building levels from tags"""
        # try building:levels
        if "building:levels" in tags:
            try:
                return int(tags["building:levels"])
            except ValueError:
                pass
        
        # try levels
        if "levels" in tags:
            try:
                return int(tags["levels"])
            except ValueError:
                pass
        
        return None

