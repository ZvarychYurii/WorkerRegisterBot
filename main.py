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

from keep_alive import keep_alive  # импорт в конце

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

# Multi-language text definitions
TEXTS = {
    "ua": {
        "welcome": "👋 Вітаємо! Я допоможу вам зареєструватися в нашій системі.",
        "name": "Введіть ваше повне ім'я:",
        "age": "Скільки вам років? (від 16 до 40):",
        "phone": "Введіть номер телефону:\n🇺🇦 +380661234567",
        "invalid_phone": "❌ Невірний формат номера.\nПриклади:\n🇺🇦 +380661234567\nСпробуйте ще раз:",
        "invalid_age": "❌ Вік має бути числом від 16 до 40 років. Спробуйте ще раз:",
        "invalid_name": "❌ Ім'я має містити мінімум 2 символи та тільки букви. Спробуйте ще раз:",
        "age_accepted": "✅ Вік прийнято!",
        "name_accepted": "✅ Чудово, {name}!",
        "confirm": "📋 Будь ласка, перевірте введені дані:\n\n👤 Ім'я: {name}\n🎂 Вік: {age} років\n📞 Телефон: {phone}\n\nВсе вірно? Надішліть 'так' для підтвердження або 'ні' для повторного введення.",
        "confirm_yes": ["так", "yes", "y", "+"],
        "confirm_no": ["ні", "no", "n", "-"],
        "success": "✅ Реєстрація успішно завершена!\n\nВаші дані збережено в системі. Найближчим часом з вами зв'яжеться наш HR-менеджер.\n\nДякуємо за реєстрацію! 🎉",
        "error": "❌ Сталася помилка при збереженні даних. Будь ласка, спробуйте пізніше або зверніться до адміністратора.",
        "restart": "🔄 Добре, почнемо спочатку.\nВведіть ваше повне ім'я:",
        "confirm_help": "❓ Будь ласка, дайте відповідь 'так' для підтвердження або 'ні' для повторного введення:",
        "cancel": "❌ Реєстрацію скасовано.\nЯкщо передумаєте, використовуйте команду /start для початку реєстрації.",
        "help": "🤖 <b>Бот реєстрації співробітників</b>\n\n<b>Доступні команди:</b>\n/start - Почати реєстрацію\n/cancel - Скасувати поточну реєстрацію\n/help - Показати це повідомлення\n\n<b>Процес реєстрації:</b>\n1️⃣ Оберіть мову\n2️⃣ Введіть повне ім'я\n3️⃣ Вкажіть вік (16-70 років)\n4️⃣ Введіть номер телефону\n5️⃣ Підтвердьте дані\n\n❓ Якщо у вас виникли питання, зверніться до адміністратора."
    },
    "ru": {
        "welcome": "👋 Добро пожаловать! Я помогу вам зарегистрироваться в нашей системе.",
        "name": "Введите ваше полное имя:",
        "age": "Сколько вам лет? (от 16 до 40):",
        "phone": "Введите номер телефона:\n🇺🇦 +380661234567",
        "invalid_phone": "❌ Некорректный формат номера.\nПримеры:\n🇺🇦 +380661234567\nПопробуйте снова:",
        "invalid_age": "❌ Возраст должен быть числом от 16 до 40 лет. Попробуйте еще раз:",
        "invalid_name": "❌ Имя должно содержать минимум 2 символа и только буквы. Попробуйте еще раз:",
        "age_accepted": "✅ Возраст принят!",
        "name_accepted": "✅ Отлично, {name}!",
        "confirm": "📋 Пожалуйста, проверьте введенные данные:\n\n👤 Имя: {name}\n🎂 Возраст: {age} лет\n📞 Телефон: {phone}\n\nВсе верно? Отправьте 'да' для подтверждения или 'нет' для повторного ввода.",
        "confirm_yes": ["да", "yes", "y", "+"],
        "confirm_no": ["нет", "no", "n", "-"],
        "success": "✅ Регистрация успешно завершена!\n\nВаши данные сохранены в системе. В ближайшее время с вами свяжется наш HR-менеджер.\n\nСпасибо за регистрацию! 🎉",
        "error": "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже или обратитесь к администратору.",
        "restart": "🔄 Хорошо, давайте начнем заново.\nВведите ваше полное имя:",
        "confirm_help": "❓ Пожалуйста, ответьте 'да' для подтверждения или 'нет' для повторного ввода:",
        "cancel": "❌ Регистрация отменена.\nЕсли передумаете, используйте команду /start для начала регистрации.",
        "help": "🤖 <b>Бот регистрации сотрудников</b>\n\n<b>Доступные команды:</b>\n/start - Начать регистрацию\n/cancel - Отменить текущую регистрацию\n/help - Показать это сообщение\n\n<b>Процесс регистрации:</b>\n1️⃣ Выберите язык\n2️⃣ Введите полное имя\n3️⃣ Укажите возраст (16-70 лет)\n4️⃣ Введите номер телефона\n5️⃣ Подтвердите данные\n\n❓ Если у вас возникли вопросы, обратитесь к администратору."
    },
    "en": {
        "welcome": "👋 Welcome! I'll help you register in our system.",
        "name": "Please enter your full name:",
        "age": "How old are you? (16 to 40 years):",
        "phone": "Enter your phone number:\n🇺🇦 +380661234567",
        "invalid_phone": "❌ Invalid phone format.\nExamples:\n🇺🇦 +380661234567\nTry again:",
        "invalid_age": "❌ Age must be a number between 16 and 40. Try again:",
        "invalid_name": "❌ Name must contain at least 2 characters and only letters. Try again:",
        "age_accepted": "✅ Age accepted!",
        "name_accepted": "✅ Great, {name}!",
        "confirm": "📋 Please verify your information:\n\n👤 Name: {name}\n🎂 Age: {age} years\n📞 Phone: {phone}\n\nIs everything correct? Send 'yes' to confirm or 'no' to re-enter.",
        "confirm_yes": ["yes", "y", "+", "да", "так"],
        "confirm_no": ["no", "n", "-", "нет", "ні"],
        "success": "✅ Registration completed successfully!\n\nYour information has been saved. Our HR manager will contact you soon.\n\nThank you for registering! 🎉",
        "error": "❌ An error occurred while saving data. Please try again later or contact the administrator.",
        "restart": "🔄 Alright, let's start over.\nEnter your full name:",
        "confirm_help": "❓ Please answer 'yes' to confirm or 'no' to re-enter:",
        "cancel": "❌ Registration cancelled.\nIf you change your mind, use /start to begin registration.",
        "help": "🤖 <b>Worker Registration Bot</b>\n\n<b>Available commands:</b>\n/start - Start registration\n/cancel - Cancel current registration\n/help - Show this message\n\n<b>Registration process:</b>\n1️⃣ Choose language\n2️⃣ Enter full name\n3️⃣ Specify age (16-70 years)\n4️⃣ Enter phone number\n5️⃣ Confirm information\n\n❓ If you have questions, contact the administrator."
    }
}

class WorkerRegistrationBot:
    def __init__(self):
        self.config = Config()
        self.sheets_manager = GoogleSheetsManager()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the registration process with language selection"""
        user = update.effective_user
        logger.info(f"User {user.id} started registration")
        
        keyboard = [
            [
                InlineKeyboardButton("🇺🇦 Українська", callback_data='ua'),
                InlineKeyboardButton("🇬🇧 English", callback_data='en'),
                InlineKeyboardButton("🇷🇺 Русский", callback_data='ru')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌐 Оберіть мову / Choose language / Выберите язык:",
            reply_markup=reply_markup
        )
        return LANG_CHOICE
    
    async def lang_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle language selection"""
        query = update.callback_query
        await query.answer()
        
        lang = query.data
        context.user_data['lang'] = lang
        
        welcome_text = TEXTS[lang]["welcome"]
        name_text = TEXTS[lang]["name"]
        
        await query.edit_message_text(f"{welcome_text}\n\n{name_text}")
        return NAME
    
    def get_text(self, context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs) -> str:
        """Get localized text"""
        lang = context.user_data.get('lang', 'ru')  # Default to Russian
        text = TEXTS[lang].get(key, TEXTS['ru'][key])  # Fallback to Russian
        return text.format(**kwargs) if kwargs else text

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's name"""
        name = update.message.text.strip()
        
        if not validate_name(name):
            error_text = self.get_text(context, "invalid_name")
            await update.message.reply_text(error_text)
            return NAME
        
        context.user_data['name'] = name
        name_accepted_text = self.get_text(context, "name_accepted", name=name)
        age_text = self.get_text(context, "age")
        
        await update.message.reply_text(f"{name_accepted_text}\n\n{age_text}")
        return AGE

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's age"""
        age_text = update.message.text.strip()
        
        if not validate_age(age_text):
            error_text = self.get_text(context, "invalid_age")
            await update.message.reply_text(error_text)
            return AGE
        
        context.user_data['age'] = age_text
        
        age_accepted_text = self.get_text(context, "age_accepted")
        phone_text = self.get_text(context, "phone")
        
        await update.message.reply_text(f"{age_accepted_text}\n\n{phone_text}")
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's phone number"""
        phone = update.message.text.strip()
        
        if not validate_phone(phone):
            error_text = self.get_text(context, "invalid_phone")
            await update.message.reply_text(error_text)
            return PHONE
        
        context.user_data['phone'] = phone
        
        # Show confirmation
        data = context.user_data
        confirmation_text = self.get_text(context, "confirm", 
                                        name=data['name'], 
                                        age=data['age'], 
                                        phone=data['phone'])
        
        await update.message.reply_text(confirmation_text)
        return CONFIRM

    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm and save registration data"""
        response = update.message.text.strip().lower()
        lang = context.user_data.get('lang', 'ru')
        
        confirm_yes = TEXTS[lang]["confirm_yes"]
        confirm_no = TEXTS[lang]["confirm_no"]
        
        if response in confirm_yes:
            try:
                data = context.user_data
                user = update.effective_user
                
                # Add user metadata
                registration_data = {
                    'name': data['name'],
                    'age': data['age'],
                    'phone': data['phone'],
                    'telegram_username': user.username or 'N/A',
                    'telegram_id': str(user.id),
                    'registration_date': None  # Will be set by sheets manager
                }
                
                # Save to Google Sheets
                success = await self.sheets_manager.add_registration(registration_data)
                
                if success:
                    success_text = self.get_text(context, "success")
                    await update.message.reply_text(success_text, reply_markup=ReplyKeyboardRemove())
                    
                    # Notify admin
                    await self.notify_admin(context, registration_data, user)
                    
                else:
                    error_text = self.get_text(context, "error")
                    await update.message.reply_text(error_text)
                
            except Exception as e:
                logger.error(f"Error during registration confirmation: {e}")
                error_text = self.get_text(context, "error")
                await update.message.reply_text(error_text)
            
            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END
            
        elif response in confirm_no:
            restart_text = self.get_text(context, "restart")
            await update.message.reply_text(restart_text)
            
            # Keep language but clear other data
            saved_lang = context.user_data.get('lang', 'ru')
            context.user_data.clear()
            context.user_data['lang'] = saved_lang
            return NAME
            
        else:
            help_text = self.get_text(context, "confirm_help")
            await update.message.reply_text(help_text)
            return CONFIRM

    async def notify_admin(self, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
    """Send notification to all admins about new registration"""
    if not self.config.ADMIN_CHAT_IDS:
        logger.warning("Admin chat IDs not configured")
        return

    admin_message = (
        "🆕 <b>Нова реєстрація співробітника</b>\n\n"
        f"👤 <b>Ім’я:</b> {data['name']}\n"
        f"🎂 <b>Вік:</b> {data['age']} років\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"📱 <b>Telegram:</b> @{data['telegram_username']} (ID: {data['telegram_id']})\n"
        f"📅 <b>Дата реєстрації:</b> {data.get('registration_date', 'Сьогодні')}"
    )

    for admin_id in self.config.ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"❌ Не вдалося відправити повідомлення адміну {admin_id}: {e}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel registration process"""
        cancel_text = self.get_text(context, "cancel")
        await update.message.reply_text(cancel_text, reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = self.get_text(context, "help")
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show registration statistics (admin only)"""
        user_id = update.effective_user.id
        
        if str(user_id) != str(self.config.ADMIN_CHAT_ID):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return
            
        try:
            stats = await self.sheets_manager.get_registration_stats()
            
            stats_message = (
                "📊 <b>Статистика регистраций</b>\n\n"
                f"👥 <b>Всего регистраций:</b> {stats.get('total', 0)}\n"
                f"📅 <b>За сегодня:</b> {stats.get('today', 0)}\n"
                f"📅 <b>За эту неделю:</b> {stats.get('this_week', 0)}\n"
                f"📅 <b>За этот месяц:</b> {stats.get('this_month', 0)}"
            )
            
            await update.message.reply_text(stats_message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении статистики."
            )

    def setup_handlers(self, app: Application):
        """Setup all bot handlers"""
        # Conversation handler for registration
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                CommandHandler("register", self.start)
            ],
            states={
                LANG_CHOICE: [CallbackQueryHandler(self.lang_choice)],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_age)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_phone)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_registration)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        
        # Add handlers
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("stats", self.admin_stats))

def main():
    """Main function to run the bot"""
    try:
        # Initialize bot
        bot = WorkerRegistrationBot()
        
        # Create application
        app = Application.builder().token(bot.config.BOT_TOKEN).build()
        
        # Setup handlers
        bot.setup_handlers(app)
        
        logger.info("Worker Registration Bot is starting...")
        print("🤖 Worker Registration Bot is running...")
        
        # Run the bot
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()
