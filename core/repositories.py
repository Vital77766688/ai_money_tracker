from typing import Dict, Set, Tuple, Any, Union, Callable, TypeVar, Generic
from pydantic import BaseModel
from sqlalchemy import select, and_, or_, inspect
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound, IntegrityError
from core.database import Base
from core.exceptions import InstanceNotFound, ConstraintsViolation, FilterFieldNotAllowed, FilterOperationNotAllowed
from core.schemas import OPERATOR_MAP, Filter


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
OperatorFunc = Callable[[Any, Any], BinaryExpression]


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    In case selected fields differ from model field, you can override list/get methods in subclasses
    Use self._select method to execute selectables
    """
    model: ModelType = None
    allowed_fields: dict[str, Tuple[Any, Union[str, None]]] = None
    allowed_ops: dict[str, OperatorFunc] = OPERATOR_MAP

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _select(self, stmt: Select):
        return await self.session.execute(stmt)
    
    async def _flush(self) -> None:
        try:
            await self.session.flush()
        except IntegrityError:
            raise ConstraintsViolation 

    def _build_filter(self, filter_def: Filter) -> Tuple[BinaryExpression, set[str]]:
        joins: set[str] = set()

        def _parse_condition(cond: dict) -> BinaryExpression:
            if "and_" in cond:
                return and_(*[_parse_condition(c) for c in cond["and_"]])
            elif "or_" in cond:
                return or_(*[_parse_condition(c) for c in cond["or_"]])
            else:
                field_name = cond["field"]
                op = cond["op"].lower()
                value = cond.get("value")

                if field_name not in self.allowed_fields:
                    raise FilterFieldNotAllowed(f"Field '{field_name}' is not allowed.")
                if op not in self.allowed_ops:
                    raise FilterOperationNotAllowed(f"Operator '{op}' is not allowed.")

                column, join_key = self.allowed_fields[field_name]
                if join_key:
                    joins.add(join_key)
                return self.allowed_ops[op](column, value)

        filter_ = filter_def.model_dump()
        if isinstance(filter_, list):
            expr = and_(*[_parse_condition(f) for f in filter_])
        else:
            expr = _parse_condition(filter_)
        return expr, joins

    def _apply_joins(self, stmt, joins: Set[str], preload_related: bool):
        relationships = self._get_relationships()
        for join_key in joins:
            if join_key in relationships:
                if preload_related:
                    # Используем только joinedload без явного JOIN
                    stmt = stmt.options(joinedload(relationships[join_key]))
                else:
                    # Только явный JOIN без дублирования
                    stmt = stmt.join(relationships[join_key])
        return stmt

    def _get_relationships(self) -> Dict[str, Any]:
        """Получает все отношения модели в формате {имя: атрибут}"""
        mapper = inspect(self.model)
        return {
            rel.key: getattr(self.model, rel.key)  # Используем сам атрибут модели
            for rel in mapper.relationships
        }

    async def get(self, id: int, filters: Filter=None) -> ModelType:
        stmt = select(self.model).where(self.model.id==id)
        if filters:
            where_clause, joins = self._build_filter(filters)
            stmt = self._apply_joins(stmt, joins, False)
            stmt = stmt.where(where_clause)
        result = await self._select(stmt)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise InstanceNotFound

    async def list(self, limit: int=10, offset: int=0, filters: Filter=None) -> ModelType:
        stmt = select(self.model) \
            .order_by(self.model.id.desc()) \
            .limit(limit) \
            .offset(offset)
        if filters:
            where_clause, joins = self._build_filter(filters)
            stmt = self._apply_joins(stmt, joins, False)
            stmt = stmt.where(where_clause)
        results = await self._select(stmt)
        return results.scalars().all()

    async def create(self, item_data: CreateSchemaType) -> ModelType:
        instance = self.model(**item_data.model_dump(exclude_none=True))
        self.session.add(instance)
        await self._flush()
        return instance

    async def update(self, id: int, item_data: UpdateSchemaType, filters: Filter=None) -> ModelType:
        instance = await self.get(id=id, filters=filters)
        for attr, value in item_data.model_dump(exclude_none=True).items():
            setattr(instance, attr, value)
        self.session.add(instance)
        await self._flush()
        return instance

    async def delete(self, id: int, filters: Filter=None) -> None:
        instance = await self.get(id=id, filters=filters)
        await self.session.delete(instance)
