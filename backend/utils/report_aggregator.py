"""Utilities for aggregating and analyzing agent reports."""

import math
from collections import defaultdict

from backend.agents.base_agent import AgentReport, EventType


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def group_reports_by_location(
    reports: list[AgentReport],
    proximity_km: float = 0.5,
) -> list[list[AgentReport]]:
    """
    Cluster reports that are geographically close together.

    Uses a simple greedy clustering approach: iterate reports and assign
    each to the first existing cluster within proximity_km, or start a
    new cluster.

    Args:
        reports: List of agent reports to cluster.
        proximity_km: Maximum distance in km to consider reports as co-located.

    Returns:
        List of clusters, where each cluster is a list of nearby reports.
    """
    clusters: list[list[AgentReport]] = []
    centroids: list[tuple[float, float]] = []

    for report in reports:
        assigned = False
        for i, (clat, clon) in enumerate(centroids):
            dist = _haversine_km(report.location.lat, report.location.lon, clat, clon)
            if dist <= proximity_km:
                clusters[i].append(report)
                # Update centroid as running average
                n = len(clusters[i])
                centroids[i] = (
                    clat + (report.location.lat - clat) / n,
                    clon + (report.location.lon - clon) / n,
                )
                assigned = True
                break

        if not assigned:
            clusters.append([report])
            centroids.append((report.location.lat, report.location.lon))

    return clusters


def calculate_consensus_confidence(reports: list[AgentReport]) -> float:
    """
    Calculate a weighted consensus confidence from multiple reports.

    More reports from diverse sources increase confidence.
    The formula combines individual confidences and adds a corroboration bonus.

    Args:
        reports: Reports about the same event/location.

    Returns:
        Consensus confidence score between 0.0 and 1.0.
    """
    if not reports:
        return 0.0

    if len(reports) == 1:
        return reports[0].confidence

    # Weighted average of individual confidences
    total_conf = sum(r.confidence for r in reports)
    avg_conf = total_conf / len(reports)

    # Diversity bonus: more unique sources = higher confidence
    unique_sources = len(set(r.source for r in reports))
    diversity_bonus = min(0.15, unique_sources * 0.05)

    # Corroboration bonus: capped at 0.10
    corroboration_bonus = min(0.10, (len(reports) - 1) * 0.03)

    return min(1.0, avg_conf + diversity_bonus + corroboration_bonus)


def identify_conflicting_reports(
    reports: list[AgentReport],
    proximity_km: float = 0.5,
) -> list[dict]:
    """
    Find contradicting reports about the same location.

    A conflict occurs when reports about the same area have opposing
    event types (e.g., ROAD_CLOSURE vs ROAD_CLEAR).

    Args:
        reports: All reports to scan for conflicts.
        proximity_km: Distance threshold for considering reports co-located.

    Returns:
        List of conflict dicts, each containing:
          - road_id: representative location string
          - reports: the conflicting AgentReport objects
          - types: set of conflicting EventType values
    """
    # Event types that contradict each other
    contradictions = {
        EventType.ROAD_CLOSURE: {EventType.ROAD_CLEAR},
        EventType.ROAD_CLEAR: {EventType.ROAD_CLOSURE, EventType.ROAD_DAMAGE},
        EventType.ROAD_DAMAGE: {EventType.ROAD_CLEAR},
        EventType.FLOODING: {EventType.ROAD_CLEAR},
    }

    clusters = group_reports_by_location(reports, proximity_km)
    conflicts = []

    for cluster in clusters:
        types_in_cluster = set(r.event_type for r in cluster)

        # Check if any event type in the cluster contradicts another
        has_conflict = False
        for etype in types_in_cluster:
            if etype in contradictions:
                if types_in_cluster & contradictions[etype]:
                    has_conflict = True
                    break

        if has_conflict:
            # Build a readable location identifier
            rep = cluster[0]
            road_id = (
                rep.location.address
                or f"{rep.location.lat:.4f},{rep.location.lon:.4f}"
            )
            conflicts.append({
                "road_id": road_id,
                "reports": cluster,
                "types": types_in_cluster,
            })

    return conflicts
