from sqlalchemy import select
from . import BaseRepository
from budget.models import User
from budget.schemas import UserCreateSchema, UserSchema


class UserRepository(BaseRepository):
    async def create_user(self, user_data: UserCreateSchema) -> UserSchema:
        async with self.session() as session:
            user = User(**user_data.model_dump())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return UserSchema.model_validate(user, from_attributes=True)
    
    async def get_user(self, username: str) -> UserSchema:
        async with self.session() as session:
            user = await session.execute(
                    select(User.name, User.telegram_id, User.id) \
                    .filter_by(name=username)
                )
            return UserSchema.model_validate(user.one(), from_attributes=True)
        
    async def get_user_by_telegram_id(self, tg_id: int) -> UserSchema:
        async with self.session() as session:
            user = await session.execute(
                select(User.name, User.telegram_id, User.id) \
                .filter_by(telegram_id=tg_id)
            )
            return UserSchema.model_validate(user.one(), from_attributes=True)
