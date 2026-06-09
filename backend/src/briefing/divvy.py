"""Fetch Divvy bike-share availability from GBFS API."""

import logging
import math
from dataclasses import dataclass, field

import httpx

from src.briefing.constants import (
    API_TIMEOUT_SECONDS,
    FREE_BIKE_SEARCH_RADIUS_M,
    FREE_BIKE_STATUS_URL,
    HOME_LATITUDE,
    HOME_LONGITUDE,
    STATION_STATUS_URL,
    STATIONS,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StationAvailability:
    """Availability data for a single Divvy station."""

    station_id: str
    classic_bikes: int = 0
    ebikes: int = 0
    scooters: int = 0
    docks_available: int = 0
    is_installed: bool = True
    is_renting: bool = True
    is_returning: bool = True

    @property
    def total_vehicles(self) -> int:
        return self.classic_bikes + self.ebikes + self.scooters

    @property
    def is_active(self) -> bool:
        return self.is_installed and self.is_renting


@dataclass(frozen=True)
class NearbyFreeBikes:
    """Free-floating vehicles near the home station."""

    ebikes: int = 0
    scooters: int = 0


@dataclass
class DivvyData:
    """All Divvy data needed for the morning briefing."""

    home_primary: StationAvailability | None = None
    home_backup: StationAvailability | None = None
    optiver_dropoff: StationAvailability | None = None
    adyen_dropoff: StationAvailability | None = None
    nearby_free: NearbyFreeBikes = field(default_factory=NearbyFreeBikes)


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two lat/lon points in meters."""
    r = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_station(raw: dict) -> StationAvailability:
    """Parse a single station from the GBFS station_status response."""
    # Count vehicle types from vehicle_types_available (GBFS v2.3)
    classic = 0
    ebikes = 0
    scooters = 0
    for vt in raw.get("vehicle_types_available", []):
        vt_id = vt.get("vehicle_type_id", "")
        count = vt.get("count", 0)
        if "scooter" in vt_id.lower():
            scooters += count
        elif "electric" in vt_id.lower() or "ebike" in vt_id.lower():
            ebikes += count
        elif "classic" in vt_id.lower() or "bike" in vt_id.lower():
            classic += count

    # Fallback: if no vehicle_types_available, use num_bikes_available
    if classic == 0 and ebikes == 0 and scooters == 0:
        classic = raw.get("num_bikes_available", 0)

    return StationAvailability(
        station_id=raw.get("station_id", ""),
        classic_bikes=classic,
        ebikes=ebikes,
        scooters=scooters,
        docks_available=raw.get("num_docks_available", 0),
        is_installed=bool(raw.get("is_installed", 1)),
        is_renting=bool(raw.get("is_renting", 1)),
        is_returning=bool(raw.get("is_returning", 1)),
    )


async def fetch_station_status() -> dict[str, StationAvailability] | None:
    """Fetch station status from Divvy GBFS. Returns dict of station_id -> availability.

    Only returns data for stations we track (defined in STATIONS).
    Returns None on failure.
    """
    tracked_ids: set[str] = set()
    for group in STATIONS.values():
        for sid in group.values():
            tracked_ids.add(sid)

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            resp = await client.get(STATION_STATUS_URL)
            resp.raise_for_status()
            data = resp.json()

        stations_raw = data.get("data", {}).get("stations", [])
        result: dict[str, StationAvailability] = {}

        for raw in stations_raw:
            sid = raw.get("station_id", "")
            if sid in tracked_ids:
                result[sid] = _parse_station(raw)

        return result

    except httpx.TimeoutException:
        logger.error("Divvy station_status API timed out after %ds", API_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Divvy station_status returned HTTP %d", e.response.status_code)
        return None
    except Exception:
        logger.exception("Unexpected error fetching Divvy station status")
        return None


async def fetch_free_bikes() -> NearbyFreeBikes | None:
    """Fetch free-floating bikes/scooters near the home station.

    Filters to vehicles within FREE_BIKE_SEARCH_RADIUS_M of home.
    Returns None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            resp = await client.get(FREE_BIKE_STATUS_URL)
            resp.raise_for_status()
            data = resp.json()

        bikes_raw = data.get("data", {}).get("bikes", [])
        ebikes = 0
        scooters = 0

        for bike in bikes_raw:
            lat = bike.get("lat")
            lon = bike.get("lon")
            if lat is None or lon is None:
                continue

            distance = _haversine_meters(HOME_LATITUDE, HOME_LONGITUDE, lat, lon)
            if distance > FREE_BIKE_SEARCH_RADIUS_M:
                continue

            vehicle_type = bike.get("vehicle_type_id", "")
            if "scooter" in vehicle_type.lower():
                scooters += 1
            else:
                ebikes += 1

        return NearbyFreeBikes(ebikes=ebikes, scooters=scooters)

    except httpx.TimeoutException:
        logger.error("Divvy free_bike_status API timed out after %ds", API_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Divvy free_bike_status returned HTTP %d", e.response.status_code)
        return None
    except Exception:
        logger.exception("Unexpected error fetching Divvy free bikes")
        return None


def build_divvy_data(
    station_status: dict[str, StationAvailability] | None,
    free_bikes: NearbyFreeBikes | None,
) -> DivvyData:
    """Assemble DivvyData from raw API results. Handles partial failures."""
    divvy = DivvyData()

    if station_status:
        home_primary_id = STATIONS["home"]["primary"]
        home_backup_id = STATIONS["home"]["backup"]
        optiver_id = STATIONS["optiver"]["dropoff"]
        adyen_id = STATIONS["adyen"]["dropoff"]

        divvy.home_primary = station_status.get(home_primary_id)
        divvy.home_backup = station_status.get(home_backup_id)
        divvy.optiver_dropoff = station_status.get(optiver_id)
        divvy.adyen_dropoff = station_status.get(adyen_id)

    if free_bikes:
        divvy.nearby_free = free_bikes

    return divvy
