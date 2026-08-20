from aiogram.fsm.state import State, StatesGroup


class AdminCreateTestState(StatesGroup):
    waiting_for_title = State()
    waiting_for_code = State()
    waiting_for_file = State()
    waiting_for_answer_key = State()
    waiting_for_time_limit = State()
    waiting_for_schedule = State()


class AdminAddQuestionState(StatesGroup):
    waiting_for_test_id = State()
    waiting_for_question_text = State()
    waiting_for_photo = State()
    waiting_for_option_a = State()
    waiting_for_option_b = State()
    waiting_for_option_c = State()
    waiting_for_option_d = State()
    waiting_for_correct_option = State()
    waiting_for_points = State()
    waiting_for_explanation = State()


class AdminExcelImportState(StatesGroup):
    waiting_for_test_id = State()
    waiting_for_file = State()


class AdminStudentSearchState(StatesGroup):
    waiting_for_query = State()


class AdminBlockUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_reason = State()


class AdminGroupState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_student_id_to_add = State()


class AdminBroadcastState(StatesGroup):
    waiting_for_target_type = State()
    waiting_for_target_id = State()
    waiting_for_message = State()
    waiting_for_confirmation = State()


class AdminSupportResponseState(StatesGroup):
    waiting_for_ticket_id = State()
    waiting_for_response = State()


class AdminChannelState(StatesGroup):
    waiting_for_title = State()
    waiting_for_channel_id = State()
    waiting_for_invite_link = State()


class AdminAddAdminState(StatesGroup):
    waiting_for_telegram_id = State()
    waiting_for_full_name = State()


class AdminScheduleState(StatesGroup):
    waiting_for_test_id = State()
    waiting_for_dates = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()


class AdminSetPasswordState(StatesGroup):
    waiting_for_password = State()
