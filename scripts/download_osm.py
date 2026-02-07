#!/usr/bin/env python3
"""
Download OpenStreetMap road network for Western North Carolina.

This script downloads the drivable road network for the Asheville region
using OSMnx and exports it to GeoJSON format.

Usage:
    python scripts/download_osm.py

Output:
    backend/data/osm/western_nc_roads.geojson
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_road_network():
    """Download and save the road network."""
    try:
        import osmnx as ox
        import geopandas as gpd
    except ImportError:
        print("Error: osmnx and geopandas are required.")
        print("Install with: pip install osmnx geopandas")
        sys.exit(1)

    # Configure OSMnx
    ox.settings.log_console = True
    ox.settings.use_cache = True

    # Define bounding box for Western NC
    # Covers Asheville, Hendersonville, Black Mountain, Boone, etc.
    north = 36.5
    south = 35.0
    east = -81.5
    west = -83.5

    print(f"Downloading road network for Western NC...")
    print(f"Bounding box: N={north}, S={south}, E={east}, W={west}")

    try:
        # Download road network
        # network_type='drive' gets roads that cars can use
        G = ox.graph_from_bbox(
            north=north,
            south=south,
            east=east,
            west=west,
            network_type="drive",
            simplify=True,
        )

        print(f"Downloaded {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

        # Convert to GeoDataFrame for export
        nodes, edges = ox.graph_to_gdfs(G)

        # Prepare output directory
        output_dir = Path(__file__).parent.parent / "backend" / "data" / "osm"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save edges (roads) as GeoJSON
        edges_file = output_dir / "western_nc_roads.geojson"
        edges_simplified = edges[["geometry", "osmid", "name", "highway", "length", "oneway"]].copy()
        edges_simplified.to_file(edges_file, driver="GeoJSON")
        print(f"Saved roads to: {edges_file}")

        # Save nodes (intersections) as GeoJSON
        nodes_file = output_dir / "western_nc_nodes.geojson"
        nodes_simplified = nodes[["geometry", "street_count"]].copy()
        nodes_simplified.to_file(nodes_file, driver="GeoJSON")
        print(f"Saved nodes to: {nodes_file}")

        # Also save as GraphML for potential use with NetworkX directly
        graphml_file = output_dir / "western_nc_roads.graphml"
        ox.save_graphml(G, graphml_file)
        print(f"Saved graph to: {graphml_file}")

        # Print summary
        print("\n" + "=" * 50)
        print("DOWNLOAD COMPLETE")
        print("=" * 50)
        print(f"Total nodes: {G.number_of_nodes():,}")
        print(f"Total edges: {G.number_of_edges():,}")

        # Count road types
        highway_counts = edges["highway"].value_counts()
        print("\nRoad types:")
        for highway_type, count in highway_counts.head(10).items():
            print(f"  {highway_type}: {count:,}")

        return True

    except Exception as e:
        print(f"Error downloading road network: {e}")
        return False


def create_sample_network():
    """Create a small sample network for testing without downloading."""
    import json
    from pathlib import Path

    print("Creating sample road network for testing...")

    # Sample road segments around Asheville
    sample_roads = {
        "type": "FeatureCollection",
        "features": [
            # I-40 segment
            {
                "type": "Feature",
                "properties": {
                    "osmid": "i40-001",
                    "name": "Interstate 40",
                    "highway": "motorway",
                    "length": 5000,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-82.6, 35.6],
                        [-82.5, 35.6],
                        [-82.4, 35.6],
                    ],
                },
            },
            # I-26 segment
            {
                "type": "Feature",
                "properties": {
                    "osmid": "i26-001",
                    "name": "Interstate 26",
                    "highway": "motorway",
                    "length": 8000,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-82.55, 35.6],
                        [-82.55, 35.5],
                        [-82.5, 35.4],
                    ],
                },
            },
            # US-25 segment
            {
                "type": "Feature",
                "properties": {
                    "osmid": "us25-001",
                    "name": "US Highway 25",
                    "highway": "primary",
                    "length": 10000,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-82.55, 35.6],
                        [-82.53, 35.5],
                        [-82.52, 35.45],
                    ],
                },
            },
            # NC-191 segment
            {
                "type": "Feature",
                "properties": {
                    "osmid": "nc191-001",
                    "name": "NC 191",
                    "highway": "secondary",
                    "length": 15000,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-82.6, 35.55],
                        [-82.7, 35.45],
                        [-82.75, 35.3],
                    ],
                },
            },
            # Downtown Asheville streets
            {
                "type": "Feature",
                "properties": {
                    "osmid": "patton-001",
                    "name": "Patton Avenue",
                    "highway": "tertiary",
                    "length": 2000,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-82.56, 35.595],
                        [-82.55, 35.595],
                        [-82.54, 35.595],
                    ],
                },
            },
        ],
    }

    # Save to file
    output_dir = Path(__file__).parent.parent / "backend" / "data" / "osm"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "western_nc_roads.geojson"
    with open(output_file, "w") as f:
        json.dump(sample_roads, f, indent=2)

    print(f"Created sample network at: {output_file}")
    print(f"Contains {len(sample_roads['features'])} road segments")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download OSM road network for Western NC")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Create a small sample network instead of downloading full data",
    )

    args = parser.parse_args()

    if args.sample:
        success = create_sample_network()
    else:
        success = download_road_network()

    sys.exit(0 if success else 1)
