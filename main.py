import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from google_sheets import GoogleSheetsManager
from validators import validate_age, validate_phone
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
NAME, AGE, PHONE, CONFIRM = range(4)

class WorkerRegistrationBot:
    def __init__(self):
        self.config = Config()
        self.sheets_manager = GoogleSheetsManager()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the registration process"""
        user = update.effective_user
        logger.info(f"User {user.id} started registration")
        
        welcome_message = (
            "👋 Добро пожаловать в систему регистрации сотрудников!\n\n"
            "Я помогу вам зарегистрироваться в нашей системе. "
            "Процесс займет всего несколько минут.\n\n"
            "Для начала, пожалуйста, введите ваше полное имя:"
        )
        
        await update.message.reply_text(welcome_message)
        return NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's name"""
        name = update.message.text.strip()
        
        if len(name) < 2:
            await update.message.reply_text(
                "❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:"
            )
            return NAME
            
        if not all(char.isalpha() or char.isspace() for char in name):
            await update.message.reply_text(
                "❌ Имя должно содержать только буквы. Попробуйте еще раз:"
            )
            return NAME
        
        context.user_data['name'] = name
        await update.message.reply_text(
            f"✅ Отлично, {name}!\n\n"
            "Теперь укажите ваш возраст (от 16 до 70 лет):"
        )
        return AGE

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's age"""
        age_text = update.message.text.strip()
        
        if not validate_age(age_text):
            await update.message.reply_text(
                "❌ Возраст должен быть числом от 16 до 70 лет. "
                "Попробуйте еще раз:"
            )
            return AGE
        
        context.user_data['age'] = age_text
        await update.message.reply_text(
            "✅ Возраст принят!\n\n"
            "Теперь введите ваш номер телефона в формате:\n"
            "+7 (999) 123-45-67 или +79991234567"
        )
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect user's phone number"""
        phone = update.message.text.strip()
        
        if not validate_phone(phone):
            await update.message.reply_text(
                "❌ Некорректный формат номера телефона.\n"
                "Используйте формат: +7 (999) 123-45-67 или +79991234567\n"
                "Попробуйте еще раз:"
            )
            return PHONE
        
        context.user_data['phone'] = phone
        
        # Show confirmation
        data = context.user_data
        confirmation_message = (
            "📋 Пожалуйста, проверьте введенные данные:\n\n"
            f"👤 Имя: {data['name']}\n"
            f"🎂 Возраст: {data['age']} лет\n"
            f"📞 Телефон: {data['phone']}\n\n"
            "Все верно? Отправьте 'да' для подтверждения или 'нет' для повторного ввода."
        )
        
        await update.message.reply_text(confirmation_message)
        return CONFIRM

    async def confirm_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm and save registration data"""
        response = update.message.text.strip().lower()
        
        if response in ['да', 'yes', 'y', '+']:
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
                    await update.message.reply_text(
                        "✅ Регистрация успешно завершена!\n\n"
                        "Ваши данные сохранены в системе. "
                        "В ближайшее время с вами свяжется наш HR-менеджер.\n\n"
                        "Спасибо за регистрацию! 🎉",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    
                    # Notify admin
                    await self.notify_admin(context, registration_data, user)
                    
                else:
                    await update.message.reply_text(
                        "❌ Произошла ошибка при сохранении данных. "
                        "Пожалуйста, попробуйте позже или обратитесь к администратору."
                    )
                
            except Exception as e:
                logger.error(f"Error during registration confirmation: {e}")
                await update.message.reply_text(
                    "❌ Произошла техническая ошибка. "
                    "Пожалуйста, попробуйте позже."
                )
            
            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END
            
        elif response in ['нет', 'no', 'n', '-']:
            await update.message.reply_text(
                "🔄 Хорошо, давайте начнем заново.\n"
                "Введите ваше полное имя:"
            )
            context.user_data.clear()
            return NAME
            
        else:
            await update.message.reply_text(
                "❓ Пожалуйста, ответьте 'да' для подтверждения или 'нет' для повторного ввода:"
            )
            return CONFIRM

    async def notify_admin(self, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
        """Send notification to admin about new registration"""
        if not self.config.ADMIN_CHAT_ID:
            logger.warning("Admin chat ID not configured")
            return
            
        try:
            admin_message = (
                "🆕 <b>Новая регистрация сотрудника</b>\n\n"
                f"👤 <b>Имя:</b> {data['name']}\n"
                f"🎂 <b>Возраст:</b> {data['age']} лет\n"
                f"📞 <b>Телефон:</b> {data['phone']}\n"
                f"📱 <b>Telegram:</b> @{data['telegram_username']} (ID: {data['telegram_id']})\n"
                f"📅 <b>Дата регистрации:</b> {data.get('registration_date', 'Сейчас')}"
            )
            
            await context.bot.send_message(
                chat_id=self.config.ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel registration process"""
        await update.message.reply_text(
            "❌ Регистрация отменена.\n"
            "Если передумаете, используйте команду /start для начала регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = (
            "🤖 <b>Бот регистрации сотрудников</b>\n\n"
            "<b>Доступные команды:</b>\n"
            "/start - Начать регистрацию\n"
            "/register - Начать регистрацию (альтернатива)\n"
            "/cancel - Отменить текущую регистрацию\n"
            "/help - Показать это сообщение\n\n"
            "<b>Процесс регистрации:</b>\n"
            "1️⃣ Введите полное имя\n"
            "2️⃣ Укажите возраст (16-70 лет)\n"
            "3️⃣ Введите номер телефона\n"
            "4️⃣ Подтвердите данные\n\n"
            "❓ Если у вас возникли вопросы, обратитесь к администратору."
        )
        
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
