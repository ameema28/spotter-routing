"""Request the main routes and third-route candidates together (D7 in DECISIONS.md)."""
import logging
from concurrent.futures import Future, ThreadPoolExecutor, wait

from routing.domain.alternatives import Candidate, select_hubs
from routing.domain.hubs import HUBS
from routing.services import mapbox
from routing.services.errors import ProviderError
from routing.services.mapbox import Route

logger = logging.getLogger(__name__)

# How long after the main call returns to keep waiting for candidates.
CANDIDATE_DEADLINE_SECONDS = 12


def _hub_label(name: str) -> str:
    return f'generated alternative (via {name.split(",")[0]})'


def _collect(label: str, future: Future) -> list[Candidate]:
    # A candidate is optional, so one failure must not lose the routes that worked.
    try:
        return [Candidate(label, route) for route in future.result()]
    except ProviderError as error:
        logger.warning('Skipped %s: %s', label, error)
        return []


def generate_candidates(origin: dict, destination: dict) -> tuple[list[Route], list[Candidate], int]:
    """Mapbox's own routes, every candidate that came back in time, and how many were too late.

    Only a failed main call raises. All calls are sent together because a new query can take about
    10 s, so waiting for the main call first could double a slow search.
    """
    hubs = select_hubs(origin, destination, HUBS)
    pool = ThreadPoolExecutor(max_workers=len(hubs) + 2)
    try:
        main = pool.submit(mapbox.directions, origin, destination)
        optional = [('generated alternative (avoids tolls)',
                     pool.submit(mapbox.directions, origin, destination, exclude='toll'))]
        optional += [(_hub_label(hub.name), pool.submit(mapbox.directions, origin, destination,
                                                        via={'lat': hub.lat, 'lon': hub.lon})) for hub in hubs]
        routes = main.result()
        _, unfinished = wait([future for _, future in optional], timeout=CANDIDATE_DEADLINE_SECONDS)
    finally:
        # Late calls finish on their own threads, so the driver's search never waits for them.
        pool.shutdown(wait=False, cancel_futures=True)

    candidates = []
    for label, future in optional:
        if future not in unfinished:
            candidates += _collect(label, future)
    return routes, candidates, len(unfinished)
