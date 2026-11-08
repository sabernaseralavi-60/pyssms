"""pyssms: continuous surrogate safety indicators for road-user encounters.

TTC, Time Advantage, T2 and Time Gap for arbitrary approach angles, computed exactly on a
time-time conflict polygon.
"""

from pyssms.disturbance import DisturbanceSet, disturbance_set, form_probability
from pyssms.geometry import rectangle, rectangle_corners
from pyssms.margins import lateral_margin
from pyssms.severity import delta_v, extended_delta_v
from pyssms.stories import Story, first_contact, profile
from pyssms.timetime import Indicators, conflict_polygon, indicators, indicators_rect

__version__ = "0.1.0"
__all__ = [
    "DisturbanceSet",
    "Indicators",
    "Story",
    "__version__",
    "conflict_polygon",
    "delta_v",
    "disturbance_set",
    "extended_delta_v",
    "first_contact",
    "form_probability",
    "indicators",
    "indicators_rect",
    "lateral_margin",
    "profile",
    "rectangle",
    "rectangle_corners",
]
