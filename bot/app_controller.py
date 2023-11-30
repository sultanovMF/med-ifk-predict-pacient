import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot.types import KeyboardButton, Message, ReplyKeyboardMarkup

from .app_model import AppModel
from .event import Event
from .user_model import UserModel


def create_yn_markup(*args):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for arg in args:
        markup.add(KeyboardButton(arg))

    return markup


class AppController:
    def __init__(self, token: str, app_model: AppModel):
        self.__bot = AsyncTeleBot(token, parse_mode=None)
        self.__app_model = app_model
        self.__users = {str: UserModel}

        @self.__bot.message_handler(commands=["start"])
        async def start_command(message: Message):
            self.__users[message.chat.id] = UserModel(current_event=Event.NONE, form={})
            await self.__bot.send_message(
                message.chat.id,
                "Добро пожаловать в программу прогнозирования внутриутробной гибели плода.",
            )
            await self.__bot.send_message(
                message.chat.id, "Для начала работы требуется пройти регистрацию."
            )
            await self.__handle_event(message)

        @self.__bot.message_handler(func=lambda message: True)
        async def receive_message(message: Message):
            await self.__handle_event(message)

    async def __handle_event(self, message: Message):
        match self.__users[message.chat.id].current_event:
            case Event.NONE:  # => Stage.ENTER_NAME
                await self.__bot.send_message(message.chat.id, "Введите ФИО:")
                self.__users[message.chat.id].current_event = Event.ENTERED_NAME

            case Event.ENTERED_NAME:  # => Stage.ENTER_DIAGNOSIS
                # TODO обработать корявый ввод
                self.__users[message.chat.id].form["full_name"] = message.text
                await self.__bot.send_message(
                    message.chat.id, f"Приятно познакомиться, {message.text}"
                )

                await self.__bot.send_message(
                    message.chat.id,
                    "Злоупотребляете алкоголем? *(Да/Нет)",
                    reply_markup=create_yn_markup("Да", "Нет"),
                )
                self.__users[message.chat.id].current_event = Event.ENTERED_BOOL
            case Event.ENTERED_BOOL:
                # надо проверить, что данные пришли с кнопки или было введно Да/Нет
                self.__users[message.chat.id].form["alchoholic"] = message.text
                await self.__bot.send_message(message.chat.id, "Чем болеете?")
                self.__users[message.chat.id].current_event = Event.ENTERED_DIAGNOSIS
            case Event.ENTERED_DIAGNOSIS:  # => Stage.ENTER_DIAGNOSIS
                self.__users[message.chat.id].form["diagnosis"] = message.text
                self.__users[message.chat.id].current_event = Event.END_FORM
                await self.__handle_event(message)
            case Event.END_FORM:
                self.__app_model.add_to_db(user_form=self.__users[message.chat.id].form)
                await self.__bot.send_message(
                    message.chat.id, "Анкета отправлена врачу. Ожидайте результатов!"
                )
                await self.__bot.send_message(
                    message.chat.id,
                    "Чтобы заоплнить анкету еще раз нажмите на кнопку.",
                    reply_markup=create_yn_markup("Начать"),
                )
                self.__users[message.chat.id].current_event = Event.NONE

    def run(self):
        asyncio.run(self.__bot.polling())
