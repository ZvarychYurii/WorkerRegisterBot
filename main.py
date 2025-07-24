import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from google_sheets import GoogleSheetsManager
from validators import validate_age, validate_phone, validate_name, format_phone_variants
from config import Config
from keep_alive import keep_alive  # импорт для веб-сервера

# Запускаем веб-сервер (для кейп-алайва на Replit/Railway)
keep_alive()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
LANG_CHOICE, NAME, AGE, PHONE, CONFIRM = range(5)

# Тексты сообщений на разных языках
TEXTS = {
    "ua": {
        "welcome": "👋 Вітаємо! Я допоможу вам зареєструватися в нашій системі.",
        "name": "Введіть ваше повне ім'я:",
        "age": "Скільки вам років? (від 16 до 40):",
        "phone": "Введіть номер телефону:
🇺🇦 +380661234567",
        "invalid_phone": "❌ Невірний формат номера.
Приклади:
🇺🇦 +380661234567
0661234567",
        "invalid_age": "❌ Вік має бути числом від 16 до 40 років. Спробуйте ще раз:",
        "invalid_name": "❌ Ім'я має містити мінімум 2 символи та тільки букви. Спробуйте ще раз:",
        "age_accepted": "✅ Вік прийнято!",
        "name_accepted": "✅ Чудово, {name}!",
        "confirm": "📋 Перевірте дані:
👤 Ім'я: {name}
🎂 Вік: {age} років
📞 Телефон: {phone}

Все вірно? Відправте 'так' або 'ні'.",
        "confirm_yes": ["так", "yes", "y", "+"],
        "confirm_no": ["ні", "no", "n", "-"],
        "success": "✅ Реєстрація завершена! Дякуємо за реєстрацію.",
        "error": "❌ Помилка збереження. Спробуйте пізніше.",
        "restart": "🔄 Почнемо знову. Введіть ім'я:",
        "confirm_help": "❓ Відповідь 'так' або 'ні'.",
        "cancel": "❌ Скасовано. /start для початку.",
        "help": "🤖 /start - почати
/cancel - скасувати
/help - допомога"
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Я помогу вам зарегистрироваться.",
        "name": "Введите полное имя:",
        "age": "Сколько лет? (16-40):",
        "phone": "Введите номер телефона:
🇺🇦 +380661234567",
        "invalid_phone": "❌ Неверный формат.
Примеры:
+380661234567
0661234567",
        "invalid_age": "❌ Возраст 16-40. Попробуйте снова:",
        "invalid_name": "❌ Имя от 2 букв. Попробуйте снова:",
        "age_accepted": "✅ Возраст принят!",
        "name_accepted": "✅ Отлично, {name}!",
        "confirm": "📋 Проверьте данные:
👤 Имя: {name}
🎂 Возраст: {age}
📞 Телефон: {phone}

Правильно? 'да' или 'нет'.",
        "confirm_yes": ["да", "yes", "y", "+"],
        "confirm_no": ["нет", "no", "n", "-"],
        "success": "✅ Регистрация завершена! Спасибо.",
        "error": "❌ Ошибка сохранения. Попробуйте позже.",
        "restart": "🔄 Начнём сначала. Введите имя:",
        "confirm_help": "❓ Ответьте 'да' или 'нет'.",
        "cancel": "❌ Отменено. /start для начала.",
        "help": "🤖 /start - начать
/cancel - отменить
/help - помощь"
    },
    "en": {
        "welcome": "👋 Welcome! Let's register.",
        "name": "Enter your full name:",
        "age": "How old are you? (16-40):",
        "phone": "Enter phone number:
🇺🇦 +380661234567",
        "invalid_phone": "❌ Invalid format.
Examples:
+380661234567
0661234567",
        "invalid_age": "❌ Age must be 16-40. Try again:",
        "invalid_name": "❌ Name must have 2+ letters. Try again:",
        "age_accepted": "✅ Age accepted!",
        "name_accepted": "✅ Great, {name}!",
        "confirm": "📋 Check data:
👤 Name: {name}
🎂 Age: {age}
📞 Phone: {phone}

Correct? 'yes' or 'no'.",
        "confirm_yes": ["yes", "y", "+"],
        "confirm_no": ["no", "n", "-"],
        "success": "✅ Registration done! Thanks.",
        "error": "❌ Save error. Try later.",
        "restart": "🔄 Let's restart. Enter name:",
        "confirm_help": "❓ Reply 'yes' or 'no'.",
        "cancel": "❌ Cancelled. /start to begin.",
        "help": "🤖 /start - start
/cancel - cancel
/help - help"
    }
}

class WorkerRegistrationBot:
    def __init__(self):
        self.config = Config()
        self.sheets_manager = GoogleSheetsManager()

    def get_text(self, context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs) -> str:
        lang = context.user_data.get('lang', 'ru')
        text = TEXTS[lang].get(key, TEXTS['ru'][key])
        return text.format(**kwargs) if kwargs else text

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        keyboard = [[
            InlineKeyboardButton("🇺🇦 Українська", callback_data='ua'),
            InlineKeyboardButton("🇬🇧 English", callback_data='en'),
            InlineKeyboardButton("🇷🇺 Русский", callback_data='ru')
        ]]
        await update.message.reply_text(
            "🌐 Оберіть мову / Choose language / Выберите язык:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return LANG_CHOICE

    async def lang_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        lang = query.data
        context.user_data['lang'] = lang
        await query.edit_message_text(
            f"{TEXTS[lang]['welcome']}\n\n{TEXTS[lang]['name']}"
        )
        return NAME

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
        age_text = update.message.text.strip()
        if not validate_age(age_text):
            await update.message.reply_text(self.get_text(context, "invalid_age"))
            return AGE
        context.user_data['age'] = age_text
        await update.message.reply_text(
            f"{self.get_text(context, 'age_accepted')}\n\n{self.get_text(context, 'phone')}"
        )
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        phone = update.message.text.strip()
        if not validate_phone(phone):
            await update.message.reply_text(self.get_text(context, "invalid_phone"))
            return PHONE
        # Форматируем номер в два варианта
        variants = format_phone_variants(phone)
        context.user_data['phone'] = variants['international']
        context.user_data['phone_local'] = variants['local']
        # Подтверждение
        data = context.user_data
        confirm_text = self.get_text(
            context,
            "confirm",
            name=data['name'],
            age=data['age'],
            phone=f"{data['phone']} ({data['phone_local']})"
        )
        await update.message.reply_text(confirm_text)
        return CONFIRM

    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        response = update.message.text.strip().lower()
        lang = context.user_data.get('lang', 'ru')
        if response in TEXTS[lang]['confirm_yes']:
            try:
                data = context.user_data
                user = update.effective_user
                registration_data = {
                    'name': data['name'],
                    'age': data['age'],
                    'phone': data['phone'],
                    'telegram_username': user.username or 'N/A',
                    'telegram_id': str(user.id)
                }
                success = await self.sheets_manager.add_registration(registration_data)
                if success:
                    await update.message.reply_text(
                        self.get_text(context, "success"),
                        reply_markup=ReplyKeyboardRemove()
                    )
                    await self.notify_admin(context, registration_data, user)
                else:
                    await update.message.reply_text(self.get_text(context, "error"))
            except Exception as e:
                logger.error(f"Error confirming registration: {e}")
                await update.message.reply_text(self.get_text(context, "error"))
            context.user_data.clear()
            return ConversationHandler.END
        elif response in TEXTS[lang]['confirm_no']:
            saved_lang = context.user_data.get('lang', 'ru')
            context.user_data.clear()
            context.user_data['lang'] = saved_lang
            await update.message.reply_text(self.get_text(context, "restart"))
            return NAME
        else:
            await update.message.reply_text(self.get_text(context, "confirm_help"))
            return CONFIRM

    async def notify_admin(self, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
        """Send notification to all admins"""
        if not self.config.ADMIN_CHAT_IDS:
            logger.warning("Admin chat IDs not configured")
            return
        message = (
            "🆕 <b>Новая регистрация сотрудника</b>\n\n"
            f"👤 <b>Имя:</b> {data['name']}\n"
            f"🎂 <b>Возраст:</b> {data['age']} лет\n"
            f"📞 <b>Телефон:</b> {data['phone']} ({data.get('phone_local', '')})\n"
            f"📱 <b>Telegram:</b> @{data['telegram_username']} (ID: {data['telegram_id']})"
        )
        for admin_id in self.config.ADMIN_CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            self.get_text(context, "cancel"),
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_text(context, "help"), parse_mode='HTML')

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in self.config.ADMIN_CHAT_IDS:
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return
        stats = await self.sheets_manager.get_registration_stats()
        stats_msg = (
            "📊 <b>Статистика регистраций</b>\n\n"
            f"👥 <b>Всего:</b> {stats['total']}\n"
            f"📅 <b>Сегодня:</b> {stats['today']}\n"
            f"📅 <b>Эта неделя:</b> {stats['this_week']}\n"
            f"📅 <b>Этот месяц:</b> {stats['this_month']}"
        )
        await update.message.reply_text(stats_msg, parse_mode='HTML')

    def setup_handlers(self, app: Application):
        conv = ConversationHandler(
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
        app.add_handler(conv)
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("stats", self.admin_stats))

def main():
    bot = WorkerRegistrationBot()
    app = Application.builder().token(bot.config.BOT_TOKEN).build()
    bot.setup_handlers(app)
    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
