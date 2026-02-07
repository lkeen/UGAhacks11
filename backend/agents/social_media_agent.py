"""Social Media Intelligence Agent for disaster relief coordination."""

import json
from datetime import datetime
from pathlib import Path

from .base_agent import (
    AgentReport,
    BaseAgent,
    BoundingBox,
    DataSource,
    EventType,
    Location,
)


class SocialMediaAgent(BaseAgent):
    """
    Agent that processes social media posts to extract disaster intelligence.

    In production, this would use Twitter/X API and Reddit API.
    For the demo, we load from a curated dataset of mock posts based on
    real Hurricane Helene reports.
    """

    # Keywords that indicate different event types
    EVENT_KEYWORDS = {
        EventType.ROAD_CLOSURE: [
            "road closed", "road blocked", "can't get through",
            "impassable", "no access", "shut down", "closed off"
        ],
        EventType.BRIDGE_COLLAPSE: [
            "bridge out", "bridge collapsed", "bridge gone",
            "bridge washed away", "bridge destroyed"
        ],
        EventType.FLOODING: [
            "flooded", "underwater", "water rising", "flash flood",
            "river overflowing", "submerged"
        ],
        EventType.RESCUE_NEEDED: [
            "trapped", "stranded", "need rescue", "help needed",
            "people stuck", "evacuate"
        ],
        EventType.SUPPLIES_NEEDED: [
            "need water", "need food", "need medicine", "running out",
            "no supplies", "desperate for"
        ],
        EventType.POWER_OUTAGE: [
            "power out", "no electricity", "blackout", "no power",
            "lights out"
        ],
    }

    # Confidence adjustments based on source characteristics
    SOURCE_CONFIDENCE = {
        "verified_account": 0.15,
        "local_resident": 0.10,
        "photo_attached": 0.20,
        "video_attached": 0.25,
        "multiple_retweets": 0.10,
        "news_outlet": 0.15,
        "emergency_services": 0.25,
    }

    def __init__(
        self,
        name: str = "SocialMediaAgent",
        confidence_weight: float = 0.7,
        data_path: str | Path | None = None,
    ):
        """
        Initialize the Social Media Agent.

        Args:
            name: Agent name
            confidence_weight: Base confidence multiplier
            data_path: Path to mock social media data JSON file
        """
        super().__init__(name, confidence_weight)
        self.data_path = Path(data_path) if data_path else None
        self._mock_posts: list[dict] = []

    def load_mock_data(self, filepath: str | Path) -> None:
        """Load mock social media posts from JSON file."""
        filepath = Path(filepath)
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                self._mock_posts = data.get("posts", [])

    async def gather_intelligence(
        self,
        scenario_time: datetime,
        bbox: BoundingBox,
    ) -> list[AgentReport]:
        """
        Gather intelligence from social media sources.

        For the demo, this filters mock posts by time and location.
        In production, would query Twitter/Reddit APIs.

        Args:
            scenario_time: Current time in the disaster scenario
            bbox: Geographic area to search

        Returns:
            List of structured reports extracted from social media
        """
        reports = []

        # Load data if path is set and not loaded
        if self.data_path and not self._mock_posts:
            self.load_mock_data(self.data_path)

        for post in self._mock_posts:
            # Parse post timestamp
            post_time = datetime.fromisoformat(post["timestamp"].replace("Z", "+00:00"))

            # Skip posts after scenario time (haven't happened yet)
            if post_time > scenario_time:
                continue

            # Check if location is in bounding box
            location = Location(
                lat=post["location"]["lat"],
                lon=post["location"]["lon"],
            )
            if not bbox.contains(location):
                continue

            # Determine event type from content
            event_type = self._classify_event(post["content"])
            if event_type is None:
                continue  # Not a relevant post

            # Calculate base confidence
            confidence = self._calculate_confidence(post)

            # Create report
            report = AgentReport(
                timestamp=post_time,
                event_type=event_type,
                location=location,
                description=post["content"],
                source=DataSource.TWITTER if post.get("platform") == "twitter" else DataSource.REDDIT,
                confidence=confidence,
                raw_data=post,
                corroborations=post.get("retweets", 0) + post.get("replies", 0),
                agent_name=self.name,
                metadata={
                    "username": post.get("username"),
                    "platform": post.get("platform"),
                    "has_media": post.get("has_photo", False) or post.get("has_video", False),
                },
            )

            reports.append(report)
            self._reports.append(report)

        return reports

    def assess_confidence(self, report: AgentReport) -> float:
        """
        Calculate final confidence score for a social media report.

        Factors in:
        - Base confidence from source characteristics
        - Agent's confidence weight
        - Number of corroborations
        """
        base_confidence = report.confidence

        # Boost for corroborations (diminishing returns)
        corroboration_boost = min(0.2, report.corroborations * 0.02)

        # Apply agent weight
        final_confidence = (base_confidence + corroboration_boost) * self.confidence_weight

        # Clamp to [0, 1]
        return max(0.0, min(1.0, final_confidence))

    def _classify_event(self, content: str) -> EventType | None:
        """Classify social media post content into an event type."""
        content_lower = content.lower()

        for event_type, keywords in self.EVENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return event_type

        return None

    def _calculate_confidence(self, post: dict) -> float:
        """Calculate base confidence score for a post."""
        confidence = 0.4  # Base confidence for any social media post

        # Add boosts based on post characteristics
        if post.get("verified"):
            confidence += self.SOURCE_CONFIDENCE["verified_account"]
        if post.get("is_local"):
            confidence += self.SOURCE_CONFIDENCE["local_resident"]
        if post.get("has_photo"):
            confidence += self.SOURCE_CONFIDENCE["photo_attached"]
        if post.get("has_video"):
            confidence += self.SOURCE_CONFIDENCE["video_attached"]
        if post.get("retweets", 0) > 10:
            confidence += self.SOURCE_CONFIDENCE["multiple_retweets"]
        if post.get("is_news"):
            confidence += self.SOURCE_CONFIDENCE["news_outlet"]
        if post.get("is_emergency_services"):
            confidence += self.SOURCE_CONFIDENCE["emergency_services"]

        # Cap at 0.95 (social media never 100% reliable)
        return min(0.95, confidence)

    def extract_structured_event(self, content: str, location: Location) -> dict:
        """
        Use LLM to extract structured event data from raw post content.

        This is a placeholder for Claude API integration.
        Returns a structured dict that could be used for AgentReport.
        """
        # TODO: Integrate Claude API for intelligent extraction
        # For now, use rule-based extraction
        event_type = self._classify_event(content)

        return {
            "event_type": event_type.value if event_type else None,
            "location": location.to_dict(),
            "description": content,
            "confidence": 0.5,
            "extracted_entities": [],
        }
