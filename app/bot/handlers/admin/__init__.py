from aiogram import Router
from .admin_menu import router as admin_menu_router
from .tests_manage import router as tests_manage_router
from .test_creator import router as test_creator_router
from .excel_handler import router as excel_handler_router
from .students_manage import router as students_manage_router
from .groups_manage import router as groups_manage_router
from .broadcast_handler import router as broadcast_handler_router
from .support_manage import router as support_manage_router
from .channels_manage import router as channels_manage_router
from .admins_manage import router as admins_manage_router
from .statistics import router as statistics_router
from .settings_manage import router as settings_manage_router

admin_router = Router(name="admin_root")
admin_router.include_routers(
    admin_menu_router,
    tests_manage_router,
    test_creator_router,
    excel_handler_router,
    students_manage_router,
    groups_manage_router,
    broadcast_handler_router,
    support_manage_router,
    channels_manage_router,
    admins_manage_router,
    statistics_router,
    settings_manage_router,
)

all = ["admin_router"]
