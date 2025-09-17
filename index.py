from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import threading
import schedule
import calendar
from datetime import date

from database import(job, run_schedule, 
                    authenticate, get_db, 
                    get_daily_driver_counts, 
                    get_custom_driver_counts,
                    get_monthly_driver_counts, 
                    calculate_level,
                    get_trip_success)

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
    
    # Daily report
    if query.data == "get_daily_report":
        username = update.effective_user.username
        today = date.today()
        number_of_total_drivers, number_of_registration, number_of_reactivation  = get_daily_driver_counts(db, username)
        registration_trip, reactivation_trip = get_trip_success(db, username, today=today)

        await query.edit_message_text(
            text=   f"📊 Daily Report ({today})\n\n"
                    f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                    f"🔄 Reactivations: {number_of_reactivation}\n"
                    f"🆕 New Registrations: {number_of_registration}\n\n"
                    f"🚗 Trip Engagement\n\n"
                    f"From Reactivations: {reactivation_trip}\n"
                    f"From New Registrations: {registration_trip}", 
            reply_markup=reply_handler("back_to_main_menu"))
    
    # Custom report
    if query.data == "get_custom_report":
        days = date.today().day
        # days = date(2025, 6, 20).day
        await query.edit_message_text(text="Pick the first day:", reply_markup=reply_handler("day_picker_1", days))
    
    if query.data.startswith("first_date"):
        days = date.today().day
        # days = date(2025, 6, 20).day
        first_date = int(query.data[10:])
        await query.edit_message_text(text="Pick the second day:", reply_markup=reply_handler("day_picker_2", days))
    
    if query.data.startswith("second_date"):
        username = update.effective_user.username
        today = date.today()
        # today = date(2025, 6, 20)
        days = today.day
        second_date = int(query.data[11:])
        number_of_total_drivers, number_of_registration, number_of_reactivation  = get_custom_driver_counts(db, username, first_date, second_date)
        registration_trip, reactivation_trip = get_trip_success(db, username, first_date=first_date, second_date=second_date)

        await query.edit_message_text(
            text=   f"📊 Custom Report\n\n"
                    f"First Date: {first_date}\n"
                    f"Second Date: {second_date}\n\n"
                    f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                    f"🔄 Reactivations: {number_of_reactivation}\n"
                    f"🆕 New Registrations: {number_of_registration}\n\n"
                    f"🚗 Trip Engagement\n\n"
                    f"From Reactivations: {reactivation_trip}\n"
                    f"From New Registrations: {registration_trip}",
            reply_markup=reply_handler("back_to_main_menu"))            
    
    # Monthly report
    if query.data == "get_monthly_report":
        username = update.effective_user.username
        number_of_total_drivers, number_of_registration, number_of_reactivation, today = get_monthly_driver_counts(db, username)
        registration_trip, reactivation_trip = get_trip_success(db, username)
        level = calculate_level(number_of_total_drivers)

        await query.edit_message_text(
            text=   f"📊 {today.strftime("%B")}, Monthly Report\n\n"
                    f"Level: {level}\n"
                    f"👤 Total Drivers Registered: {number_of_total_drivers}\n"
                    f"🔄 Reactivations: {number_of_reactivation}\n"
                    f"🆕 New Registrations: {number_of_registration}\n\n"
                    f"🚗 Trip Engagement\n\n"
                    f"From Reactivations: {reactivation_trip}\n"
                    f"From New Registrations: {registration_trip}",
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