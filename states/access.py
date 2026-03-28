from aiogram.fsm.state import State, StatesGroup


class AccessStates(StatesGroup):
    waiting_for_access_code = State()


class AdminStates(StatesGroup):
    waiting_for_delete_code = State()
    waiting_for_deactivate_code = State()