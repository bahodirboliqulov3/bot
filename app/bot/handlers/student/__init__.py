from aiogram import Router
from .main_menu import router as main_menu_router
from .tests_list import router as tests_list_router
from .test_solver import router as test_solver_router
from .quick_check import router as quick_check_router
from .results import router as results_router
from .ratings import router as ratings_router
from .student_test_creator import router as student_test_creator_router
from .saved_tests import router as saved_tests_router
from .achievements import router as achievements_router
from .support import router as support_router
from .guide import router as guide_router

student_router = Router(name="student_root")
student_router.include_routers(
    main_menu_router,
    tests_list_router,
    test_solver_router,
    quick_check_router,
    results_router,
    ratings_router,
    student_test_creator_router,
    saved_tests_router,
    achievements_router,
    support_router,
    guide_router,
)

all = ["student_router"]
