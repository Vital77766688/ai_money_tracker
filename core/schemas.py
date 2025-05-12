from typing import List, Any, Union, Literal, Optional
from pydantic import BaseModel, RootModel, Field, field_validator
from sqlalchemy.sql import operators


OPERATOR_MAP = {
    '=': operators.eq,
    '==': operators.eq,
    '!=': operators.ne,
    '<>': operators.ne,
    '>': operators.gt,
    '>=': operators.ge,
    '<': operators.lt,
    '<=': operators.le,
    'in': operators.in_op,
    'not in': lambda col, val: ~col.in_(val),
    'like': operators.like_op,
    'not like': lambda col, val: ~col.like(val),
    'ilike': operators.ilike_op,
    'not ilike': lambda col, val: ~col.ilike(val),
    'between': lambda col, val: col.between(val[0], val[1]),
    'is null': lambda col, _: col.is_(None),
    'is not null': lambda col, _: col.is_not(None),
    'true': lambda col, _: col.is_(True),
    'false': lambda col, _: col.is_(False)
}


class SimpleCondition(BaseModel):
    field: str
    op: Literal[
        '=', '==', '!=', '<>', '>', '>=', '<', '<=', 
        'in', 'not in', 'like', 'not like', 'ilike', 'not ilike',
        'between', 'is null', 'is not null', 'true', 'false'
    ]
    value: Optional[Any] = None

    @field_validator("value")
    def validate_value(cls, v, info):
        op = info.data.get("op")
        if op in {"between"} and (not isinstance(v, (list, tuple)) or len(v) != 2):
            raise ValueError("Value for 'between' must be a list of two items.")
        if op in {"is null", "is not null"} and v is not None:
            raise ValueError(f"Operator '{op}' should not have a value.")
        return v


class LogicalFilter(BaseModel):
    and_: Optional[List[Union["LogicalFilter", SimpleCondition]]] = Field(default=None, alias="and")
    or_: Optional[List[Union["LogicalFilter", SimpleCondition]]] = Field(default=None, alias="or")

    model_config = {
        "populate_by_name": True,
        "extra": "forbid"
    }
LogicalFilter.model_rebuild()  # чтобы разрешить рекурсию


class Filter(RootModel[Union[List[SimpleCondition], LogicalFilter]]):
    @property
    def conditions(self) -> LogicalFilter:
        if isinstance(self.root, list):
            return LogicalFilter(and_=self.root)
        return self.root
