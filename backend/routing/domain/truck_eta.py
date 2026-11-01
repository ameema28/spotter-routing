"""Turn Mapbox car durations into truck travel time (D8 in DECISIONS.md).

Hours-of-service rules for property-carrying drivers, from:
- FMCSA summary (updated 2022-03-28):
  https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations
- 49 CFR 395.3 (edition dated 2023-10-01):
  https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol5/xml/CFR-2023-title49-vol5-sec395-3.xml

The model is one driver, starting rested, stopping exactly where a limit falls. Not modelled: rest-stop
locations, team driving, 60/70-hour limits, sleeper-berth split, adverse-conditions extension and
on-duty non-driving time.
"""
from dataclasses import dataclass

from routing.domain.geo import METERS_PER_MILE

SECONDS_PER_HOUR = 3600

# An assumption for a typical governed truck, not a legal limit: speed limits vary by state.
TRUCK_MAX_MPH = 65


@dataclass(frozen=True)
class HoursOfServiceRules:
    driving_before_break_s: float
    break_s: float
    driving_before_rest_s: float
    rest_s: float


# The 14-hour window never binds here: 11 h driving plus one 30-minute break is 11.5 h on duty.
HOURS_OF_SERVICE = HoursOfServiceRules(
    driving_before_break_s=8 * SECONDS_PER_HOUR,
    break_s=30 * 60,
    driving_before_rest_s=11 * SECONDS_PER_HOUR,
    rest_s=10 * SECONDS_PER_HOUR,
)


@dataclass(frozen=True)
class StopEvent:
    kind: str       # 'break' or 'rest'
    mile: float
    start_s: float  # Seconds from departure.
    end_s: float


def apply_speed_cap(seg_distances_m: list[float], seg_durations_s: list[float],
                    max_mph: float) -> list[float]:
    """Slow any segment faster than max_mph. Slower segments keep their traffic-aware time."""
    max_metres_per_second = max_mph * METERS_PER_MILE / SECONDS_PER_HOUR
    return [max(seconds, metres / max_metres_per_second)
            for metres, seconds in zip(seg_distances_m, seg_durations_s, strict=True)]


def add_rest_breaks(profile: list[tuple[float, float]],
                    rules: HoursOfServiceRules) -> tuple[list[tuple[float, float]], list[StopEvent]]:
    """Insert stops into a (mile, seconds) profile. Returns a new profile and the stops.

    Each stop adds two points at one mile, so an ETA at that mile is the arrival, before the stop.
    """
    new_profile = [profile[0]]
    events = []
    since_break = since_rest = stopped = 0.0
    for (mile, second), (end_mile, end_second) in zip(profile, profile[1:]):
        while True:
            driving = end_second - second
            until_stop = min(rules.driving_before_break_s - since_break,
                             rules.driving_before_rest_s - since_rest)
            # <= means a trip ending exactly on a limit needs no stop: the limit is on driving past it.
            if driving <= until_stop:
                break
            mile += (end_mile - mile) * until_stop / driving
            second += until_stop
            is_rest = since_rest + until_stop >= rules.driving_before_rest_s
            length = rules.rest_s if is_rest else rules.break_s
            start = second + stopped
            new_profile += [(mile, start), (mile, start + length)]
            events.append(StopEvent('rest' if is_rest else 'break', mile, start, start + length))
            stopped += length
            since_rest = 0.0 if is_rest else since_rest + until_stop
            since_break = 0.0
        since_break += driving
        since_rest += driving
        new_profile.append((end_mile, end_second + stopped))
    return new_profile, events
