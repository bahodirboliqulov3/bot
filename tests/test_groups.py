import pytest
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_group_management_flow(db_session):
    group_repo = GroupRepository(db_session)
    user_repo = UserRepository(db_session)

    # 1. Create users
    u1 = await user_repo.create(
        telegram_id=111,
        first_name="Sanjar",
        last_name="Aliyev",
        phone_number="+998901111111",
        school="Maktab 1",
        grade="9-A"
    )
    u2 = await user_repo.create(
        telegram_id=222,
        first_name="Madina",
        last_name="Karimova",
        phone_number="+998902222222",
        school="Maktab 1",
        grade="9-A"
    )

    # 2. Create Group
    group = await group_repo.create(name="9-A Sinf", created_by=999)
    assert group.id is not None

    # 3. Add members
    await group_repo.add_member(group.id, u1.id)
    await group_repo.add_member(group.id, u2.id)

    members = await group_repo.get_group_members(group.id)
    assert len(members) == 2
    assert await group_repo.is_member(group.id, u1.id) is True

    # 4. Remove member
    removed = await group_repo.remove_member(group.id, u1.id)
    assert removed is True
    assert await group_repo.is_member(group.id, u1.id) is False

    members_after = await group_repo.get_group_members(group.id)
    assert len(members_after) == 1
