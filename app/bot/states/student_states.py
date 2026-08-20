from aiogram.fsm.state import State, StatesGroup


class TestByCodeState(StatesGroup):
    waiting_for_code = State()
    waiting_for_password = State()


class QuickCheckState(StatesGroup):
    waiting_for_test_code = State()
    waiting_for_answers = State()


class StudentSupportState(StatesGroup):
    waiting_for_message = State()


class StudentCreateTestState(StatesGroup):
    waiting_for_title = State()
    waiting_for_subject = State()
    waiting_for_grade = State()
    waiting_for_time_limit = State()
    # Question addition loop
    waiting_for_question_text = State()
    waiting_for_option_a = State()
    waiting_for_option_b = State()
    waiting_for_option_c = State()
    waiting_for_option_d = State()
    waiting_for_correct_option = State()
    waiting_for_points = State()


class ProfileEditState(StatesGroup):
    waiting_for_name = State()
    waiting_for_school = State()
    waiting_for_phone = State()
