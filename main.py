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
Спробуйте ще раз:",
        "invalid_age": "❌ Вік має бути числом від 16 до 40 років. Спробуйте ще раз:",
        "invalid_name": "❌ Ім'я має містити мінімум 2 символи та тільки букви. Спробуйте ще раз:",
        "age_accepted": "✅ Вік прийнято!",
        "name_accepted": "✅ Чудово, {name}!",
        "confirm": "📋 Будь ласка, перевірте введені дані:

👤 Ім'я: {name}
🎂 Вік: {age} років
📞 Телефон: {phone}

Все вірно? Надішліть 'так' для підтвердження або 'ні' для повторного введення.",
        "confirm_yes": ["так", "yes", "y", "+"],
        "confirm_no": ["ні", "no", "n", "-"],
        "success": "✅ Реєстрація успішно завершена!

Ваші дані збережено в системі. Найближчим часом з вами зв'яжеться наш HR-менеджер.

Дякуємо за реєстрацію! 🎉",
        "error": "❌ Сталася помилка при збереженні даних. Будь ласка, спробуйте пізніше або зверніться до адміністратора.",
        "restart": "🔄 Добре, почнемо спочатку.
Введіть ваше повне ім'я:",
        "confirm_help": "❓ Будь ласка, дайте відповідь 'так' для підтвердження або 'ні' для повторного введення:",
        "cancel": "❌ Реєстрацію скасовано.
Якщо передумаєте, використовуйте команду /start для початку реєстрації.",
        "help": "🤖 <b>Бот реєстрації співробітників</b>

<b>Доступні команди:</b>
/start - Почати реєстрацію
/cancel - Скасувати поточну реєстрацію
/help - Показати це повідомлення

<b>Процес реєстрації:</b>
1️⃣ Оберіть мову
2️⃣ Введіть повне ім'я
3️⃣ Вкажіть вік (16-40 років)
4️⃣ Введіть номер телефону
5️⃣ Підтвердьте дані

❓ Якщо у вас виникли питання, зверніться до адміністратора."
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Я помогу вам зарегистрироваться в нашей системе.",
        "name": "Введите ваше полное имя:",
        "age": "Сколько вам лет? (от 16 до 40):",
        "phone": "Введите номер телефона:
🇺🇦 +380661234567",
        "invalid_phone": "❌ Некорректный формат номера.
Примеры:
🇺🇦 +380661234567
Попробуйте снова:",
        "invalid_age": "❌ Возраст должен быть числом от 16 до 40 лет. Попробуйте еще раз:",
        "invalid_name": "❌ Имя должно содержать минимум 2 символа и только буквы. Попробуйте еще раз:",
        "age_accepted": "✅ Возраст принят!",
        "name_accepted": "✅ Отлично, {name}!",
        "confirm": "📋 Пожалуйста, проверьте введенные данные:

👤 Имя: {name}
🎂 Возраст: {age} лет
📞 Телефон: {phone}

Все верно? Отправьте 'да' для подтверждения или 'нет' для повторного ввода.",
        "confirm_yes": ["да", "yes", "y", "+"],
        "confirm_no": ["нет", "no", "n", "-"],
        "success": "✅ Регистрация успешно завершена!

Ваши данные сохранены в системе. В ближайшее время с вами свяжется наш HR-менеджер.

Спасибо за регистрацию! 🎉",
        "error": "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже или обратитесь к администратору.",
        "restart": "🔄 Хорошо, давайте начнем заново.
Введите ваше полное имя:",
        "confirm_help": "❓ Пожалуйста, ответьте 'да' для подтверждения или 'нет' для повторного ввода:",
        "cancel": "❌ Регистрация отменена.
Если передумаете, используйте команду /start для начала регистрации.",
        "help": "🤖 <b>Бот регистрации сотрудников</b>

<b>Доступные команды:</b>
/start - Начать регистрацию
/cancel - Отменить текущую регистрацию
/help - Показать это сообщение

<b>Процесс регистрации:</b>
1️⃣ Выберите язык
2️⃣ Введите полное имя
3️⃣ Укажите возраст (16-40 лет)
4️⃣ Введите номер телефона
5️⃣ Подтвердите данные

❓ Если у вас возникли вопросы, обратитесь к администратору."
    },
    "en": {
        "welcome": "👋 Welcome! I'll help you register in our system.",
        "name": "Please enter your full name:",
        "age": "How old are you? (16 to 40 years):",
        "phone": "Enter your phone number:
🇺🇦 +380661234567",
        "invalid_phone": "❌ Invalid phone format.
Examples:
🇺🇦 +380661234567
Try again:",
        "invalid_age": "❌ Age must be a number between 16 and 40. Try again:",
        "invalid_name": "❌ Name must contain at least 2 characters and only letters. Try again:",
        "age_accepted": "✅ Age accepted!",
        "name_accepted": "✅ Great, {name}!",
        "confirm": "📋 Please verify your information:

👤 Name: {name}
🎂 Age: {age} years
📞 Phone: {phone}

Is everything correct? Send 'yes' to confirm or 'no' to re-enter.",
        "confirm_yes": ["yes", "y", "+", "да", "так"],
        "confirm_no": ["no", "n", "-", "нет", "ні"],
        "success": "✅ Registration completed successfully!

Your information has been saved. Our HR manager will contact you soon.

Thank you for registering! 🎉",
        "error": "❌ An error occurred while saving data. Please try again later or contact the administrator.",
        "restart": "🔄 Alright, let's start over.
Enter your full name:",
        "confirm_help": "❓ Please answer 'yes' to confirm or 'no' to re-enter:",
        "cancel": "❌ Registration cancelled.
If you change your mind, use /start to begin registration.",
        "help": "🤖 <b>Worker Registration Bot</b>

<b>Available commands:</b>
/start - Start registration
/cancel - Cancel current registration
/help - Show this message

<b>Registration process:</b>
1️⃣ Choose language
2️⃣ Enter full name
3️⃣ Specify age (16 to 40 years)
4️⃣ Enter phone number
5️⃣ Confirm information

❓ If you have questions, contact the administrator."
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
