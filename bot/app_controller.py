from __future__ import annotations

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections import namedtuple
from typing import cast

import zmq
from telebot.async_telebot import AsyncTeleBot
from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)

from mvc import BaseController, Event, EventBus

from .app_model import AppModel
from .events import (NewUserFormEvent, ReinitializeHandlersEvent,
                     SaveUserFormEvent, UpdateUserFormEvent, UserNotifyEvent)

ViewElements = namedtuple("ViewElements", "handler view_data")
UserData = namedtuple("UserData", "chat_id field value")
HandlerData = namedtuple("HandlerData", "current_handler current_view_data chat_id")


def create_markup(*args):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for arg in args:
        markup.add(KeyboardButton(arg))

    return markup


class Handler(ABC):
    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        pass

    @abstractmethod
    async def handle(self, chat_id: int):
        pass


class AbstractHandler(Handler):
    _next_handler: Handler = None

    def __init__(self, event_bus: EventBus, bot: AsyncTeleBot, *args, **kwargs):
        self._event_bus = event_bus
        self._bot = bot

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler

    @abstractmethod
    async def handle(self, chat_id: int):
        pass

    def __call__(self, *args, **kwargs):
        return self


class AbstractInfoHandler(AbstractHandler, ABC):
    pass


class AbstractRequestHandler(AbstractHandler, ABC):
    def __init__(self, event_bus: EventBus, *args, **kwargs):
        super().__init__(event_bus, *args, **kwargs)
        self._commit = asyncio.Event()
        self._data = None

    @abstractmethod
    async def process_response(self, data: str):
        # метод для валидации данных
        self._data = data
        self._commit.set()


class AbstractRequestTextHandler(AbstractRequestHandler, ABC):
    pass


class AbstractRequestButtonHandler(AbstractRequestHandler, ABC):
    pass


class WelcomeMessangeHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "Добро пожаловать!")
        await self._bot.send_photo(
            chat_id=chat_id, photo="https://telegram.org/img/t_logo.png"
        )

        self._event_bus.publish(NewUserFormEvent(chat_id))

        return self._next_handler


class AlcoholicFormHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Вы злоупотребялете алкоголем?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о злоупотреблении алкоголем вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_alcoholic",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class DiagnosisFormHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Чем болеете?",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="diagnosis", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class EndFormActionHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Нажмите на кнопку, чтобы начать заново.",
            reply_markup=create_markup("Начать"),
        )

        self._event_bus.publish(SaveUserFormEvent(chat_id))

        await self._commit.wait()

        self._event_bus.publish(
            ReinitializeHandlersEvent(
                HandlerData(
                    current_handler=self, current_view_data=None, chat_id=chat_id
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        if data == "Начать":
            self._data = data
            self._commit.set()


class AppController(BaseController):
    __form_handlers = (
        ViewElements(handler=WelcomeMessangeHandler, view_data=None),
        ViewElements(handler=AlcoholicFormHandler, view_data=None),
        ViewElements(handler=DiagnosisFormHandler, view_data=None),
        ViewElements(handler=EndFormActionHandler, view_data=None),
    )

    def __init__(self, token: str, app_model: AppModel, event_bus: EventBus):
        super().__init__()
        self.__event_bus = event_bus
        self.__event_bus.subscribe(self)

        self.__bot = AsyncTeleBot(token, parse_mode=None)

        self.__app_model = app_model

        self.__zmq_context = zmq.Context()
        self.__zmq_socket = self.__zmq_context.socket(zmq.REP)
        self.__zmq_socket.bind("tcp://*:5555")
        threading.Thread(target=self.__zmq_listening, daemon=True).start()

        self._event_handlers[cast(Event, UserNotifyEvent)] = self.__notify_event
        self._event_handlers[cast(Event, UpdateUserFormEvent)] = self.__update_user_form
        self._event_handlers[
            cast(Event, ReinitializeHandlersEvent)
        ] = self.__reinitialize_handler
        self._event_handlers[cast(Event, SaveUserFormEvent)] = self.__save_user_form
        self._event_handlers[cast(Event, NewUserFormEvent)] = self.__new_user_form

        self.__user_handler = {}
        self.__user_forms = {}

        async def handle_events(chat_id):
            while self.__user_handler[chat_id]:
                self.__user_handler[chat_id] = await self.__user_handler[
                    chat_id
                ].handle(chat_id)

        @self.__bot.message_handler(commands=["start"])
        async def start_command(message: Message):
            self.__user_handler[message.chat.id] = self.__add_start_handlers(
                *self.__form_handlers
            )

            await handle_events(message.chat.id)

        @self.__bot.message_handler(func=lambda message: True)
        async def receive_message(message: Message):
            if isinstance(
                self.__user_handler[message.chat.id], AbstractRequestTextHandler
            ):
                await self.__user_handler[message.chat.id].process_response(
                    message.text
                )

        @self.__bot.callback_query_handler(func=lambda call: True)
        async def button_processing(call: CallbackQuery):
            if isinstance(
                self.__user_handler[call.message.chat.id], AbstractRequestButtonHandler
            ):
                await self.__user_handler[call.message.chat.id].process_response(
                    call.data
                )

    def __new_user_form(self, e: Event):
        chat_id = e.data
        self.__user_forms[chat_id] = {"chat_id": chat_id}

    def __save_user_form(self, e: Event):
        chat_id = e.data
        self.__app_model.add_to_db(self.__user_forms[chat_id])

    def __reinitialize_handler(self, e: Event):
        current_handler, current_view_data, chat_id = e.data
        self.__user_handler[chat_id] = self.__add_start_handlers(
            ViewElements(handler=current_handler, view_data=current_view_data),
            *self.__form_handlers,
        )

    def __add_start_handlers(self, *args):
        result_handler = args[0].handler(
            self.__event_bus, self.__bot, args[0].view_data
        )
        if len(args) > 1:
            result_handler.set_next(self.__add_start_handlers(*args[1:]))

        return result_handler

    def __notify_event(self, e: Event):
        pass

    def __zmq_listening(self):
        while True:
            message = self.__zmq_socket.recv()
            print("Received request: %s" % message)

            time.sleep(10)

            self.__zmq_socket.send(b"World")

    def __update_user_form(self, e: Event):
        chat_id, field, value = e.data
        self.__user_forms[chat_id][field] = value

    def run(self):
        asyncio.run(self.__bot.polling())
