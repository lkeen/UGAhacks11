"""Command-line interface for the disaster relief orchestrator."""

import asyncio
import json
from datetime import datetime

from .orchestrator import Orchestrator


def print_header():
    """Print CLI header."""
    print("\n" + "=" * 60)
    print("  DISASTER RELIEF SUPPLY CHAIN OPTIMIZER")
    print("  Hurricane Helene - Western NC")
    print("=" * 60 + "\n")


def print_intelligence_summary(intelligence: dict):
    """Print summary of gathered intelligence."""
    print("\n📡 INTELLIGENCE SUMMARY")
    print("-" * 40)

    for source, reports in intelligence.items():
        if reports:
            print(f"\n{source.upper()} ({len(reports)} reports):")
            for report in reports[:3]:  # Show first 3
                print(f"  • [{report.event_type.value}] {report.description[:60]}...")
            if len(reports) > 3:
                print(f"  ... and {len(reports) - 3} more")


def print_delivery_plan(response: dict):
    """Print the delivery plan."""
    print("\n📦 DELIVERY PLAN")
    print("-" * 40)

    plan = response.get("delivery_plan", {})
    routes = plan.get("routes", [])

    if not routes:
        print("No viable delivery routes found.")
        return

    for i, route in enumerate(routes, 1):
        print(f"\n🚚 ROUTE {i}")
        print(f"   Distance: {route['distance_m']/1000:.1f} km")
        print(f"   Est. Time: {route['estimated_duration_min']:.0f} minutes")
        print(f"   Confidence: {route['confidence']:.0%}")
        print(f"   {route['reasoning']}")

        hazards = route.get("hazards_avoided", [])
        if hazards:
            print(f"   ⚠️  Avoiding {len(hazards)} hazard(s)")


def print_reasoning(response: dict):
    """Print the reasoning summary."""
    print("\n💡 REASONING")
    print("-" * 40)
    print(response.get("reasoning", "No reasoning available."))


async def demo_scenario():
    """Run a demo scenario showing the system capabilities."""
    print_header()

    print("Initializing orchestrator...")
    orchestrator = Orchestrator()

    # Set scenario time
    scenario_time = datetime.fromisoformat("2024-09-27T14:00:00+00:00")
    orchestrator.set_scenario_time(scenario_time)
    print(f"Scenario time: {scenario_time.strftime('%Y-%m-%d %H:%M UTC')}")

    # Demo query
    query = "I have 200 cases of water at the Asheville airport staging area. Which shelters need it most and what routes should I take?"

    print(f"\n📝 QUERY: {query}\n")
    print("Gathering intelligence from all agents...")

    # Process the query
    response = await orchestrator.process_query(query)

    # Print results
    print_intelligence_summary(orchestrator._last_intelligence)

    awareness = response.get("situational_awareness", {})
    print(f"\n📊 SITUATION OVERVIEW")
    print(f"   Total reports: {awareness.get('total_reports', 0)}")
    print(f"   Blocked roads: {awareness.get('blocked_roads', 0)}")
    print(f"   Damaged roads: {awareness.get('damaged_roads', 0)}")

    print_delivery_plan(response)
    print_reasoning(response)

    # Show JSON output option
    print("\n" + "=" * 60)
    print("Full JSON response available. Use --json flag to see it.")


async def interactive_mode():
    """Run interactive query mode."""
    print_header()

    print("Initializing orchestrator...")
    orchestrator = Orchestrator()

    scenario_time = datetime.fromisoformat("2024-09-27T14:00:00+00:00")
    orchestrator.set_scenario_time(scenario_time)

    print(f"Scenario time: {scenario_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print("\nType your supply routing questions. Type 'quit' to exit.\n")

    while True:
        try:
            query = input("Query> ").strip()

            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if not query:
                continue

            if query.startswith("time "):
                # Advance time
                try:
                    hours = float(query.split()[1])
                    orchestrator.advance_scenario_time(hours)
                    print(f"Advanced time by {hours} hours. Now: {orchestrator.scenario_time}")
                except (ValueError, IndexError):
                    print("Usage: time <hours>")
                continue

            print("\nProcessing query...")
            response = await orchestrator.process_query(query)

            print_delivery_plan(response)
            print_reasoning(response)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def run_cli():
    """Main CLI entry point."""
    import sys

    if "--demo" in sys.argv:
        asyncio.run(demo_scenario())
    elif "--json" in sys.argv:
        async def json_demo():
            orchestrator = Orchestrator()
            orchestrator.set_scenario_time(datetime.fromisoformat("2024-09-27T14:00:00+00:00"))
            response = await orchestrator.process_query(
                "I have 200 cases of water at Asheville airport. Where should they go?"
            )
            print(json.dumps(response, indent=2, default=str))

        asyncio.run(json_demo())
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    run_cli()
