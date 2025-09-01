from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import threading
import schedule
import calendar
from datetime import date

from database import(run_schedule, authenticate, get_db, 
                    get_number_of_all_drivers, get_number_of_reactivation, get_number_of_registration, calculate_level, 
                    get_monthly_number_of_all_drivers, get_monthly_number_of_reactivation, get_monthly_number_of_registration,
                    get_custom_number_of_all_drivers, get_custom_number_of_reactivation, get_custom_number_of_registration)

# Bot info
TOKEN: Final = "8418676143:AAFIMnVSpcO6ZpDSDz4A3AX-VXojxZ1ZPEM"
BOT_USERNAME: Final = "@LittleSalesReportBot"
first_date = 1
second_date = 1


def reply_handler(reply_txt, days=1):
    report_option_keyboard = [
        [InlineKeyboardButton("📅 Daily Report", callback_data="get_daily_report")],
        [InlineKeyboardButton("📆 Custom Range", callback_data="get_custom_report")],
        [InlineKeyboardButton("🗓️ Monthly Report", callback_data="get_monthly_report")],
        [InlineKeyboardButton("🏠 Back to Home", callback_data="start")]
    ]

    back_to_home_keyboard = [
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main_menu")]
    ]
    start_keyboard = [
        [InlineKeyboardButton("📊 Get Report", callback_data="get_report")],
        # [InlineKeyboardButton("Other Option", url="https://www.google.com")],
    ]
    restart_keyboard = [
        [InlineKeyboardButton("🔄 Retry", callback_data="restart")]
    ]

    day_picker_keyboard_1 = []
    day_picker_keyboard_2 = []

    temp = []
    for i in range(1, days+1):
        temp.append(InlineKeyboardButton(f"{i}", callback_data=f"first_date{i}"))
        if i%7 == 0:
            day_picker_keyboard_1.append(temp)
            temp = []
    day_picker_keyboard_1.append(temp)
    
    temp = []
    for i in range(1, days+1):
        temp.append(InlineKeyboardButton(f"{i}", callback_data=f"second_date{i}"))
        if i%7 == 0:
            day_picker_keyboard_2.append(temp)
            temp = []
    day_picker_keyboard_2.append(temp)


    if reply_txt == "reports_keyboard":
        return  InlineKeyboardMarkup(report_option_keyboard)
    
    if reply_txt == "start_keyboard":
        return InlineKeyboardMarkup(start_keyboard) 

    if reply_txt == "restart":
        return InlineKeyboardMarkup(restart_keyboard) 

    if reply_txt == "back_to_main_menu":
        return InlineKeyboardMarkup(back_to_home_keyboard)  

    if reply_txt == "day_picker_1":
        return InlineKeyboardMarkup(day_picker_keyboard_1)

    if reply_txt == "day_picker_2":
        return InlineKeyboardMarkup(day_picker_keyboard_2)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("start command called")
    user = update.effective_user
    db = next(get_db())
    username = user.username if user else ""    
    
    if authenticate(db, username):
        await update.message.reply_text(f"Hello {username}, I am Little Sales Report Bot. Choose the options below:", reply_markup=reply_handler("start_keyboard"))
    else:
        await update.message.reply_text(f"Hello {username}, you are not allowed to use this bot. Contact the support team.", reply_markup=reply_handler("restart"))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global first_date, second_date
    db = next(get_db())
    query = update.callback_query
    await query.answer()

    if query.data == "get_report":
        await query.edit_message_text(text="Choose an option to get your report:", reply_markup=reply_handler("reports_keyboard"))
    
    if query.data == "get_daily_report":
        username = update.effective_user.username
        # today = date.today()
        today = date(2025, 7, 14)
        number_of_total_drivers = get_number_of_all_drivers(db, username, today)
        number_of_reactivation = get_number_of_reactivation(db, username, today)
        number_of_registration = get_number_of_registration(db, username, today)
        
        await query.edit_message_text(
            text=   f"📊 Daily Report ({today})\n\n"
                    f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                    f"🔄 Reactivations: {number_of_reactivation}\n"
                    f"🆕 New Registrations: {number_of_registration}", 
            reply_markup=reply_handler("back_to_main_menu"))
    
    if query.data == "get_custom_report":
        # days = date.today().day
        days = date(2025, 7, 14).day
        await query.edit_message_text(text="Pick the first day:", reply_markup=reply_handler("day_picker_1", days))
    
    if query.data.startswith("first_date"):
        # days = date.today().day
        days = date(2025, 7, 14).day
        first_date = int(query.data[10:])
        await query.edit_message_text(text="Pick the second day:", reply_markup=reply_handler("day_picker_2", days))
    
    if query.data.startswith("second_date"):
        username = update.effective_user.username
        # today = date.today()
        today = date(2025, 7, 14)
        days = today.day
        second_date = int(query.data[11:])
        number_of_total_drivers = get_custom_number_of_all_drivers(db, username, today, first_date, second_date)
        number_of_reactivation = get_custom_number_of_reactivation(db, username, today, first_date, second_date)
        number_of_registration = get_custom_number_of_registration(db, username, today, first_date, second_date)
    

        await query.edit_message_text(
            text=   f"📊 Custom Report\n\n"
                    f"First Date: {first_date}\n"
                    f"Second Date: {second_date}\n"
                    f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                    f"🔄 Reactivations: {number_of_reactivation}\n"
                    f"🆕 New Registrations: {number_of_registration}",
            reply_markup=reply_handler("back_to_main_menu"))            
    
    if query.data == "get_monthly_report":
        username = update.effective_user.username
        # today = date.today()
        today = date(2025, 7, 14)
        last_day = calendar.monthrange(today.year, today.month)[1]
        if today.day == last_day:
            number_of_total_drivers = get_monthly_number_of_all_drivers(db, username, today)
            level = calculate_level(number_of_total_drivers)
            number_of_reactivation = get_monthly_number_of_reactivation(db, username, today)
            number_of_registration = get_monthly_number_of_registration(db, username, today)
            await query.edit_message_text(
                text=   f"📊 {today.strftime("%B")}, Monthly Report\n\n"
                        f"Level: {level}\n"
                        f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                        f"🔄 Reactivations: {number_of_reactivation}\n"
                        f"🆕 New Registrations: {number_of_registration}",
                reply_markup=reply_handler("back_to_main_menu"))
        else:
            last_month_day = today
            if today.month == 1:
                last_month_day = date(today.year - 1, 12, 15)
            else:
                last_month_day = date(today.year, today.month - 1, 15)

            number_of_total_drivers = get_monthly_number_of_all_drivers(db, username, last_month_day)
            level = calculate_level(number_of_total_drivers)
            number_of_reactivation = get_monthly_number_of_reactivation(db, username, last_month_day)
            number_of_registration = get_monthly_number_of_registration(db, username, last_month_day)
            await query.edit_message_text(
                text=   f"📊 Last Month ({last_month_day.strftime("%B")}) Monthly Report\n\n"
                        f"Level: {level}\n"
                        f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                        f"🔄 Reactivations: {number_of_reactivation}\n"
                        f"🆕 New Registrations: {number_of_registration}",
                reply_markup=reply_handler("back_to_main_menu"))

    
    if query.data == "back_to_main_menu":
        user = update.effective_user
        # db = next(get_db())
        username = user.username if user else ""    
        
        await query.edit_message_text(f"Hello {username}, I am Little Sales Report Bot. Choose the options below:", reply_markup=reply_handler("reports_keyboard"))

    if query.data == "restart":
        user = update.effective_user
        db = next(get_db())
        username = user.username if user else ""

        if authenticate(db, username):
            await query.edit_message_text(f"Hello {username}, I am Little Sales Report Bot. Choose the options below:", reply_markup=reply_handler("start_keyboard"))
        else:
            await query.edit_message_text(f"Hello {username}, you are not allowed to use this bot. Contact the support team.", reply_markup=reply_handler("restart"))
    
    if query.data == "start":
        user = update.effective_user
        username = user.username if user else ""

        await query.edit_message_text(f"Hello {username}, I am Little Sales Report Bot. Choose the options below:", reply_markup=reply_handler("start_keyboard"))

  
        


# schedule.every(60).minutes.do(job)
# threading.Thread(target=run_schedule, daemon=True).start()
# job()

# if __name__ == "main":
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CallbackQueryHandler(button_handler))
print("Little running...")
app.run_polling()