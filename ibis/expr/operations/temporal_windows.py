"""Temporal window operations."""

from __future__ import annotations

from typing import Literal, Optional

from public import public

import ibis.expr.datatypes as dt
from ibis.common.annotations import attribute
from ibis.common.collections import FrozenOrderedDict
from ibis.expr.operations.core import Column, Scalar, Value  # noqa: TC001
from ibis.expr.operations.relations import Relation, Unaliased
from ibis.expr.schema import Schema


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
    parent: Relation
    time_col: Unaliased[Column]
    bucket_width: Scalar[dt.Interval]
    groups: FrozenOrderedDict[str, Unaliased[Column]]
    metrics: FrozenOrderedDict[str, Unaliased[Value]]
    origin: Optional[Scalar[dt.Timestamp]] = None

    def __init__(self, parent, time_col, bucket_width, groups, metrics, origin=None):
        from ibis.expr.operations.relations import _check_integrity

        items = [time_col, bucket_width, *groups.values(), *metrics.values()]
        if origin is not None:
            items.append(origin)
        _check_integrity(tuple(items), {parent})
        super().__init__(
            parent=parent,
            time_col=time_col,
            bucket_width=bucket_width,
            groups=groups,
            metrics=metrics,
            origin=origin,
        )

    @attribute
    def values(self):
        return FrozenOrderedDict({**self.groups, **self.metrics})

    @attribute
    def schema(self):
        tz = getattr(self.time_col.dtype, "timezone", None)
        field_pairs = {
            "bucket": dt.Timestamp(timezone=tz, nullable=True),
            **{k: v.dtype for k, v in self.groups.items()},
            **{k: v.dtype for k, v in self.metrics.items()},
        }
        return Schema(field_pairs)
