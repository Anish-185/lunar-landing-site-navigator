"""Earth eclipsing the Sun as seen from the Moon (a lunar eclipse seen from the surface)."""

from __future__ import annotations

import numpy as np


def angular_separation(az1, el1, az2, el2):
    """Great-circle angle (deg) between two az/el directions."""
    a1, e1, a2, e2 = (np.radians(np.asarray(v, float)) for v in (az1, el1, az2, el2))
    c = np.sin(e1) * np.sin(e2) + np.cos(e1) * np.cos(e2) * np.cos(a1 - a2)
    return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))


def overlap_fraction(r_sun, r_earth, sep):
    """Fraction of the Sun's disc (radius r_sun) covered by Earth's disc (radius r_earth) at centre separation
    `sep` (all deg): the two-circle intersection area / (pi r_sun^2). Small-angle (flat) geometry."""
    r1, r2, d = np.broadcast_arrays(*(np.asarray(v, float) for v in (r_sun, r_earth, sep)))
    out = np.zeros(d.shape)
    full = d <= np.abs(r2 - r1)
    out[full] = np.where(r2[full] >= r1[full], 1.0, (r2[full] / r1[full]) ** 2)
    part = (d < r1 + r2) & ~full
    if part.any():
        a, b, s = r1[part], r2[part], d[part]
        x1 = np.clip((s * s + a * a - b * b) / (2 * s * a), -1, 1)
        x2 = np.clip((s * s + b * b - a * a) / (2 * s * b), -1, 1)
        k = np.sqrt(np.clip((-s + a + b) * (s + a - b) * (s - a + b) * (s + a + b), 0, None))
        area = a * a * np.arccos(x1) + b * b * np.arccos(x2) - 0.5 * k
        out[part] = area / (np.pi * a * a)
    return np.clip(out, 0.0, 1.0)


def effective_sun(disc_frac, eclipse_frac):
    """Share of the full Sun reaching the site: visible disc fraction x (1 - Earth-covered fraction)."""
    return np.asarray(disc_frac, float) * (1.0 - np.asarray(eclipse_frac, float))
