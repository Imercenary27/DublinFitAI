import math
import requests
import networkx as nx
from utils.geospatial import calculate_distance

class OSMRoutePlanner:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        
    def get_osm_footways(self, center, radius):
        """Fetch pedestrian paths from OSM within given radius"""
        query = f"""
        [out:json];
        way(around:{radius},{center[0]},{center[1]})["highway"~"footway|path|pedestrian"];
        (._;>;);
        out body;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query)
            response.raise_for_status()
            return response.json()['elements']
        except Exception as e:
            print(f"OSM API Error: {e}")
            return []

    def build_pedestrian_graph(self, elements):
        """Build network graph from OSM elements"""
        G = nx.Graph()
        nodes = {}
        ways = []

        # Process nodes
        for element in elements:
            if element['type'] == 'node':
                nodes[element['id']] = (element['lat'], element['lon'])
            elif element['type'] == 'way':
                ways.append(element['nodes'])

        # Create edges with distances
        for way in ways:
            for i in range(len(way)-1):
                if way[i] in nodes and way[i+1] in nodes:
                    node1 = nodes[way[i]]
                    node2 = nodes[way[i+1]]
                    distance = calculate_distance(node1[0], node1[1], node2[0], node2[1])
                    G.add_edge(node1, node2, weight=distance)
                    
        return G

    def find_optimal_loop(self, G, start_point, target_distance):
        """Find loop route closest to target distance"""
        try:
            # Find nearest node to start point
            start_node = min(G.nodes(), key=lambda n: calculate_distance(
                start_point[0], start_point[1], n[0], n[1]
            ))
            
            # Find all simple paths returning to start
            paths = []
            for node in G.neighbors(start_node):
                try:
                    path = nx.shortest_path(G, start_node, node, weight='weight')
                    return_path = nx.shortest_path(G, node, start_node, weight='weight')
                    full_path = path + return_path[1:]
                    total_dist = sum(G[u][v]['weight'] for u,v in zip(full_path[:-1], full_path[1:]))
                    
                    if 0.8 * target_distance <= total_dist <= 1.2 * target_distance:
                        paths.append((full_path, total_dist))
                except nx.NetworkXNoPath:
                    continue
            
            if paths:
                # Select path closest to target distance
                best_path = min(paths, key=lambda x: abs(x[1] - target_distance))
                return [node for node in best_path[0]]
            
            # Fallback if no suitable paths found
            return self.create_fallback_route(start_point, target_distance)
            
        except Exception as e:
            print(f"Routing error: {e}")
            return self.create_fallback_route(start_point, target_distance)

    def create_fallback_route(self, center, distance):
        """Create circular route when no OSM paths found"""
        radius = distance / (2 * 3.14159)  # Circumference = 2πr
        points = []
        for angle in range(0, 360, 45):
            lat = center[0] + (radius / 111320) * math.cos(math.radians(angle))
            lon = center[1] + (radius / (111320 * math.cos(math.radians(center[0])))) * math.sin(math.radians(angle))
            points.append((lat, lon))
        points.append(points[0])  # Close the loop
        return points
