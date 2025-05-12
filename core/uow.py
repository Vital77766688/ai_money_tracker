from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from core.repositories import BaseRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession, repositories: Dict[str, BaseRepository] = None) -> None:
        self.session_factory = session
        self.repositories = repositories or {}

    def add_repository(self, label: str, repository: BaseRepository) -> None:
        self.repositories[label] = repository

    async def __aenter__(self):
        async with self.session_factory() as session:
            self.session = session
            for label, repository in self.repositories.items():
                setattr(self, label, repository(session))
            return self
        
    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, instance) -> None:
        await self.session.refresh(instance)

    async def flush(self) -> None:
        await self.session.flush()
