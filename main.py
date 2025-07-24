import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from google_sheets import GoogleSheetsManager
from validators import validate_age, validate_phone, validate_name, format_phone_variants, sanitize_input
from config import Config
from keep_alive import keep_alive  # запускает простой веб-сервер для keep-alive

# Запускаем веб-сервер
keep_alive()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
LANG_CHOICE, NAME, AGE, PHONE, CONFIRM = range(5)

# Мультиязычные тексты
TEXTS = {
    "ua": {
        "welcome": "👋 Вітаємо! Я допоможу вам зареєструватися в нашій системі.",
        "name": "Введіть ваше повне ім'я:",
        "age": "Скільки вам років? (від 16 до 40):",
        "phone": "Введіть номер телефону:\n🇺🇦 +380661234567 або 0661234567",
        "invalid_phone": "❌ Невірний формат номера.\nПриклади:\n+380661234567\n0661234567",
        "invalid_age": "❌ Вік має бути числом від 16 до 40 років. Спробуйте ще раз:",
        "invalid_name": "❌ Ім'я має містити мінімум 2 символи та лише букви. Спробуйте ще раз:",
        "age_accepted": "✅ Вік прийнято!",
        "name_accepted": "✅ Чудово, {name}!",
        "confirm": "📋 Перевірте дані:\n👤 Ім'я: {name}\n🎂 Вік: {age} років\n📞 Телефон: {phone}\n\nВірно? Надішліть 'так' або 'ні'.",
        "confirm_yes": ["так", "yes", "y", "+"],
        "confirm_no": ["ні", "no", "n", "-"],
        "success": "✅ Реєстрація успішно завершена! Наш HR-менеджер зв'яжеться з вами найближчим часом.",
        "error": "❌ Помилка збереження. Спробуйте пізніше або зверніться до адміністратора.",
        "restart": "🔄 Почнемо спочатку. Введіть ваше повне ім'я:",
        "confirm_help": "❓ Відповідь 'так' або 'ні'.",
        "cancel": "❌ Скасовано. /start для початку.",
        "help": "🤖 Команди:\n/start - почати реєстрацію\n/cancel - скасувати\n/help - допомога"
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Я помогу вам зарегистрироваться.",
        "name": "Введите полное имя:",
        "age": "Сколько вам лет? (от 16 до 40):",
        "phone": "Введите номер телефона:\n🇺🇦 +380661234567 или 0661234567",
        "invalid_phone": "❌ Неверный формат номера.\nПримеры:\n+380661234567\n0661234567",
        "invalid_age": "❌ Возраст должен быть от 16 до 40 лет. Попробуйте снова:",
        "invalid_name": "❌ Имя должно содержать минимум 2 буквы. Попробуйте снова:",
        "age_accepted": "✅ Возраст принят!",
        "name_accepted": "✅ Отлично, {name}!",
        "confirm": "📋 Проверьте данные:\n👤 Имя: {name}\n🎂 Возраст: {age} лет\n📞 Телефон: {phone}\n\nВерно? Отправьте 'да' или 'нет'.",
        "confirm_yes": ["да", "yes", "y", "+"],
        "confirm_no": ["нет", "no", "n", "-"],
        "success": "✅ Регистрация успешна! Наш HR-менеджер свяжется с вами скоро.",
        "error": "❌ Ошибка сохранения. Попробуйте позже или обратитесь к администратору.",
        "restart": "🔄 Начнем сначала. Введите полное имя:",
        "confirm_help": "❓ Ответьте 'да' или 'нет'.",
        "cancel": "❌ Отменено. /start для начала.",
        "help": "🤖 Команды:\n/start - начать регистрацию\n/cancel - отменить\n/help - помощь"
    },
    "en": {
        "welcome": "👋 Welcome! I'll help you register.",
        "name": "Please enter your full name:",
        "age": "How old are you? (16 to 40):",
        "phone": "Enter phone number:\n🇺🇦 +380661234567 or 0661234567",
        "invalid_phone": "❌ Invalid format.\nExamples:\n+380661234567\n0661234567",
        "invalid_age": "❌ Age must be between 16 and 40. Try again:",
        "invalid_name": "❌ Name must have at least 2 letters. Try again:",
        "age_accepted": "✅ Age accepted!",
        "name_accepted": "✅ Great, {name}!",
        "confirm": "📋 Check data:\n👤 Name: {name}\n🎂 Age: {age}\n📞 Phone: {phone}\n\nCorrect? Send 'yes' or 'no'.",
        "confirm_yes": ["yes", "y", "+"],
        "confirm_no": ["no", "n", "-"],
        "success": "✅ Registration complete! Our HR manager will contact you soon.",
        "error": "❌ Error saving data. Try again later.",
        "restart": "🔄 Let's start over. Enter your full name:",
        "confirm_help": "❓ Reply 'yes' or 'no'.",
        "cancel": "❌ Cancelled. /start to begin.",
        "help": "🤖 Commands:\n/start - start registration\n/cancel - cancel\n/help - help"
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
            self.get_text(context, "welcome") + "\n\n" + self.get_text(context, "name"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return LANG_CHOICE

    async def lang_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        lang = query.data
        context.user_data['lang'] = lang
        await query.edit_message_text(
            self.get_text(context, "welcome") + "\n\n" + self.get_text(context, "name")
        )
        return NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        name = sanitize_input(update.message.text)
        if not validate_name(name):
            await update.message.reply_text(self.get_text(context, "invalid_name"))
            return NAME
        context.user_data['name'] = name
        await update.message.reply_text(
            self.get_text(context, "name_accepted", name=name) + "\n\n" + self.get_text(context, "age")
        )
        return AGE

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        age = update.message.text.strip()
        if not validate_age(age):
            await update.message.reply_text(self.get_text(context, "invalid_age"))
            return AGE
        context.user_data['age'] = age
        await update.message.reply_text(
            self.get_text(context, "age_accepted") + "\n\n" + self.get_text(context, "phone")
        )
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        phone = update.message.text.strip()
        if not validate_phone(phone):
            await update.message.reply_text(self.get_text(context, "invalid_phone"))
            return PHONE
        variants = format_phone_variants(phone)
        context.user_data['phone'] = variants['international']
        context.user_data['phone_local'] = variants['local']
        await update.message.reply_text(
            self.get_text(context, "confirm", name=context.user_data['name'], age=context.user_data['age'], phone=f"{variants['international']} ({variants['local']})"),
            reply_markup=ReplyKeyboardRemove()
        )
        return CONFIRM

    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        resp = update.message.text.strip().lower()
        lang = context.user_data.get('lang','ru')
        if resp in TEXTS[lang]['confirm_yes']:
            data = context.user_data
            user = update.effective_user
            reg = {'name': data['name'], 'age': data['age'], 'phone': data['phone'], 'telegram_username': user.username or 'N/A', 'telegram_id': str(user.id)}
            if await self.sheets_manager.add_registration(reg):
                await update.message.reply_text(self.get_text(context,"success"))
                for aid in self.config.ADMIN_CHAT_IDS:
                    await context.bot.send_message(aid,
                        f"🆕 Нова реєстрація:\nІм'я: {reg['name']}\nВік: {reg['age']}\nТелефон: {reg['phone']} ({context.user_data['phone_local']})\nTelegram: @{reg['telegram_username']} (ID {reg['telegram_id']})",
                        parse_mode='HTML')
            else:
                await update.message.reply_text(self.get_text(context,"error"))
            context.user_data.clear()
            return ConversationHandler.END
        elif resp in TEXTS[lang]['confirm_no']:
            lang = context.user_data.get('lang')
            context.user_data.clear()
            context.user_data['lang'] = lang
            await update.message.reply_text(self.get_text(context,"restart"))
            return NAME
        else:
            await update.message.reply_text(self.get_text(context,"confirm_help"))
            return CONFIRM

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(self.get_text(context,"cancel"), reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_text(context,"help"), parse_mode='HTML')

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in self.config.ADMIN_CHAT_IDS:
            return await update.message.reply_text("❌ У вас нет прав")
        stats = await self.sheets_manager.get_registration_stats()
        await update.message.reply_text(
            f"📊 Всего: {stats['total']}, Сегодня: {stats['today']}, Неделя: {stats['this_week']}, Месяц: {stats['this_month']}"
        )

    def setup_handlers(self, app: Application):
        conv = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={LANG_CHOICE:[CallbackQueryHandler(self.lang_choice)], NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)], AGE:[MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_age)], PHONE:[MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_phone)], CONFIRM:[MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)]},
            fallbacks=[CommandHandler('cancel',self.cancel)]
        )
        app.add_handler(conv)
        app.add_handler(CommandHandler('help', self.help_command))
        app.add_handler(CommandHandler('stats', self.admin_stats))

async def main():
    bot = WorkerRegistrationBot()
    app = Application.builder().token(bot.config.BOT_TOKEN).build()
    bot.setup_handlers(app)
    logger.info("Bot started")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
