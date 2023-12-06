from __future__ import annotations

from .app_model import AppModel
from .events import (NewUserFormEvent, ReinitializeHandlersEvent,
                     SaveUserFormEvent, UpdateUserFormEvent, UserNotifyEvent)
from typing import cast
from .handlers import *
import zmq


class AppController(BaseController):
    __form_handlers = (
        # Блок вопросов: плодовые факторы риска
        ViewElements(handler=FetalRiskFactorsHandler, view_data=None),
        ViewElements(handler=CongenitalMalformationsHandler, view_data=None),
        ViewElements(handler=AcuteInfectionsHandler, view_data=None),
        ViewElements(handler=NonimmuneHydropsHandler, view_data=None),
        ViewElements(handler=IsoimmunizationHandler, view_data=None),
        ViewElements(handler=MaternalFetalHemorrhageHandler, view_data=None),
        ViewElements(handler=FetoFetalTransfusionSyndromeHandler, view_data=None),
        ViewElements(handler=FetalGrowthRestrictionHandler, view_data=None),
        # Блок вопросов: пуповинные факторы риска
        ViewElements(handler=UmbilicalCordRiskFactorsHandler, view_data=None),
        ViewElements(handler=ProlapseHandler, view_data=None),
        ViewElements(handler=UmbilicalCoilingKnotHandler, view_data=None),
        ViewElements(handler=VelamentousInsertionHandler, view_data=None),
        ViewElements(handler=ShortUmbilicalCordHandler, view_data=None),
        # Блок вопросов: плацентарные факторы риска
        ViewElements(handler=PlacentalRiskFactorsHandler, view_data=None),
        ViewElements(handler=PlacentalAbruptionHandler, view_data=None),
        ViewElements(handler=PlacentalPreviaHandler, view_data=None),
        ViewElements(handler=VascularCordProlapseHandler, view_data=None),
        ViewElements(handler=PlacentalInsufficiencyHandler, view_data=None),
        # Блок вопросов: факторы, связанные с патологией амниотической жидкости
        ViewElements(handler=FactorsAmnioticFluidPathologyHandler, view_data=None),
        ViewElements(handler=ChorioamnionitisHandler, view_data=None),
        ViewElements(handler=OligohydramniosHandler, view_data=None),
        ViewElements(handler=PolyhydramniosHandler, view_data=None),
        # Блок вопросов: материнские факторы риска
        ViewElements(handler=MaternalRiskFactorsHandler, view_data=None),
        ViewElements(handler=AsphyxiaHandler, view_data=None),
        ViewElements(handler=BirthTraumaHandler, view_data=None),
        ViewElements(handler=ExternalInjuryHandler, view_data=None),
        ViewElements(handler=IatrogenicInjuryHandler, view_data=None),
        ViewElements(handler=UterineRuptureHandler, view_data=None),
        ViewElements(handler=UterineMalformationsHandler, view_data=None),
        ViewElements(handler=SubstanceAbuseHandler, view_data=None),
        ViewElements(handler=TobaccoConsumptionHandler, view_data=None),
        ViewElements(handler=AlcoholConsumptionHandler, view_data=None),
        # Блок вопросв: текстовые
        ViewElements(handler=PreTextQuestionsHandler, view_data=None),
        ViewElements(handler=InfectiousAndParasiticHandler, view_data=None),
        ViewElements(handler=BloodAndImmuneSystemHandler, view_data=None),
        ViewElements(handler=EndocrineSystemHandler, view_data=None),
        ViewElements(handler=NervousSystemHandler, view_data=None),
        ViewElements(handler=CirculatorySystemHandler, view_data=None),
        ViewElements(handler=RespiratorySystemHandler, view_data=None),
        ViewElements(handler=DigestiveSystemHandler, view_data=None),
        ViewElements(handler=MusculoskeletalSystemHandler, view_data=None),
        ViewElements(handler=GenitourinarySystemHandler, view_data=None),
        ViewElements(handler=CongenitalAnomaliesHandler,view_data= None),
        ViewElements(handler=ExternalCausesHandler, view_data=None),
        # Концовка
        ViewElements(handler=EndCommentHandler, view_data=None),
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
                ViewElements(handler=PersonalDataAgreeMessageHandler, view_data=None),
                ViewElements(handler=StartMessageHandler, view_data=None),
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
