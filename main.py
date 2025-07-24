import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from google_sheets import GoogleSheetsManager
from validators import validate_age, validate_phone, validate_name
from config import Config
from keep_alive import keep_alive

# Запускаем веб-сервер
keep_alive()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
LANG_CHOICE, NAME, AGE, PHONE, CONFIRM = range(5)

# Localization (UA, RU, EN) – тот же словарь TEXTS, как у тебя
from texts import TEXTS  # предполагается, что ты вынес словарь TEXTS отдельно

class WorkerRegistrationBot:
    def __init__(self):
        self.config = Config()
        self.sheets_manager = GoogleSheetsManager()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        keyboard = [[
            InlineKeyboardButton("\ud83c\uddfa\ud83c\udde6 \u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430", callback_data='ua'),
            InlineKeyboardButton("\ud83c\uddec\ud83c\udde7 English", callback_data='en'),
            InlineKeyboardButton("\ud83c\uddf7\ud83c\uddfa \u0420\u0443\u0441\u0441\u043a\u0438\u0439", callback_data='ru')
        ]]
        await update.message.reply_text(
            "\ud83c\udf10 Choose language / \u041e\u0431\u0435\u0440\u0456\u0442\u044c \u043c\u043e\u0432\u0443 / \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return LANG_CHOICE

    async def lang_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        lang = query.data
        context.user_data['lang'] = lang
        await query.edit_message_text(f"{TEXTS[lang]['welcome']}\n\n{TEXTS[lang]['name']}")
        return NAME

    def get_text(self, context, key, **kwargs):
        lang = context.user_data.get('lang', 'ru')
        return TEXTS[lang][key].format(**kwargs) if kwargs else TEXTS[lang][key]

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        name = update.message.text.strip()
        if not validate_name(name):
            await update.message.reply_text(self.get_text(context, "invalid_name"))
            return NAME
        context.user_data['name'] = name
        await update.message.reply_text(
            f"{self.get_text(context, 'name_accepted', name=name)}\n\n{self.get_text(context, 'age')}"
        )
        return AGE

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        age = update.message.text.strip()
        if not validate_age(age):
            await update.message.reply_text(self.get_text(context, "invalid_age"))
            return AGE
        context.user_data['age'] = age
        await update.message.reply_text(
            f"{self.get_text(context, 'age_accepted')}\n\n{self.get_text(context, 'phone')}"
        )
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        phone = update.message.text.strip()
        if not validate_phone(phone):
            await update.message.reply_text(self.get_text(context, "invalid_phone"))
            return PHONE
        context.user_data['phone'] = phone
        return await self.confirm(update, context)

    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        data = context.user_data
        msg = self.get_text(context, "confirm", name=data['name'], age=data['age'], phone=data['phone'])
        await update.message.reply_text(msg)
        return CONFIRM

    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        response = update.message.text.strip().lower()
        lang = context.user_data.get('lang', 'ru')
        yes_list = TEXTS[lang]['confirm_yes']
        no_list = TEXTS[lang]['confirm_no']

        if response in yes_list:
            data = context.user_data
            user = update.effective_user
            reg_data = {
                'name': data['name'],
                'age': data['age'],
                'phone': data['phone'],
                'telegram_username': user.username or 'N/A',
                'telegram_id': str(user.id),
                'registration_date': None
            }
            success = await self.sheets_manager.add_registration(reg_data)
            if success:
                await update.message.reply_text(self.get_text(context, 'success'), reply_markup=ReplyKeyboardRemove())
                await self.notify_admins(context, reg_data)
            else:
                await update.message.reply_text(self.get_text(context, 'error'))
            context.user_data.clear()
            return ConversationHandler.END

        elif response in no_list:
            lang = context.user_data.get('lang', 'ru')
            context.user_data.clear()
            context.user_data['lang'] = lang
            await update.message.reply_text(self.get_text(context, 'restart'))
            return NAME

        else:
            await update.message.reply_text(self.get_text(context, 'confirm_help'))
            return CONFIRM

    async def notify_admins(self, context: ContextTypes.DEFAULT_TYPE, data: dict):
        """Send notification to all admins about new registration"""
        if not self.config.ADMIN_CHAT_IDS:
            logger.warning("Admin chat IDs not configured")
            return

        message = (
            "\ud83d\udd0e <b>New Registration</b>\n\n"
            f"\ud83d\udc64 <b>Name:</b> {data['name']}\n"
            f"\ud83c\udf82 <b>Age:</b> {data['age']}\n"
            f"\ud83d\udcde <b>Phone:</b> {data['phone']}\n"
            f"\ud83d\udcf1 <b>Telegram:</b> @{data['telegram_username']} (ID: {data['telegram_id']})"
        )

        for admin_id in self.config.ADMIN_CHAT_IDS:
            await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(self.get_text(context, 'cancel'), reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_text(context, 'help'), parse_mode='HTML')

    def setup_handlers(self, app: Application):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                LANG_CHOICE: [CallbackQueryHandler(self.lang_choice)],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_age)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_phone)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("help", self.help_command))

def main():
    bot = WorkerRegistrationBot()
    app = Application.builder().token(bot.config.BOT_TOKEN).build()
    bot.setup_handlers(app)
    logger.info("Worker Bot запущен")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
