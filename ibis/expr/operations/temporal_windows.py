"""Temporal window operations."""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from public import public

import ibis.expr.datatypes as dt
from ibis.common.annotations import attribute
from ibis.common.collections import FrozenOrderedDict
from ibis.common.patterns import Attrs
from ibis.common.temporal import IntervalUnit
from ibis.expr.operations.core import Column, Scalar  # noqa: TC001
from ibis.expr.operations.relations import Relation, Unaliased
from ibis.expr.schema import Schema

# Constrain bucket_width to only calendar-safe interval units
# (i.e., units that can be used with timestamp arithmetic across all backends).
# This prevents, for example, mixing a microsecond interval with a
# millisecond-resolution timestamp column.
_BucketInterval = Annotated[
    dt.Interval,
    Attrs(unit=IntervalUnit),
]


@public
class WindowAggregate(Relation):
    parent: Relation
    window_type: Literal["tumble", "hop"]
    time_col: Unaliased[Column]
    groups: FrozenOrderedDict[str, Unaliased[Column]]
    metrics: FrozenOrderedDict[str, Unaliased[Scalar]]
    window_size: Scalar[dt.Interval]
    window_slide: Optional[Scalar[dt.Interval]] = None
    window_offset: Optional[Scalar[dt.Interval]] = None

    @attribute
    def values(self):
        return FrozenOrderedDict({**self.groups, **self.metrics})

    @attribute
    def schema(self):
        field_pairs = {
            "window_start": dt.timestamp,
            "window_end": dt.timestamp,
            **{k: v.dtype for k, v in self.groups.items()},
            **{k: v.dtype for k, v in self.metrics.items()},
        }
        return Schema(field_pairs)


@public
class GapFill(Relation):
    """Relational operation that generates a dense series of time buckets
    and left-joins the source relation onto it, filling gaps with NULLs.

    Parameters
    ----------
    parent
        The source relation containing sparse / irregular time-series rows.
    time_col
        The timestamp column used to bucket and align rows.
    bucket_width
        The fixed interval width for each generated bucket
        (e.g. 15 minutes, 1 hour, 1 day).
    groups
        Optional partition-by columns. A separate dense series is generated
        per unique combination of group keys.
    metrics
        Aggregated value columns that will be NULL for missing buckets.
    origin
        An optional interval offset from the UNIX epoch that shifts the
        bucket grid (e.g. to align buckets to a business-hour start).
    """

    parent: Relation
    time_col: Unaliased[Column]
    bucket_width: Scalar[dt.Interval]
    groups: FrozenOrderedDict[str, Unaliased[Column]]
    metrics: FrozenOrderedDict[str, Unaliased[Scalar]]
    origin: Optional[Scalar[dt.Interval]] = None

    @attribute
    def values(self):
        return FrozenOrderedDict({**self.groups, **self.metrics})

    @attribute
    def schema(self):
        # The output schema always leads with the bucket timestamp column,
        # followed by any group-by key columns, then the metric columns.
        # Metric columns may be NULL for missing buckets.
        field_pairs = {
            "bucket": dt.timestamp,
            **{k: v.dtype for k, v in self.groups.items()},
            **{k: v.dtype for k, v in self.metrics.items()},
        }
        return Schema(field_pairs)
