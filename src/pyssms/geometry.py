"""Footprints of road users and the half-plane form of their Minkowski difference.

A road user is a convex polygon that translates without rotating (the assumption of
Laureshyn et al., 2010, Appendix A: "the line moves parallel to itself"). Shapes are stored
relative to the reference point (usually the centre) with vertices in counter-clockwise order,
as arrays of shape ``(N, V, 2)`` so that ``N`` encounters are processed at once.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]
BoolArray = NDArray[np.bool_]
StrArray = NDArray[np.str_]

__all__ = [
    "BoolArray",
    "FloatArray",
    "IntArray",
    "StrArray",
    "edge_normals",
    "minkowski_halfplanes",
    "rectangle",
    "rectangle_corners",
    "support",
]


def rectangle(heading: ArrayLike, length: ArrayLike, width: ArrayLike) -> FloatArray:
    """Rectangle footprints relative to their centre.

    Args:
        heading: Body orientation in radians, shape ``(N,)`` or scalar.
        length: Length along the heading (m).
        width: Width across the heading (m).

    Returns:
        Array ``(N, 4, 2)``: front-right, front-left, rear-left, rear-right (counter-clockwise).
    """
    h, ln, wd = np.broadcast_arrays(
        np.asarray(heading, dtype=float),
        np.asarray(length, dtype=float),
        np.asarray(width, dtype=float),
    )
    h, ln, wd = np.atleast_1d(h), np.atleast_1d(ln), np.atleast_1d(wd)
    fwd = np.stack([np.cos(h), np.sin(h)], axis=-1)
    left = np.stack([-np.sin(h), np.cos(h)], axis=-1)
    signs = np.array([[0.5, -0.5], [0.5, 0.5], [-0.5, 0.5], [-0.5, -0.5]])
    a = signs[None, :, 0] * ln[:, None]
    b = signs[None, :, 1] * wd[:, None]
    out: FloatArray = a[..., None] * fwd[:, None, :] + b[..., None] * left[:, None, :]
    return out


def rectangle_corners(
    x: ArrayLike, y: ArrayLike, heading: ArrayLike, length: ArrayLike, width: ArrayLike
) -> FloatArray:
    """Absolute corner coordinates ``(N, 4, 2)`` of rectangles centred at ``(x, y)``."""
    shape = rectangle(heading, length, width)
    centre = np.stack(np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float)), axis=-1)
    out: FloatArray = shape + np.atleast_2d(centre)[:, None, :]
    return out


def edge_normals(shape: FloatArray) -> FloatArray:
    """Outward unit normals ``(N, V, 2)`` of counter-clockwise polygons ``(N, V, 2)``."""
    edge = np.roll(shape, -1, axis=1) - shape
    n = np.stack([edge[..., 1], -edge[..., 0]], axis=-1)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    out: FloatArray = n / np.where(norm > 0, norm, 1.0)
    return out


def support(shape: FloatArray, direction: FloatArray) -> FloatArray:
    """Support function ``h(n) = max_p n.p`` for directions ``(N, K, 2)``; returns ``(N, K)``."""
    out: FloatArray = np.einsum("nkd,nvd->nkv", direction, shape).max(axis=-1)
    return out


def minkowski_halfplanes(shape1: FloatArray, shape2: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Half-planes ``n.x <= b`` of ``M = S1 (+) (-S2)``.

    Two bodies overlap exactly when the vector from reference point 1 to reference point 2
    lies in ``M``. The edge normals of a Minkowski sum of convex polygons are the union of the
    edge normals of the summands, so the description is exact (8 half-planes for two
    rectangles; repeated normals are harmless).

    Returns:
        ``normals`` ``(N, V1+V2, 2)`` and offsets ``b`` ``(N, V1+V2)``.
    """
    normals = np.concatenate([edge_normals(shape1), -edge_normals(shape2)], axis=1)
    b = support(shape1, normals) + support(shape2, -normals)
    return normals, b
