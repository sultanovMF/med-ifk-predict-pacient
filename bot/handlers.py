from __future__ import annotations

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections import namedtuple
from telebot.async_telebot import AsyncTeleBot
from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)
from .events import (NewUserFormEvent, ReinitializeHandlersEvent,
                     SaveUserFormEvent, UpdateUserFormEvent, UserNotifyEvent)

from mvc import BaseController, Event, EventBus

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


class PersonalDataAgreeMessageHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton("Согласен 🟢", callback_data="согласен"),
        )

        await self._bot.send_message(chat_id, """
        Приветствуем вас в нашем боте прогнозирования внутриутробной гибели плода. Мы понимаем, что это чувствительная тема, и мы здесь, чтобы предоставить вам информацию и поддержку.

Наш бот основан на современных методах анализа данных и медицинских исследованиях. Мы стремимся предоставить вам точные и надежные прогнозы, которые могут помочь вам принимать информированные решения относительно вашего здоровья и беременности.

Пожалуйста, помните, что результаты, предоставленные ботом, не заменяют консультацию с квалифицированным врачом. Если у вас есть какие-либо вопросы или беспокойства, рекомендуем обсудить их с вашим врачом.

*Для начала использования бота и получения прогнозов, вы должны согласиться на обработку персональных данных. Нажмите кнопку "Согласен".* """, parse_mode='Markdown', reply_markup=markup)

        await self._commit.wait()

        self._event_bus.publish(NewUserFormEvent(chat_id))

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class StartMessageHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton("Начать 🚀", callback_data="начать"),
        )

        await self._bot.send_message(chat_id, """
Вы согласились на обработку персональных данных!

*Для начала использования бота и получения прогнозов, пожалуйста, нажмите кнопку "Начать".* """, parse_mode='Markdown', reply_markup=markup)

        await self._commit.wait()

        self._event_bus.publish(NewUserFormEvent(chat_id))

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class FetalRiskFactorsHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "*🔎 Блок вопросов: плодовые факторы риска.*", parse_mode='Markdown')

        return self._next_handler


class CongenitalMalformationsHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдались ли врожденные пороки развития?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о врожденых пороках развития вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_congenital_mal_formations",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class AcuteInfectionsHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдались ли инфекции острые?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос об острых инфекциях вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_acute_infections",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class NonimmuneHydropsHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюбдалась ли неиммунная водянка?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о неимунной водянке вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_nonimmune_hydrops",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class IsoimmunizationHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли изоиммунизация?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос об изомунизации вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_isoimmunization",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class MaternalFetalHemorrhageHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли плодово-материнское кровотечение?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о плодово-материнское кровотечении вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_maternal_fetal_hemorrhage",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class FetoFetalTransfusionSyndromeHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдался ли фето-фетальный трансфузионный синдром?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о фето-фетальный трансфузионный синдроме вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_feto_fetal_transfusion_syndrome",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class FetalGrowthRestrictionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли задержка роста плода?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о задержке роста плода вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_fetal_growth_restriction",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class UmbilicalCordRiskFactorsHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "* 🔎 Блок вопросов: пуповинные факторы риска.*", parse_mode='Markdown')

        return self._next_handler


class ProlapseHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалось ли выпадение пуповины?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о выпадении пуповины вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_prolapse",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class UmbilicalCoilingKnotHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалось ли обвитие/узел пуповины?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о обвитии/узла пуповины вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_umbilical_coiling_knot",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class VelamentousInsertionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалось ли оболочечное прикрепление пуповины?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о оболочечном прикреплении пуповины вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_velamentous_insertion",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class ShortUmbilicalCordHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдается ли короткая пуповина?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о короткой пуповине вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_short_umbilical_cord",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class PlacentalRiskFactorsHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "* 🔎 Блок вопросов: плацентарные факторы риска.*", parse_mode='Markdown')

        return self._next_handler



class PlacentalAbruptionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли отслойка плаценты?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос об отслойке плаценты вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_placental_abruption",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class PlacentalPreviaHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли предлежание плаценты?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о предлежании плаценты вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_placental_previa",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class VascularCordProlapseHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли предлежание сосудов пуповины?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос об  предлежании сосудов пуповины вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_vascular_cord_prolapse",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class PlacentalInsufficiencyHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли плацентарная недостаточность?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о плацентарной недостаточности вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_placental_insufficiency",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class FactorsAmnioticFluidPathologyHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "* 🔎 Блок вопросов: факторы, связанные с патологией амниотической жидкости *", parse_mode='Markdown')

        return self._next_handler



class ChorioamnionitisHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдался ли хориоамнионит?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о хориоамнионите вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_chorioamnionitis",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class OligohydramniosHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдался ли олигоамнион (маловодие)?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о олигоамнионе (маловодии) вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_oligohydramnios",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class PolyhydramniosHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдался ли полигидрамнион (многоводие)?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о полигидрамнионе (многоводии) вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_polyhydramnios",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class MaternalRiskFactorsHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, "* 🔎 Блок вопросов: материнские факторы риска *", parse_mode='Markdown')

        return self._next_handler


class AsphyxiaHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли интранатальная (во время родов) асфиксия?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о интранатальной асфиксии вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_asphyxia",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class BirthTraumaHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли интранатальная (во время родов) родовая травма?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о интранатальной родовой травме вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_birth_trauma",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class ExternalInjuryHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли внешняя травма?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о внешней травме вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_external_injury",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class IatrogenicInjuryHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдалась ли ятрогенная травма?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о ятрогенной травме вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_iatrogenic_injury",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class UterineRuptureHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдался ли разрыв матки?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о разрыве матки вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_uterine_rupture",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class UterineMalformationsHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Наблюдались ли немодифицируемые пороки развития/строения матки?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о немодифицируемых пороках развития/строения матки вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_uterine_malformations",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class SubstanceAbuseHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Употребляете/употребляли ли вы наркотические средства?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос об употреблении наркотических средств вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_substance_abuse",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class TobaccoConsumptionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Употребляете/употребляли табак?",
            reply_markup=markup,
        )

        await self._commit.wait()

        await self._bot.edit_message_text(
            text=f"На вопрос о потреблении табака вы ответили: {self._data}",
            chat_id=chat_id,
            message_id=sent_message.message_id,
        )

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(
                    chat_id=chat_id,
                    field="is_tobacco_consumption",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class AlcoholConsumptionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("Да", callback_data="да"),
            InlineKeyboardButton("Нет", callback_data="нет"),
        )

        sent_message = await self._bot.send_message(
            chat_id,
            "Злоупотребляете ли вы алкоголем?",
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
                    field="is_alcohol_consumption",
                    value=True if self._data == "да" else False,
                )
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class PreTextQuestionsHandler(AbstractInfoHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(chat_id, """* Далее последуют вопросы, на которые требуется ответить развернуто. Пишите всё, что считаете необходимым.  
        
Если вам нечего ответить поставьте прочерк.
        *""", parse_mode='Markdown')

        return self._next_handler

class InfectiousAndParasiticHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите инфекционные и паразитарные болезни: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="infectious_and_parasitic", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class BloodAndImmuneSystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни крови, кроветворных органов и отдельные нарушения, вовлекающие иммунный механизм: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="blood_and_immune_system", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()



class EndocrineSystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни эндокринной системы, расстройства питания и нарушения обмена веществ: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="endocrine_system", value=self._data)
            )
        )

        return self._next_handler
    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class NervousSystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни нервной системы: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="nervous_system", value=self._data)
            )
        )

        return self._next_handler
    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class CirculatorySystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни системы кровообращения: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="circulatory_system", value=self._data)
            )
        )

        return self._next_handler
    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class RespiratorySystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни органов дыхания: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="respiratory_system", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class DigestiveSystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни органов пищеварения: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="digestive_system", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class MusculoskeletalSystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни костно-мышечной системы и соединительной ткани: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="musculoskeletal_system", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class GenitourinarySystemHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите болезни мочеполовой системы: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="genitourinary_system", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class CongenitalAnomaliesHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите врожденные аномалии, деформации и хромосомные нарушения: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="congenital_anomalies", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class ExternalCausesHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Перечислите травмы, отравления и некоторые другие последствия воздействия внешних причин: ",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="external_causes", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()


class EndCommentHandler(AbstractRequestTextHandler):
    async def handle(self, chat_id: int):
        await self._bot.send_message(
            chat_id,
            "Если у вас остались вопросы/комментарии задайте их:",
        )

        await self._commit.wait()

        self._event_bus.publish(
            UpdateUserFormEvent(
                UserData(chat_id=chat_id, field="comment", value=self._data)
            )
        )

        return self._next_handler

    async def process_response(self, data: str):
        self._data = data
        self._commit.set()

class EndFormActionHandler(AbstractRequestButtonHandler):
    async def handle(self, chat_id: int):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton("Начать 🚀", callback_data="начать"),
        )

        await self._bot.send_message(chat_id, """
Благодарим вас за предоставленные данные. 🌟 Ваши ответы были успешно отправлены врачу для дополнительной проверки. Пожалуйста, дождитесь окончательного результата, который будет доступен в ближайшее время.

Мы готовы продолжить поддерживать вас на каждом этапе вашего пути к здоровой беременности. В случае дополнительных вопросов не забывайте обращаться к вашему врачу для профессиональной консультации.

Чтобы начать новую консультацию или обновить текущие данные, нажмите кнопку "Начать" """, parse_mode='Markdown', reply_markup=markup)

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
        self._data = data
        self._commit.set()