from typing import Optional
from ..base import BaseScraper
from .test_track import TestTrackScraper

def get_scraper_for_track(track_name: str) -> Optional[BaseScraper]:
    """Factory function to get appropriate scraper for a track"""
    scrapers = {
        'Test Track': TestTrackScraper,
        'Belmont Park': TestTrackScraper,  # Using test scraper as placeholder
        'Santa Anita Park': TestTrackScraper,
        'Churchill Downs': TestTrackScraper,
    }
    
    scraper_class = scrapers.get(track_name)
    if scraper_class:
        return scraper_class()
    return None