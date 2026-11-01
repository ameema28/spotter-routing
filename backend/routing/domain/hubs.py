"""Major US interstate hub cities, used as via points for generated routes.

Coordinates are Census internal points, from the 2024 US Census Gazetteer place file:
https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip
They are stored here rather than geocoded because Mapbox results may not be kept.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Hub:
    name: str
    lat: float
    lon: float


HUBS = (
    Hub('Albany, NY', 42.6657, -73.7984),
    Hub('Albuquerque, NM', 35.1048, -106.6468),
    Hub('Amarillo, TX', 35.1981, -101.8331),
    Hub('Atlanta, GA', 33.7629, -84.4227),
    Hub('Billings, MT', 45.7885, -108.5525),
    Hub('Birmingham, AL', 33.5272, -86.7970),
    Hub('Boise, ID', 43.5993, -116.2298),
    Hub('Charlotte, NC', 35.2090, -80.8310),
    Hub('Cheyenne, WY', 41.1287, -104.7908),
    Hub('Chicago, IL', 41.8370, -87.6849),
    Hub('Cincinnati, OH', 39.1402, -84.5058),
    Hub('Cleveland, OH', 41.4785, -81.6794),
    Hub('Columbus, OH', 39.9839, -82.9849),
    Hub('Dallas, TX', 32.7933, -96.7665),
    Hub('Denver, CO', 39.7619, -104.8811),
    Hub('Des Moines, IA', 41.5726, -93.6102),
    Hub('El Paso, TX', 31.8478, -106.4311),
    Hub('Fargo, ND', 46.8647, -96.8291),
    Hub('Grand Junction, CO', 39.0891, -108.5675),
    Hub('Houston, TX', 29.7857, -95.3888),
    Hub('Indianapolis, IN', 39.7767, -86.1459),
    Hub('Jackson, MS', 32.3158, -90.2129),
    Hub('Jacksonville, FL', 30.3369, -81.6616),
    Hub('Kansas City, MO', 39.1252, -94.5503),
    Hub('Las Vegas, NV', 36.2335, -115.2640),
    Hub('Little Rock, AR', 34.7254, -92.3586),
    Hub('Louisville, KY', 38.2247, -85.7406),
    Hub('Memphis, TN', 35.1092, -89.9685),
    Hub('Minneapolis, MN', 44.9633, -93.2683),
    Hub('Nashville, TN', 36.1718, -86.7850),
    Hub('North Platte, NE', 41.1250, -100.7504),
    Hub('Oklahoma City, OK', 35.4671, -97.5137),
    Hub('Omaha, NE', 41.2627, -96.0535),
    Hub('Phoenix, AZ', 33.5722, -112.0901),
    Hub('Pittsburgh, PA', 40.4399, -79.9757),
    Hub('Portland, OR', 45.5370, -122.6500),
    Hub('Rapid City, SD', 44.0711, -103.2179),
    Hub('Reno, NV', 39.5491, -119.8499),
    Hub('Richmond, VA', 37.5314, -77.4760),
    Hub('Rock Springs, WY', 41.5947, -109.2209),
    Hub('Sacramento, CA', 38.5677, -121.4682),
    Hub('Salina, KS', 38.8131, -97.6145),
    Hub('Salt Lake City, UT', 40.7769, -111.9310),
    Hub('San Antonio, TX', 29.4628, -98.5246),
    Hub('Seattle, WA', 47.6193, -122.3515),
    Hub('Spokane, WA', 47.6669, -117.4333),
    Hub('Springfield, MO', 37.1942, -93.2926),
    Hub('St. Louis, MO', 38.6357, -90.2446),
    Hub('Tulsa, OK', 36.1279, -95.9023),
    Hub('Wichita, KS', 37.6906, -97.3458),
)
