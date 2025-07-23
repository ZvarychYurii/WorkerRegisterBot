# Worker Registration Telegram Bot

## Overview

This is a Telegram bot designed for collecting worker registration information through an interactive conversation flow. The bot validates user input, stores data in Google Sheets, and sends notifications to administrators. It features a multi-step registration process with confirmation and cancellation capabilities, primarily targeting Russian-speaking users.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

### Core Components
- **main.py**: Entry point containing the bot logic and conversation handlers
- **config.py**: Centralized configuration management with environment variable validation
- **google_sheets.py**: Google Sheets integration for data persistence
- **validators.py**: Input validation utilities for age and phone number formats

### Architecture Pattern
The bot uses a conversation-based state machine pattern implemented through Telegram's ConversationHandler, allowing for sequential data collection with proper state management.

## Key Components

### 1. Bot Framework Integration
- **Technology**: python-telegram-bot library
- **Purpose**: Handles Telegram API interactions and conversation flow management
- **States**: NAME, AGE, PHONE, CONFIRM - representing different stages of the registration process

### 2. Configuration Management
- **Centralized Config Class**: Manages all environment variables and validation
- **Environment Variables**: BOT_TOKEN (required), ADMIN_CHAT_ID, Google Sheets credentials, validation parameters
- **Validation**: Built-in configuration validation to ensure proper setup

### 3. Data Storage
- **Primary Storage**: Google Sheets integration using gspread library
- **Credentials**: Service account JSON credentials stored as environment variable
- **Fallback**: Graceful degradation when Google Sheets is unavailable

### 4. Input Validation
- **Age Validation**: Range checking (16-70 years by default)
- **Phone Validation**: Multiple Russian phone number formats supported
- **Name Validation**: Minimum length requirements with configurable limits

## Data Flow

1. **User Initiation**: User starts bot with /start command
2. **Sequential Collection**: Bot collects name → age → phone number
3. **Validation**: Each input is validated before proceeding to next step
4. **Confirmation**: User reviews collected data before final submission
5. **Persistence**: Valid data is stored in Google Sheets
6. **Notification**: Admin receives notification about new registration
7. **Completion**: User receives confirmation message

## External Dependencies

### Required Libraries
- **python-telegram-bot**: Telegram Bot API wrapper
- **gspread**: Google Sheets API integration
- **google-auth**: Authentication for Google services

### External Services
- **Telegram Bot API**: Core messaging platform
- **Google Sheets API**: Data persistence and sharing
- **Google Drive API**: Required for Sheets access permissions

### Authentication Requirements
- **Telegram Bot Token**: Required for bot operation
- **Google Service Account**: JSON credentials for Sheets access
- **Admin Chat ID**: Optional for admin notifications

## Deployment Strategy

### Environment Configuration
- **Required Variables**: BOT_TOKEN must be set
- **Optional Variables**: ADMIN_CHAT_ID, Google Sheets configuration, validation parameters
- **Graceful Degradation**: Bot functions without Google Sheets integration if credentials unavailable

### Error Handling
- **Input Validation**: Comprehensive validation with user-friendly error messages
- **Service Failures**: Graceful handling of Google Sheets connection issues
- **Configuration Errors**: Early validation with clear error messages

### Scalability Considerations
- **Stateless Design**: User data stored in conversation context, allowing horizontal scaling
- **External Storage**: Google Sheets provides shared data access across instances
- **Async Operations**: Full async/await implementation for better performance

### Monitoring and Logging
- **Structured Logging**: Configurable log levels with detailed user interaction tracking
- **Admin Notifications**: Real-time alerts for new registrations
- **Error Tracking**: Comprehensive error logging for debugging and monitoring