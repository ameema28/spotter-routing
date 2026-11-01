"""Request the main routes and third-route candidates together (D7 in DECISIONS.md)."""
import logging
from concurrent.futures import Future, ThreadPoolExecutor

from routing.domain.alternatives import Candidate, select_hubs
from routing.domain.hubs import HUBS
from routing.services import mapbox
from routing.services.errors import ProviderError
from routing.services.mapbox import Route

logger = logging.getLogger(__name__)


def _hub_label(name: str) -> str:
    return f'generated alternative (via {name.split(",")[0]})'


def _collect(label: str, future: Future) -> list[Candidate]:
    # A candidate is optional, so one failure must not lose the routes that worked.
    try:
        return [Candidate(label, route) for route in future.result()]
    except ProviderError as error:
        logger.warning('Skipped %s: %s', label, error)
        return []


def generate_candidates(origin: dict, destination: dict) -> tuple[list[Route], list[Candidate]]:
    """Mapbox's own routes, and every candidate that came back. Only a failed main call raises.

    Sent together because a new query can take about 10 s, so waiting for the main call first could
    double a slow search.
    """
    hubs = select_hubs(origin, destination, HUBS)
    with ThreadPoolExecutor(max_workers=len(hubs) + 2) as pool:
        main = pool.submit(mapbox.directions, origin, destination)
        tolls = pool.submit(mapbox.directions, origin, destination, exclude='toll')
        vias = [(hub, pool.submit(mapbox.directions, origin, destination,
                                  via={'lat': hub.lat, 'lon': hub.lon})) for hub in hubs]

    candidates = _collect('generated alternative (avoids tolls)', tolls)
    for hub, future in vias:
        candidates += _collect(_hub_label(hub.name), future)
    return main.result(), candidates
