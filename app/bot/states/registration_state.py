from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    confirm_name = State()
    waiting_for_name = State()
    choose_region = State()
    waiting_for_school = State()
    choose_role = State()
    waiting_for_phone = State()
