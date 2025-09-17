from sqlalchemy import create_engine, Column, String, Date, Integer, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import date, datetime

import schedule
import time
import calendar
import functools

engine = create_engine('sqlite:///database.db')
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, default="-")
    registrations = relationship("Registration", back_populates="user")

class Registration(Base):
    __tablename__ = 'registrations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_date = Column(Date, nullable=False, default=date(2060, 1, 1))
    status = Column(String, nullable=False, default="-")
    driver_phone = Column(String, nullable=False, default="-")
    trip_no = Column(Integer, nullable=False, default=0)
    username = Column(Integer, ForeignKey("users.username"))
    user = relationship("User", back_populates="registrations")



Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def with_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        db: Session = SessionLocal()
        try:
            result = func(*args, db=db, **kwargs)
            db.commit()
            return result
        except Exception:
            db.rollback()
        finally:
            db.close()
    return wrapper 

class RegistrationSchema(BaseModel):
    entry_date : date = date(2060, 1, 1)
    status : str = ""
    driver_phone : str = ""
    username : str = ""

class UserSchema(BaseModel):
    username : str = ""
    name : str = ""

# Google spreadsheet
import gspread
from gspread import Client, Spreadsheet, Worksheet
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
def setup_spreadsheet():
    creds = Credentials.from_service_account_file(filename="littlesalesreport.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open("driver-approval")
    sheet = spreadsheet.worksheet("BotReport")
    return sheet

def fetch_all_records():
    sheet = setup_spreadsheet()
    records = sheet.get_all_records()
    return records

@with_db
def update_user(records: list, db: Session|None=None):
    if db:
        for record in records:
            user = db.query(User).filter_by(username=record["username"]).first()
            if user:
                continue
            user_schema = UserSchema()
            user_schema.username = record["username"]
            user_schema.name = record["name"]
            user = User(**user_schema.model_dump())
            db.add(user)
            db.commit()
        
@with_db
def update_registration(records: list, db: Session|None=None):
    if db:
        for record in records:
            registration = db.query(Registration).filter(Registration.driver_phone == record["driver_phone"]).first()
            if registration:
                registration.status = record["status"]
                registration.entry_date = datetime.strptime(record["date"], "%m/%d/%Y").date()
                registration.trip_no = record["trip_no"]
                registration.username = record["username"]
                db.add(registration)
                continue


            registration_schema = RegistrationSchema()
            registration_schema.status = record["status"]
            registration_schema.entry_date = datetime.strptime(record["date"], "%m/%d/%Y").date()
            registration_schema.driver_phone = record["driver_phone"]
            user = db.query(User).filter(User.username == record["username"]).first()
            if not user:
                continue
            registration_schema.username = record["username"]
            db.add(Registration(**registration_schema.model_dump()))
            
        db.commit()

@with_db
def authenticate(username: str, db: Session|None=None):
    if db:
        user = db.query(User).filter(User.username==username).first()
        if user:
            return True
        return False

def job():
    records = fetch_all_records()
    update_user(records)
    update_registration(records)
    print("Database Updated")

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# ------------------------------------------------
# get repot functions
def month_range(year: int, month: int):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day

def calculate_level(total_drivers: int):
    if total_drivers >= 200:
        return 3
    elif total_drivers >= 100:
        return 2
    elif total_drivers >= 1:
        return 1
    else:
        return 0
    
# Daily report
@with_db
def get_daily_driver_counts(username: str, db: Session|None=None):
    if db:
        today = date.today()
        count_rows = (
            db.query(Registration.status, func.count(Registration.username))
            .filter(
                Registration.username == username,
                Registration.entry_date == today
            )
            .group_by(Registration.status)
            .all()
        )

        counts_dict = {status: count for status, count in count_rows}

        reactivation = counts_dict.get("Reactivation", 0)
        registration = counts_dict.get("Registration", 0)
        all_drivers = reactivation + registration

        return all_drivers, registration, reactivation
    return 0, 0, 0

# Custom report
@with_db
def get_custom_driver_counts(username: str, first_date: int | date, second_date: int | date, db: Session|None=None):
    if db:
        today = date.today()
        first_date = date(today.year, today.month, first_date)
        second_date = date(today.year, today.month, second_date)

        count_rows = (
            db.query(Registration.status, func.count(Registration.username))
            .filter(
                Registration.username == username,
                Registration.entry_date.between(
                    first_date, 
                    second_date)
            )
            .group_by(Registration.status)
            .all()
        )

        counts_dict = {status: count for status, count in count_rows}

        reactivation = counts_dict.get("Reactivation", 0)
        registration = counts_dict.get("Registration", 0)
        all_drivers = reactivation + registration

        return all_drivers, registration, reactivation
    return 0, 0, 0

# Monthly report
@with_db
def get_monthly_driver_counts(username: str, db: Session|None=None):
    if db:
        today = date.today()
        last_date_of_this_month = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

        if today != last_date_of_this_month:
            if today.month == 1:
                today = date(today.year - 1, 12, 15)
            else:
                today = date(today.year, today.month - 1, 15)
        
        first_date_of_the_month, last_date_of_the_month = month_range(today.year, today.month)
        
        count_rows = (
            db.query(Registration.status, func.count(Registration.username))
            .filter(
                Registration.username == username,
                Registration.entry_date.between(
                    first_date_of_the_month, 
                    last_date_of_the_month)
            )
            .group_by(Registration.status)
            .all()
        )

        counts_dict = {status: count for status, count in count_rows}

        reactivation = counts_dict.get("Reactivation", 0)
        registration = counts_dict.get("Registration", 0)
        all_drivers = reactivation + registration

        return all_drivers, registration, reactivation, first_date_of_the_month
    return 0, 0, 0, 0
            

# Trip success report
@with_db
def get_trip_success(username: str, 
                     today: date | None = None, 
                     first_date: int | None = None, 
                     second_date: int | None = None,
                     db: Session|None=None):
    if db:
        user = db.query(User).filter(User.username == username).first()

        # custom
        if first_date and second_date:
            today = date.today()
            first_day = date(today.year, today.month, first_date)
            second_day = date(today.year, today.month, second_date)

            registration = db.query(Registration).filter(Registration.user == user,
                                                        # Registration.entry_date.month == date.today().month,
                                                        Registration.entry_date.between(first_day, second_day),
                                                        Registration.status == "Registration",
                                                        Registration.trip_no > 0).count()
        
            reactivation = db.query(Registration).filter(Registration.user == user,
                                                        # Registration.entry_date.month == date.today().month,
                                                        Registration.entry_date.between(first_day, second_day),
                                                        Registration.status == "Reactivation",
                                                        Registration.trip_no > 0).count()
            print("custom trip detail")
            return registration, reactivation

        # daily
        if today:
            print(today)
            registration = db.query(Registration).filter(Registration.user == user,
                                                        Registration.entry_date == today,
                                                        Registration.status == "Registration",
                                                        Registration.trip_no > 0).count()
            
            reactivation = db.query(Registration).filter(Registration.user == user,
                                                        Registration.entry_date == today,
                                                        Registration.status == "Reactivation",
                                                        Registration.trip_no > 0).count()
            print("daily trip detail")
            return registration, reactivation
        
        # monthly
        if not today and not first_date and not second_date:
            today = date.today()
            last_day = calendar.monthrange(today.year, today.month)[1]
            if today.day == last_day:
                first_day, last_day = month_range(today.year, today.month)

                registration = db.query(Registration).filter(Registration.user == user,
                                                            Registration.entry_date.between(first_day, last_day),
                                                            Registration.status == "Registration",
                                                            Registration.trip_no > 0).count()
                
                reactivation = db.query(Registration).filter(Registration.user == user,
                                                            Registration.entry_date.between(first_day, last_day),
                                                            Registration.status == "Reactivation",
                                                            Registration.trip_no > 0).count()
                print("monthly trip detail at the end of the month")
                return registration, reactivation  
            
            else:
                if today.month == 1:
                    last_month_day = date(today.year - 1, 12, 15)
                else:
                    last_month_day = date(today.year, today.month - 1, 15)

                first_day, last_day = month_range(last_month_day.year, last_month_day.month)
                

                registration = db.query(Registration).filter(Registration.user == user,
                                                            Registration.entry_date.between(first_day, last_day),
                                                            Registration.status == "Registration",
                                                            Registration.trip_no > 0).count()
                
                reactivation = db.query(Registration).filter(Registration.user == user,
                                                            Registration.entry_date.between(first_day, last_day),
                                                            Registration.status == "Reactivation",
                                                            Registration.trip_no > 0).count()
                print("monthly trip detail of last month")
                return registration, reactivation  
    return 0, 0
