from aiogram import Router
from .common import router as common_router
from .start import router as start_router
from .student import student_router
from .admin import admin_router

main_router = Router(name="main_root")
main_router.include_routers(
    common_router,
    start_router,
    admin_router,
    student_router
)

all = ["main_router"]
