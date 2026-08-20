import pytest
from app.config import settings
from app.services.auth_service import AuthService
from app.database.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_user_registration_and_lookup(db_session):
    auth_service = AuthService(db_session)

    # 1. Register student
    user = await auth_service.get_or_create_user(
        telegram_id=999888111,
        first_name="Ali",
        last_name="Valiyev",
        username="alivaliyev",
        phone_number="+998901234567",
        school="Prezident Maktabi",
        grade="10-A"
    )

    assert user.id is not None
    assert user.full_name == "Ali Valiyev"
    assert user.grade == "10-A"

    # 2. Check registration status
    is_reg = await auth_service.is_user_registered(999888111)
    assert is_reg is True

    is_not_reg = await auth_service.is_user_registered(111222333)
    assert is_not_reg is False


@pytest.mark.asyncio
async def test_admin_authorization(db_session):
    auth_service = AuthService(db_session)

    # Owner is always admin
    is_owner_admin = await auth_service.is_admin(settings.OWNER_ID)
    assert is_owner_admin is True

    # Random user is not admin
    assert await auth_service.is_admin(555444333) is False

    # Add admin
    admin = await auth_service.add_admin(
        telegram_id=555444333,
        full_name="O'qituvchi Hasan",
        added_by=settings.OWNER_ID
    )
    assert admin.telegram_id == 555444333
    assert await auth_service.is_admin(555444333) is True

    # Remove admin
    removed = await auth_service.remove_admin(555444333)
    assert removed is True
    assert await auth_service.is_admin(555444333) is False

    # Protection: Cannot remove OWNER_ID
    with pytest.raises(ValueError):
        await auth_service.remove_admin(settings.OWNER_ID)


@pytest.mark.asyncio
async def test_user_block_and_unblock(db_session):
    auth_service = AuthService(db_session)
    user_repo = UserRepository(db_session)

    user = await auth_service.get_or_create_user(
        telegram_id=123123123,
        first_name="Spam",
        last_name="User",
        username="spammer",
        phone_number="+998900000000",
        school="N/A",
        grade="N/A"
    )

    assert await auth_service.is_user_blocked(user.telegram_id) is False

    # Block user
    await user_repo.set_blocked(user.id, is_blocked=True, blocked_by=settings.OWNER_ID, reason="Spam")
    assert await auth_service.is_user_blocked(user.telegram_id) is True

    # Unblock user
    await user_repo.set_blocked(user.id, is_blocked=False, blocked_by=settings.OWNER_ID)
    assert await auth_service.is_user_blocked(user.telegram_id) is False
