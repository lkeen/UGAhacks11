"""End-to-end demo of the disaster relief orchestrator with Claude integration."""

import asyncio
import json
import logging
import sys
from datetime import datetime

from backend.orchestrator import Orchestrator

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")


def pretty_print(label: str, data: dict | list | str) -> None:
    """Pretty-print a section with a header."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


async def run_demo():
    """Run the full orchestrator demo."""

    print("\n" + "#" * 70)
    print("#  DISASTER RELIEF SUPPLY CHAIN OPTIMIZER — DEMO")
    print("#  Hurricane Helene | Western North Carolina | Sept 2024")
    print("#" * 70)

    # ------------------------------------------------------------------
    # 1. Initialize orchestrator
    # ------------------------------------------------------------------
    logger.info("Initializing orchestrator...")
    orchestrator = Orchestrator()
    claude_status = "CONNECTED" if orchestrator.client else "UNAVAILABLE (using fallback)"
    logger.info("Claude API: %s", claude_status)

    # ------------------------------------------------------------------
    # 2. Set scenario time — early morning Sept 27
    # ------------------------------------------------------------------
    scenario_time = datetime.fromisoformat("2024-09-27T14:00:00+00:00")
    orchestrator.set_scenario_time(scenario_time)
    logger.info("Scenario time set to %s", scenario_time.isoformat())

    # ------------------------------------------------------------------
    # 3. Gather intelligence from all agents
    # ------------------------------------------------------------------
    logger.info("Gathering intelligence from all agents...")
    intelligence = await orchestrator.gather_all_intelligence()

    intel_summary = {}
    for source, reports in intelligence.items():
        intel_summary[source] = {
            "count": len(reports),
            "types": list(set(r.event_type.value for r in reports)),
        }
        logger.info(
            "  %s: %d reports — %s",
            source,
            len(reports),
            ", ".join(intel_summary[source]["types"][:5]),
        )

    pretty_print("INTELLIGENCE SUMMARY", intel_summary)

    # ------------------------------------------------------------------
    # 4. Apply intelligence to road network
    # ------------------------------------------------------------------
    edges_updated = orchestrator.apply_intelligence_to_network()
    logger.info("Road network updated: %d edges affected", edges_updated)

    stats = orchestrator.road_network.get_network_stats()
    pretty_print("ROAD NETWORK STATUS", stats)

    # ------------------------------------------------------------------
    # 5. Process a user query
    # ------------------------------------------------------------------
    query = "I have 200 water cases at Asheville airport. Where should they go?"
    logger.info('Processing query: "%s"', query)

    response = await orchestrator.process_query(query)

    pretty_print("PARSED QUERY", {
        "intent": response.get("delivery_plan", {}).get("origin"),
        "supplies": response.get("delivery_plan", {}).get("supplies"),
        "parsed_by": response.get("parsed_by"),
    })

    pretty_print("DELIVERY PLAN", response.get("delivery_plan", {}))
    pretty_print("CONFLICTS RESOLVED", response.get("conflicts_resolved", []))
    pretty_print("REASONING", response.get("reasoning", ""))

    # ------------------------------------------------------------------
    # 6. Advance time and show new intelligence
    # ------------------------------------------------------------------
    logger.info("Advancing scenario by 6 hours...")
    orchestrator.advance_scenario_time(6.0)
    new_intel = await orchestrator.gather_new_intelligence()

    new_summary = {
        source: len(reports) for source, reports in new_intel.items()
    }
    logger.info("New reports after time advance: %s", new_summary)
    pretty_print("NEW INTELLIGENCE (6h later)", new_summary)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print("\n" + "#" * 70)
    print("#  DEMO COMPLETE")
    print("#" * 70 + "\n")


def main():
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
