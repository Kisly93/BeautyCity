import datetime

from django.core.management.base import BaseCommand
from beautycity import settings
from ...models import Master, Service, MasterSchedule, Shift, ClientOffer, Client, Feedback
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ParseMode,
    LabeledPrice
)
from telegram.ext import (
    Updater,
    Filters,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
)
from phonenumbers import is_valid_number, parse


class Command(BaseCommand):
    help = 'Телеграм-бот'

    def handle(self, *args, **kwargs):
        # tg_token = settings.TOKEN
        tg_token = settings.tg_token
        updater = Updater(token=tg_token, use_context=True)
        dispatcher = updater.dispatcher

        def start_conversation(update, context):
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("Записаться", callback_data='to_make_reservation'),
                    InlineKeyboardButton("Мои записи", callback_data="to_show_orders"),
                    InlineKeyboardButton("О нас", callback_data="to_common_info"),
                ],
                [
                    InlineKeyboardButton("Позвонить нам", callback_data='to_contacts'),
                ],
                [
                    InlineKeyboardButton("Оставить отзыв о мастере", callback_data='to_choose_master_for_feedback'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if 'invoice_sended' in context.user_data:
                chat_id = update.effective_message.chat_id
                context.bot.send_message(
                    chat_id,
                    text=f"Описание компании", reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                return 'GREETINGS'

            if query:
                query.answer()
                query.edit_message_text(
                    text=f"Описание компании", reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                update.message.reply_text(
                    text=f"Описание компании", reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            return 'GREETINGS'

        def leave_feedback(update, context):
            query = update.callback_query
            clientoffer_id = query.data.split('_')[1]
            context.user_data['client_offer'] = ClientOffer.objects.get(pk=clientoffer_id)
            query.answer()
            query.edit_message_text("Напишите свой отзыв: ")
            return 'GET_FEEDBACK'

        def get_feedback(update, context):
            query = update.callback_query
            update.message.reply_text("Спасибо за ваш отзыв!")
            nickname = update.message.from_user.username
            client_offer = context.user_data['client_offer']

            Feedback.objects.create(
                text=update.message.text,
                date=datetime.date.today(),
                client=Client.objects.get(nickname=nickname),
                master=client_offer.master_schedule.master
            )

            start_conversation(update, context)
            return 'GREETINGS'

        def make_reservation(update, _):
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("Выбор Мастера", callback_data="to_choose_master"),
                    InlineKeyboardButton("Выбор Услуги", callback_data="to_choose_service"),
                ],
                [
                    InlineKeyboardButton("Позвонить нам", callback_data='to_contacts'),
                    InlineKeyboardButton("На главную", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(
                text="Как вы хотите записаться", reply_markup=reply_markup
            )
            return 'MAKE_RESERVATION'

        def call_salon(update, _):
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("На главную", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(
                text="Рады звонку в любое время.\n Телефон:8 800 555 35 35", reply_markup=reply_markup
            )
            return 'CALL_SALON'

        def show_masters(update, context):
            query = update.callback_query

            if 'to_choose_master_for_feedback' == query.data:
                nickname = query.message.chat['username']
                client_offers = ClientOffer.objects.filter(client__in=Client.objects.filter(nickname=nickname))
                keyboard = []
                for client_offer in client_offers:
                    keyboard.append([
                        InlineKeyboardButton(f'Мастер {client_offer.master_schedule.master}.Запись на {client_offer.shift.start_time} \n', callback_data=f"masterschedule_{client_offer.master_schedule.pk}")
                    ])
                keyboard.append([InlineKeyboardButton("На главную", callback_data="to_start")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.answer()
                query.edit_message_text(
                    text="Выберите Мастера", reply_markup=reply_markup
                )
                return 'GET_FEEDBACK'




            shift_id = query.data.split('_')[1]
            context.user_data['shift'] = Shift.objects.get(pk=shift_id)

            masters = Master.objects.all()
            keyboard = []
            for master in masters:
                keyboard.append([
                    InlineKeyboardButton(master.name, callback_data=f"master_{master.pk}")
                ])
            keyboard.append([InlineKeyboardButton("На главную", callback_data="to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(
                text="Выберите Мастера", reply_markup=reply_markup
            )
            return 'SHOW_MASTERS'


        def show_service_time(update, _):
            query = update.callback_query
            services = Service.objects.all()
            keyboard = []
            for service in services:
                keyboard.append([InlineKeyboardButton(service.name, callback_data=f"service_{service.pk}")])
            keyboard.append([InlineKeyboardButton("Цены на услуги", callback_data="service_prices")])
            keyboard.append([InlineKeyboardButton("На главную", callback_data="to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(text="Выберите услугу", reply_markup=reply_markup)
            return 'SHOW_SERVICE_TIME'

        def show_service_procedure(update, _):
            query = update.callback_query
            services = Service.objects.all()
            keyboard = []
            for service in services:
                keyboard.append([InlineKeyboardButton(service.name, callback_data=f"service_{service.pk}")])
            keyboard.append([InlineKeyboardButton("!!Цены на услуги", callback_data="service_prices")])
            keyboard.append([InlineKeyboardButton("На главную", callback_data="to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(text="Выберите услугу", reply_markup=reply_markup)
            return 'SHOW_SERVICE_PROCEDURE'

        def show_prices(update, _):
            query = update.callback_query
            keyboard = [
                [InlineKeyboardButton("Назад", callback_data="back_to_service")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            services = Service.objects.all()
            text = 'Наши услуги \n'
            for service in services:
                text +=f'- {str(service)}\n'
            query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )
            return 'SHOW_PRICES'

        def select_time(update, context):
            query = update.callback_query
            service_id = query.data.split('_')[1]
            context.user_data['service'] = Service.objects.get(pk=service_id)

            master_scdeule_id = 1
            # Выбор id из контекста и 2 return должно быть в зависимости от context, фильтр должен быть по дате, выбор даты должен быть на предыдущем шаге.

            client_offers = ClientOffer.objects.filter(master_schedule__id=master_scdeule_id)
            shifts = Shift.objects.exclude(pk__in=client_offers.values_list('shift'))
            keyboard = []
            for shift in shifts:
                keyboard.append(
                    [
                        InlineKeyboardButton(f'{shift.start_time} -- {shift.end_time}', callback_data=f"shift_{shift.pk}"),
                    ]
                )
            keyboard.append([InlineKeyboardButton("Позвонить нам", callback_data='to_contacts')])
            keyboard.append([InlineKeyboardButton("На главную", callback_data="to_start")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(
                text="Выберите время", reply_markup=reply_markup
            )
            return 'SELECT_TIME'

        def make_record(update, context):
            query = update.callback_query
            service_id = query.data.split('_')[1]
            context.user_data['master_id'] = service_id
            query.answer()
            query.edit_message_text("Введите ваше имя:")
            return 'GET_NAME'

        def get_name(update, context):
            name = update.message.text.strip()
            context.user_data['name'] = name
            if name:
                update.message.reply_text("Введите ваш номер телефона:")
                return 'GET_PHONE'
            else:
                update.message.reply_text("Пожалуйста, введите ваше имя.")
                return 'GET_NAME'

        def get_phone(update, context):
            phone_number = update.message.text
            parsed_number = parse(phone_number, 'RU')

            if is_valid_number(parsed_number):
                #start_time = Shift.objects.get(pk=context.user_data['shift_id']).start_time
                start_time = context.user_data['shift'].start_time
                context.user_data['phone_number'] = phone_number
                keyboard = [
                    [InlineKeyboardButton("Оплатить услугу сразу", callback_data="to_pay_now")],
                    [InlineKeyboardButton("На главную", callback_data="to_start")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(
                    text=f"Спасибо за запись! До встречи ДД.ММ {str(start_time)} по адресу: ул. улица д. дом",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                print('\ncontext', context.user_data)
                print(update)
                client, created = Client.objects.get_or_create(
                    nickname=update.message.from_user.username,
                    name=context.user_data['name'],
                    phone=phone_number
                )
                print('\n Client: \n',client, f'\n{created }')
                client_offer = ClientOffer.objects.create(
                    client=client,
                    service=context.user_data['service'],
                    master_schedule=MasterSchedule.objects.get(pk=1),
                    shift = context.user_data['shift']
                )
                print(client_offer)
                return 'WAITING_FOR_CONFIRMATION'
            else:
                update.message.reply_text("Пожалуйста, введите корректный номер телефона.")
                return 'GET_PHONE'


        def send_invoice(update, context):
            query = update.callback_query
            service = context.user_data['service']
            token = settings.payments_token
            chat_id = update.effective_message.chat_id
            context.user_data['invoice_sended'] = True
            keyboard = [
                [InlineKeyboardButton('Оплатить', pay=True)],
                [InlineKeyboardButton('На главную', callback_data='to_start')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_invoice(
                chat_id,
                'Оплата услуг',
                service.name,
                payload='payload',
                provider_token=token,
                currency='RUB',
                need_phone_number=False,
                need_email=False,
                is_flexible=False,
                prices=[
                    LabeledPrice(label=service.name, amount=int(f'{service.price}00'))
                ],
                start_parameter='start_parameter',
                reply_markup=reply_markup,
            )
            query.answer()
            return 'SHOW_ANSWER'



        def show_common_info(update, context):
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("Позвонить нам", callback_data='to_contacts'),
                    InlineKeyboardButton("На главную", callback_data="to_start"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            query.edit_message_text(
                text="Информация о салоне, что делаем и т.д", reply_markup=reply_markup
            )
            return 'COMMON_INFO'

        def show_orders(update, context):
            query = update.callback_query
            nickname = query.message.chat['username']
            keyboard = [
                [
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            text = 'Последнине записи: \n'
            client_offers=ClientOffer.objects.filter(client__in=Client.objects.filter(nickname=nickname))
            for client_offer in client_offers:
                text += f'Вы записаны на {client_offer.master_schedule.date}' \
                        f' Ваш мастер {client_offer.master_schedule.master}.' \
                        f' Запись на {client_offer.shift.start_time} \n'
            query.edit_message_text(
                text=text, reply_markup=reply_markup
            )
            return 'SHOW_ANSWER'

        def cancel(update, _):
            user = update.message.from_user
            update.message.reply_text(
                'До новых встреч',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END


        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_conversation)],
            states={
                'GREETINGS': [
                    CallbackQueryHandler(make_reservation, pattern='to_make_reservation'),
                    CallbackQueryHandler(show_orders, pattern='to_show_orders'),
                    CallbackQueryHandler(show_common_info, pattern='to_common_info'),
                    CallbackQueryHandler(call_salon, pattern='to_contacts'),
                    CallbackQueryHandler(show_masters, pattern='to_choose_master*'),
                ],
                'GET_FEEDBACK': [
                    CallbackQueryHandler(leave_feedback, pattern='masterschedule_*'),
                    MessageHandler(Filters.text, get_feedback),
                ],
                'MAKE_RESERVATION': [
                    CallbackQueryHandler(show_service_time, pattern='to_choose_service'),
                    CallbackQueryHandler(show_masters, pattern='to_choose_master'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(call_salon, pattern='to_contacts'),
                ],
                'CALL_SALON': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'SHOW_SERVICE_TIME': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(select_time, pattern=r'service_\d+$'),
                    CallbackQueryHandler(show_prices, pattern='service_prices'),
                ],
                'SHOW_SERVICE_PROCEDURE': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(select_time, pattern=r'service_\d+$'),
                    CallbackQueryHandler(show_prices, pattern='service_prices'),
                ],
                'SHOW_PRICES': [
                    CallbackQueryHandler(show_service_time, pattern='back_to_service')
                ],
                'SHOW_MASTERS': [
                    CallbackQueryHandler(make_record, pattern=r'^master_\d+$'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'SHOW_MASTERS_PROCEDURE': [
                    CallbackQueryHandler(show_service_procedure, pattern=r'master_\d+$'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'SELECT_TIME': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(call_salon, pattern='to_contacts'),
                    CallbackQueryHandler(show_masters, pattern='shift_*'),
                ],
                'GET_PHONE': [
                    CallbackQueryHandler(send_invoice, pattern='to_pay_now'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'COMMON_INFO': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(call_salon, pattern='to_contacts'),
                ],
                'SHOW_ANSWER': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_NAME': [
                    MessageHandler(Filters.text, get_name),
                ],

            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        dispatcher.add_handler(conv_handler)
        start_handler = CommandHandler('start', start_conversation)
        dispatcher.add_handler(start_handler)
        dispatcher.add_handler(MessageHandler(Filters.text, get_phone))
        dispatcher.add_handler(CallbackQueryHandler(send_invoice, pattern='to_pay_now'))
        dispatcher.add_handler(CallbackQueryHandler(start_conversation, pattern='to_start'))
        updater.start_polling()
        updater.idle()
