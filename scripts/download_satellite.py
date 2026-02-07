#!/usr/bin/env python3
"""
Download Sentinel-2 satellite imagery for Hurricane Helene analysis.

This script downloads pre and post-disaster satellite imagery from
Copernicus Open Access Hub.

Prerequisites:
    1. Create account at: https://scihub.copernicus.eu/dhus/#/self-registration
    2. Set environment variables:
       - COPERNICUS_USER
       - COPERNICUS_PASSWORD

Usage:
    python scripts/download_satellite.py

Output:
    backend/data/satellite/pre_disaster_20240926.tif
    backend/data/satellite/post_disaster_20240928.tif
"""

import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_sentinel_imagery():
    """Download Sentinel-2 imagery for the disaster period."""
    try:
        from sentinelsat import SentinelAPI
    except ImportError:
        print("Error: sentinelsat is required.")
        print("Install with: pip install sentinelsat")
        sys.exit(1)

    # Get credentials from environment
    username = os.getenv("COPERNICUS_USER")
    password = os.getenv("COPERNICUS_PASSWORD")

    if not username or not password:
        print("Error: Copernicus credentials not found.")
        print("Set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables.")
        print("\nTo get credentials:")
        print("1. Go to https://scihub.copernicus.eu/dhus/#/self-registration")
        print("2. Create an account")
        print("3. Set the environment variables")
        print("\nAlternatively, run with --mock to create mock data for testing.")
        sys.exit(1)

    # Define area of interest (Western NC)
    # Using WKT format for the bounding box
    footprint = "POLYGON((-83.5 35.0, -81.5 35.0, -81.5 36.5, -83.5 36.5, -83.5 35.0))"

    # Connect to API
    print("Connecting to Copernicus Open Access Hub...")
    api = SentinelAPI(username, password, "https://scihub.copernicus.eu/dhus")

    # Output directory
    output_dir = Path(__file__).parent.parent / "backend" / "data" / "satellite"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Search for pre-disaster imagery (Sept 26, 2024)
    print("\nSearching for pre-disaster imagery (Sept 26, 2024)...")
    pre_products = api.query(
        footprint,
        date=(date(2024, 9, 24), date(2024, 9, 26)),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 20),
        producttype="S2MSI2A",  # Level-2A (atmospherically corrected)
    )
    print(f"Found {len(pre_products)} pre-disaster products")

    # Search for post-disaster imagery (Sept 28, 2024)
    print("\nSearching for post-disaster imagery (Sept 28, 2024)...")
    post_products = api.query(
        footprint,
        date=(date(2024, 9, 28), date(2024, 9, 30)),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 30),  # Allow more clouds post-disaster
        producttype="S2MSI2A",
    )
    print(f"Found {len(post_products)} post-disaster products")

    # Download best matches
    if pre_products:
        # Sort by cloud cover and download first
        pre_df = api.to_dataframe(pre_products)
        pre_df = pre_df.sort_values("cloudcoverpercentage")
        best_pre = pre_df.iloc[0]
        print(f"\nDownloading pre-disaster: {best_pre['title']}")
        print(f"  Cloud cover: {best_pre['cloudcoverpercentage']:.1f}%")
        print(f"  Date: {best_pre['beginposition']}")
        api.download(best_pre.name, directory_path=str(output_dir))
    else:
        print("No pre-disaster imagery found matching criteria")

    if post_products:
        post_df = api.to_dataframe(post_products)
        post_df = post_df.sort_values("cloudcoverpercentage")
        best_post = post_df.iloc[0]
        print(f"\nDownloading post-disaster: {best_post['title']}")
        print(f"  Cloud cover: {best_post['cloudcoverpercentage']:.1f}%")
        print(f"  Date: {best_post['beginposition']}")
        api.download(best_post.name, directory_path=str(output_dir))
    else:
        print("No post-disaster imagery found matching criteria")

    print("\nDownload complete!")
    print(f"Files saved to: {output_dir}")

    return True


def create_mock_imagery_info():
    """Create mock imagery metadata for testing without actual downloads."""
    import json
    from pathlib import Path

    print("Creating mock satellite imagery metadata...")

    # Mock metadata about what imagery would be available
    mock_info = {
        "description": "Mock satellite imagery metadata for Hurricane Helene analysis",
        "note": "Actual GeoTIFF files not included. Use Copernicus hub for real data.",
        "imagery": [
            {
                "id": "S2A_MSIL2A_20240926T160021_N0511_R097_T17SPV_20240926T213442",
                "date": "2024-09-26",
                "type": "pre_disaster",
                "platform": "Sentinel-2A",
                "product_type": "S2MSI2A",
                "cloud_cover_percent": 5.2,
                "tile_id": "T17SPV",
                "processing_level": "Level-2A",
                "bands": ["B02", "B03", "B04", "B08", "B11", "B12"],
                "resolution_m": 10,
                "footprint": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-83.5, 35.0],
                        [-81.5, 35.0],
                        [-81.5, 36.5],
                        [-83.5, 36.5],
                        [-83.5, 35.0],
                    ]],
                },
                "download_url": "https://scihub.copernicus.eu/dhus/odata/v1/Products('xxx')",
            },
            {
                "id": "S2B_MSIL2A_20240928T155819_N0511_R097_T17SPV_20240928T203145",
                "date": "2024-09-28",
                "type": "post_disaster",
                "platform": "Sentinel-2B",
                "product_type": "S2MSI2A",
                "cloud_cover_percent": 12.8,
                "tile_id": "T17SPV",
                "processing_level": "Level-2A",
                "bands": ["B02", "B03", "B04", "B08", "B11", "B12"],
                "resolution_m": 10,
                "footprint": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-83.5, 35.0],
                        [-81.5, 35.0],
                        [-81.5, 36.5],
                        [-83.5, 36.5],
                        [-83.5, 35.0],
                    ]],
                },
                "download_url": "https://scihub.copernicus.eu/dhus/odata/v1/Products('yyy')",
            },
        ],
        "analysis_notes": {
            "method": "NDWI change detection",
            "formula": "NDWI = (Green - NIR) / (Green + NIR)",
            "flood_threshold": 0.3,
            "bands_used": {
                "green": "B03 (560nm)",
                "nir": "B08 (842nm)",
                "swir": "B11 (1610nm)",
            },
        },
        "download_instructions": [
            "1. Register at https://scihub.copernicus.eu/dhus/#/self-registration",
            "2. Set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables",
            "3. Run: python scripts/download_satellite.py",
            "4. Alternatively, use Copernicus Browser: https://browser.dataspace.copernicus.eu/",
        ],
    }

    # Save to file
    output_dir = Path(__file__).parent.parent / "backend" / "data" / "satellite"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "imagery_metadata.json"
    with open(output_file, "w") as f:
        json.dump(mock_info, f, indent=2)

    print(f"Created mock metadata at: {output_file}")
    print("\nTo download actual imagery:")
    print("1. Register at https://scihub.copernicus.eu/dhus/#/self-registration")
    print("2. Set environment variables: COPERNICUS_USER, COPERNICUS_PASSWORD")
    print("3. Run: python scripts/download_satellite.py")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Sentinel-2 satellite imagery for Hurricane Helene"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Create mock metadata instead of downloading real imagery",
    )

    args = parser.parse_args()

    if args.mock:
        success = create_mock_imagery_info()
    else:
        success = download_sentinel_imagery()

    sys.exit(0 if success else 1)
