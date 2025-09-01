from sqlalchemy import create_engine, Column, String, Date, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import date, datetime

import schedule
import time

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

# SCOPES = [
#     "https://www.googleapis.com/auth/spreadsheets",
#     "https://www.googleapis.com/auth/drive"
# ]
# def setup_spreadsheet():
#     creds = Credentials.from_service_account_file(filename="littlesalesreport.json", scopes=SCOPES)
#     client = gspread.authorize(creds)
#     spreadsheet = client.open("driver-approval")
#     sheet = spreadsheet.worksheet("BotReport")
#     return sheet

# def fetch_all_records():
#     sheet = setup_spreadsheet()
#     records = sheet.get_all_records()
#     return records

def update_user(db: Session, records: list):
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
        

def update_registration(db: Session, records: list):
    for record in records:
        registration = db.query(Registration).filter(Registration.driver_phone == record["driver_phone"]).first()
        if registration:
            registration.status = record["status"]
            registration.entry_date = datetime.strptime(record["date"], "%m/%d/%Y").date()
            # registration.driver_phone = record["driver_phone"]
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


def authenticate(db: Session, username: str):
    user = db.query(User).filter(User.username==username).first()
    if user:
        return True
    return False

# def job():
#     db = next(get_db())
#     records = fetch_all_records()
#     update_user(db, records)
#     update_registration(db, records)
#     db.close()
#     print("Database Updated")

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

def get_number_of_all_drivers(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    return db.query(Registration).filter(Registration.user == user, 
                                         Registration.entry_date == today).count()

def get_number_of_reactivation(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    return db.query(Registration).filter(Registration.user == user, 
                                         Registration.entry_date == today,
                                         Registration.status == "Reactivation").count()
    
def get_number_of_registration(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    return db.query(Registration).filter(Registration.user == user, 
                                         Registration.entry_date == today,
                                         Registration.status == "Registration").count()

def get_monthly_number_of_all_drivers(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user).all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.month == today.month:
                counter += 1
    
    return counter


def get_monthly_number_of_reactivation(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user, 
                                         Registration.status == "Reactivation").all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.month == today.month:
                counter += 1
    
    return counter
    
def get_monthly_number_of_registration(db: Session, username: str, today: date):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user, 
                                         Registration.status == "Registration").all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.month == today.month:
                counter += 1
    
    return counter

def calculate_level(total_drivers: int):
    if total_drivers >= 200:
        return 3
    elif total_drivers >= 100:
        return 2
    elif total_drivers >= 1:
        return 1
    else:
        return 0
    
# Custom
def get_custom_number_of_all_drivers(db: Session, username: str, today: date, first_date: int, second_date: int):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user).all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.day >= first_date and r.entry_date.day <= second_date:
                counter += 1
    
    return counter


def get_custom_number_of_reactivation(db: Session, username: str, today: date, first_date: int, second_date: int):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user, 
                                         Registration.status == "Reactivation").all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.day >= first_date and r.entry_date.day <= second_date:
                counter += 1
    
    return counter
    
def get_custom_number_of_registration(db: Session, username: str, today: date, first_date: int, second_date: int):
    user = db.query(User).filter(User.username == username).first()
    registrations = db.query(Registration).filter(Registration.user == user, 
                                         Registration.status == "Registration").all()
    counter = 0
    if registrations:
        for r in registrations:
            if r.entry_date.day >= first_date and r.entry_date.day <= second_date:
                counter += 1
    
    return counter