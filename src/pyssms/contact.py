"""Which sides touch first: the face and corner of a collision course (state A).

The conflict polygon ``K`` of :mod:`pyssms.timetime` is cut out by one half-plane per edge of the
Minkowski difference ``M = S1 (+) (-S2)``, and every such edge comes from an edge of one of the two
bodies. On the diagonal ``tau1 == tau2`` the Time-to-Collision is the instant at which the diagonal
enters ``K``; the half-plane it crosses at that instant is the one that gets violated just before,
and it names the **face** of one body that meets a **corner** of the other body:

* a row ``k < V1`` is face ``k`` of body 1 (outward normal ``n_k``), met by the corner of body 2
  that is furthest in the direction ``-n_k``;
* a row ``k >= V1`` is face ``k - V1`` of body 2, met by the corner of body 1 furthest in the
  direction of the row normal.

When two rows enter at the same time (parallel faces, such as the front of one car meeting the rear
of another, or a corner meeting a corner) ``n_active`` is greater than 1 and the lowest-numbered
face is reported; the contact is then a face-to-face or corner-to-corner contact. Faces of
rectangles from :func:`pyssms.geometry.rectangle` are numbered front, left, rear, right.

Only collision courses (state A) have a contact; bodies that already overlap at ``tau = 0`` are
flagged ``already`` (no entry instant exists).

:func:`avoided_contact_faces` is the counterpart for crossing courses (state B), where nothing
touches. It names the faces and corners that **would** touch first if the road user that passes
first were delayed by the Time Advantage: the active edges of ``K`` at its closest point to the
diagonal. It is a different quantity, with its own result type, and is **not** a contact.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pyssms.geometry import BoolArray, FloatArray, IntArray, minkowski_halfplanes
from pyssms.timetime import _diagonal, _vertices, constraint_rows

__all__ = ["FACES", "AvoidedContact", "Contact", "avoided_contact_faces", "contact_faces"]

#: Names of the faces of a rectangle from :func:`pyssms.geometry.rectangle`, in row order.
FACES = ("front", "left", "rear", "right")

_EPS_ROW = 1e-12
_TOL = 1e-9


@dataclass(frozen=True)
class Contact:
    """First contact of each encounter on a collision course.

    Attributes:
        ttc: Time-to-Collision (s); NaN if the diagonal misses ``K`` within the horizon.
        body: Body (1 or 2) whose **face** is met first; 0 if there is no contact or the bodies
            already overlap.
        face: Index of that face (0-3 for rectangles, see :data:`FACES`); -1 if none.
        corner: Index of the vertex of the **other** body that meets it; -1 if none.
        n_active: Number of rows that enter within ``1e-9`` s of the first one (1 = a plain
            face-corner contact; more = a face-face or corner-corner tie).
        already: ``True`` where the bodies overlap at ``tau = 0``.
    """

    ttc: FloatArray
    body: IntArray
    face: IntArray
    corner: IntArray
    n_active: IntArray
    already: BoolArray


def contact_faces(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    horizon: float = 60.0,
) -> Contact:
    """Face and corner of the first contact for convex bodies that translate at constant velocity.

    Args:
        shape1: Footprint of road user 1 relative to its reference point, ``(N, V1, 2)``.
        pos1: Reference point, ``(N, 2)``.
        vel1: Velocity, ``(N, 2)``.
        shape2: Footprint of road user 2, ``(N, V2, 2)``.
        pos2: Reference point of road user 2.
        vel2: Velocity of road user 2.
        horizon: Prediction horizon (s).

    Returns:
        :class:`Contact`.
    """
    n, v1 = shape1.shape[0], shape1.shape[1]
    normals, b = minkowski_halfplanes(shape1, shape2)
    d = pos2 - pos1
    a = -np.einsum("nkd,nd->nk", normals, vel1)
    c = np.einsum("nkd,nd->nk", normals, vel2)
    r = b - np.einsum("nkd,nd->nk", normals, d)
    norm = np.hypot(a, c)
    flat = norm < _EPS_ROW
    ok = ~np.any(flat & (r < -_TOL), axis=1)
    safe = np.where(flat, 1.0, norm)
    a, c, r = a / safe, c / safe, np.where(flat, np.inf, r / safe)
    s = a + c
    neg = (s < -_EPS_ROW) & ~flat
    pos = (s > _EPS_ROW) & ~flat
    with np.errstate(divide="ignore", invalid="ignore"):
        q = r / s
    lo_rows = np.where(neg, q, -np.inf)
    hi = np.min(np.where(pos, q, np.inf), axis=1)
    lo = lo_rows.max(axis=1)
    zero_ok = np.all(np.where(~neg & ~pos, r >= -_TOL, True), axis=1)
    hit = ok & zero_ok & (lo <= hi + _TOL) & (np.maximum(lo, 0.0) < horizon - 1e-6)
    already = hit & (lo <= 0.0)
    enters = hit & (lo > 0.0)
    ttc = np.where(hit, np.maximum(lo, 0.0), np.nan)
    k = np.argmax(lo_rows, axis=1)
    n_active = np.sum(lo_rows >= (lo[:, None] - _TOL), axis=1)
    body = np.where(enters, np.where(k < v1, 1, 2), 0)
    face = np.where(enters, np.where(k < v1, k, k - v1), -1)
    rows = np.arange(n)
    nk = normals[rows, k]  # row normal of the entering half-plane
    # body 1 face: the corner of body 2 furthest along -n; body 2 face: corner of body 1 along n
    c2 = np.argmax(np.einsum("nd,nvd->nv", -nk, shape2), axis=1)
    c1 = np.argmax(np.einsum("nd,nvd->nv", nk, shape1), axis=1)
    corner = np.where(enters, np.where(k < v1, c2, c1), -1)
    return Contact(
        ttc=ttc,
        body=body.astype(np.int64),
        face=face.astype(np.int64),
        corner=corner.astype(np.int64),
        n_active=n_active.astype(np.int64),
        already=already,
    )


@dataclass(frozen=True)
class AvoidedContact:
    """Faces and corners that would touch first if the road user ahead were delayed by TAdv.

    For encounters in state B only (crossing courses): the ``(tau1, tau2)`` point of ``K`` closest
    to the diagonal is a vertex (or an edge parallel to the diagonal) where bodies touch; the
    active edges of ``K`` there name the contact. Arrays have one row per encounter and two
    columns for the (at most two) active contact edges, ordered by row number.

    Attributes:
        tadv: Time Advantage (s); NaN unless the state is B.
        first: Road user (1 or 2) that passes the avoided collision point first; 0 if none.
        tau1: Clock of road user 1 at the closest point (s).
        tau2: Clock of road user 2 at the closest point (s).
        body: Body (1 or 2) whose **face** is touched; 0 where the column is unused.
        face: Face index (see :data:`FACES`); -1 where unused.
        corner: Vertex of the **other** body that touches it; -1 where unused.
        n_active: Number of contact edges active at the point (2 = corner-corner contact, 1 =
            face-corner contact; more with parallel or repeated edges such as equal headings).
        horizon_active: ``True`` where an edge of the horizon box is active too: the closest point
            is limited by the prediction horizon (or by ``tau = 0``), so the contact named is
            only part of the story.
    """

    tadv: FloatArray
    first: IntArray
    tau1: FloatArray
    tau2: FloatArray
    body: IntArray
    face: IntArray
    corner: IntArray
    n_active: IntArray
    horizon_active: BoolArray


def avoided_contact_faces(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    horizon: float = 60.0,
) -> AvoidedContact:
    """Faces and corners of the avoided contact for crossing courses (state B).

    The conflict polygon ``K`` is the set of clock pairs ``(tau1, tau2)`` at which the bodies
    overlap; in state B it misses the diagonal and the Time Advantage is the smallest
    ``|tau1 - tau2|`` over ``K``, reached at a vertex of ``K`` (ties: the one with the smaller
    later clock, as in :func:`pyssms.timetime.indicators`). There the bodies **touch**: the edges of
    ``K`` that pass through the vertex are faces of one body meeting a corner of the other, as in
    :func:`contact_faces`. If the road user ``first`` were delayed by ``tadv`` the bodies would
    touch at that configuration, a graze, not an overlap. Encounters that are not in state B
    (collision course, no overlap) give ``tadv = NaN`` and unused columns.

    Args and shapes as in :func:`contact_faces`.

    Returns:
        :class:`AvoidedContact`.
    """
    n, v1 = shape1.shape[0], shape1.shape[1]
    normals, _ = minkowski_halfplanes(shape1, shape2)
    a, c, r, ok = constraint_rows(shape1, pos1, vel1, shape2, pos2, vel2, horizon)
    m_contact = a.shape[1] - 4
    edge = horizon - 1e-6
    ttc = np.where(ok, _diagonal(a, c, r), np.nan)
    on_course = np.isfinite(ttc) & (ttc < edge)
    verts, feas = _vertices(a, c, r)
    feas &= ok[:, None]
    tau1, tau2 = verts[..., 0], verts[..., 1]
    later = np.where(feas, np.maximum(tau1, tau2), np.inf)
    gap = np.where(feas, np.abs(tau1 - tau2), np.inf)
    best = gap.min(axis=1)
    tie = gap <= best[:, None] + _TOL
    k = np.argmin(np.where(tie, later, np.inf), axis=1)
    rows = np.arange(n)
    t1, t2 = tau1[rows, k], tau2[rows, k]
    valid = ~on_course & np.isfinite(best) & (later[rows, k] < edge)
    resid = r - (a * t1[:, None] + c * t2[:, None])  # >= 0 inside; ~0 on an active edge
    active = (np.abs(resid) <= 1e-7) & np.isfinite(r) & valid[:, None]
    act_c = active[:, :m_contact]
    n_active = act_c.sum(axis=1)
    horizon_active = valid & active[:, m_contact:].any(axis=1)
    body = np.zeros((n, 2), dtype=np.int64)
    face = np.full((n, 2), -1, dtype=np.int64)
    corner = np.full((n, 2), -1, dtype=np.int64)
    order = np.argsort(~act_c, axis=1, kind="stable")[:, :2]  # first two active rows
    for col in range(2):
        row_k = order[:, col]
        has = act_c[rows, row_k]
        nk = normals[rows, row_k]
        c2 = np.argmax(np.einsum("nd,nvd->nv", -nk, shape2), axis=1)
        c1 = np.argmax(np.einsum("nd,nvd->nv", nk, shape1), axis=1)
        is1 = row_k < v1
        body[:, col] = np.where(has, np.where(is1, 1, 2), 0)
        face[:, col] = np.where(has, np.where(is1, row_k, row_k - v1), -1)
        corner[:, col] = np.where(has, np.where(is1, c2, c1), -1)
    first = np.where(valid, np.where(t1 < t2, 1, 2), 0)
    return AvoidedContact(
        tadv=np.where(valid, np.abs(t1 - t2), np.nan),
        first=first.astype(np.int64),
        tau1=np.where(valid, t1, np.nan),
        tau2=np.where(valid, t2, np.nan),
        body=body,
        face=face,
        corner=corner,
        n_active=np.where(valid, n_active, 0).astype(np.int64),
        horizon_active=horizon_active,
    )
