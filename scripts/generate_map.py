#!/usr/bin/env python3
"""
Generate an interactive map showing disaster situation.

Usage:
    python scripts/generate_map.py

Output:
    backend/data/situation_map.html
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def generate_map():
    """Generate an interactive map using folium."""
    try:
        import folium
        from folium.plugins import MarkerCluster
    except ImportError:
        print("Error: folium is required.")
        print("Install with: pip install folium")
        sys.exit(1)

    data_dir = Path(__file__).parent.parent / "backend" / "data"

    # Create map centered on Asheville
    m = folium.Map(
        location=[35.5951, -82.5515],
        zoom_start=9,
        tiles="OpenStreetMap",
    )

    # Add shelter markers
    shelters_file = data_dir / "shelters" / "shelters.json"
    if shelters_file.exists():
        with open(shelters_file) as f:
            shelter_data = json.load(f)

        shelter_cluster = MarkerCluster(name="Shelters")

        for shelter in shelter_data.get("shelters", []):
            if shelter.get("opened_at"):
                popup_html = f"""
                <b>{shelter['name']}</b><br>
                Capacity: {shelter.get('current_occupancy', 0)}/{shelter.get('capacity', 0)}<br>
                Needs: {', '.join(shelter.get('needs', [])[:3])}<br>
                Pets: {'Yes' if shelter.get('accepts_pets') else 'No'}
                """
                folium.Marker(
                    location=[shelter["location"]["lat"], shelter["location"]["lon"]],
                    popup=popup_html,
                    icon=folium.Icon(color="green", icon="home"),
                ).add_to(shelter_cluster)

        shelter_cluster.add_to(m)

    # Add event markers
    events_file = data_dir / "events" / "helene_timeline.json"
    if events_file.exists():
        with open(events_file) as f:
            event_data = json.load(f)

        # Different colors for different event types
        event_colors = {
            "road_closure": "red",
            "bridge_collapse": "darkred",
            "flooding": "blue",
            "power_outage": "orange",
            "supplies_needed": "purple",
            "rescue_needed": "cadetblue",
        }

        road_closures = folium.FeatureGroup(name="Road Closures")
        flooding = folium.FeatureGroup(name="Flooding")
        other_events = folium.FeatureGroup(name="Other Events")

        for event in event_data.get("events", []):
            if event["type"] in ["shelter_opening", "road_clear"]:
                continue  # Skip these

            color = event_colors.get(event["type"], "gray")
            popup_html = f"""
            <b>{event['type'].replace('_', ' ').title()}</b><br>
            {event.get('description', '')[:100]}...<br>
            Time: {event['timestamp']}<br>
            Source: {event.get('source', 'unknown')}
            """

            marker = folium.CircleMarker(
                location=[event["location"]["lat"], event["location"]["lon"]],
                radius=8,
                popup=popup_html,
                color=color,
                fill=True,
                fillOpacity=0.7,
            )

            if event["type"] in ["road_closure", "bridge_collapse"]:
                marker.add_to(road_closures)
            elif event["type"] == "flooding":
                marker.add_to(flooding)
            else:
                marker.add_to(other_events)

        road_closures.add_to(m)
        flooding.add_to(m)
        other_events.add_to(m)

    # Add satellite detections
    sat_file = data_dir / "satellite" / "detections.json"
    if sat_file.exists():
        with open(sat_file) as f:
            sat_data = json.load(f)

        sat_layer = folium.FeatureGroup(name="Satellite Detections")

        for detection in sat_data.get("detections", []):
            popup_html = f"""
            <b>Satellite Detection</b><br>
            Type: {detection['type']}<br>
            Confidence: {detection.get('confidence', 0):.0%}<br>
            {detection.get('description', '')}
            """

            folium.CircleMarker(
                location=[detection["location"]["lat"], detection["location"]["lon"]],
                radius=15,
                popup=popup_html,
                color="purple",
                fill=True,
                fillOpacity=0.3,
                weight=2,
            ).add_to(sat_layer)

        sat_layer.add_to(m)

    # Add supply depot markers
    if shelters_file.exists():
        with open(shelters_file) as f:
            depot_data = json.load(f)

        for depot in depot_data.get("supply_depots", []):
            supplies = depot.get("supplies", {})
            supply_list = "<br>".join([f"{k}: {v}" for k, v in supplies.items()])
            popup_html = f"""
            <b>{depot['name']}</b><br>
            <b>Supplies:</b><br>
            {supply_list}
            """
            folium.Marker(
                location=[depot["location"]["lat"], depot["location"]["lon"]],
                popup=popup_html,
                icon=folium.Icon(color="orange", icon="archive"),
            ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add title
    title_html = """
    <div style="position: fixed; top: 10px; left: 50px; z-index: 1000;
                background-color: white; padding: 10px; border-radius: 5px;
                border: 2px solid gray;">
        <h4 style="margin: 0;">Hurricane Helene - Western NC</h4>
        <p style="margin: 5px 0 0 0; font-size: 12px;">
            Disaster Relief Supply Chain Optimizer
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # Save map
    output_file = data_dir / "situation_map.html"
    m.save(str(output_file))
    print(f"Map saved to: {output_file}")
    print("Open this file in a browser to view the interactive map.")

    return True


if __name__ == "__main__":
    success = generate_map()
    sys.exit(0 if success else 1)
