from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from urllib.parse import quote
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(".env")

app = FastAPI()

# MongoDB setup
mongo_uri = os.environ['MONGO_AUTH']
client = MongoClient(mongo_uri)
db = client['smartbids']
users_collection = db['users']
leads_collection = db['leads']

email_base_url = os.environ['EMAIL_BASE_URL']


class EmailSchema(BaseModel):
    email: EmailStr
    id: Optional[str]


class LeadSchema(BaseModel):
    name: str
    email: EmailStr
    phone: str
    id: Optional[str]


def send_email(subject, message, to_address):
    # Your send_email logic, unchanged from before
    from_address = 'ryan@smartbids.ai'
    password = os.getenv("EMAIL_PASS")
    msg = MIMEMultipart()
    msg['From'] = "SmartBids.ai - Email verification <" + from_address + ">"
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))
    server = smtplib.SMTP_SSL('mail.privateemail.com', 465)
    server.login(from_address, password)
    text = msg.as_string()
    server.sendmail(from_address, to_address, text)
    server.quit()


@app.post("/create_lead")
async def create_lead(lead: LeadSchema):
    token = secrets.token_hex(20)
    existing_lead = leads_collection.find_one({'email': lead.email})

    if existing_lead:
        if existing_lead.get('verified', False):
            return {"message": "Email is already verified"}

        leads_collection.update_one(
            {'_id': existing_lead['_id']},
            {
                "$set": {
                    "name": lead.name,
                    "phone": lead.phone,
                    "token": token,
                    "verified": False
                }
            }
        )
    else:
        leads_collection.insert_one({
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "token": token,
            "verified": False
        })

    # [Rest of your email generation and sending logic]
    msg = f'<p>Welcome to SmartBids.ai, {lead.name}!</p><p>Please click on the following link to verify your email:</p><a href="{email_base_url}/verify_client?token={token}&email={quote(lead.email)}&phone={quote(lead.phone)}&db_type=leads">Verify Email</a><p>Thank you,</p><p>SmartBids.ai Team</p>'
    subject = 'Email verification'
    send_email(subject, msg, lead.email)

    return {"message": "Verification email sent"}


@app.post("/send_verification")
async def send_verification(email: EmailSchema):
    token = secrets.token_hex(20)
    existing_user = users_collection.find_one({'email': email.email})

    if existing_user:
        if existing_user.get('verified', False):
            return {"message": "Email is already verified"}

        users_collection.update_one(
            {'_id': existing_user['_id']},
            {
                "$set": {
                    "token": token,
                    "verified": False
                }
            }
        )
    else:
        users_collection.insert_one({
            "email": email.email,
            "token": token,
            "verified": False
        })

    # [Rest of your email generation and sending logic]
    msg = f'<p>Welcome to SmartBids.ai!</p><p>Please click on the following link to verify your email:</p><a href="{email_base_url}/verify_client?token={token}&email={quote(email.email)}&">Verify Email</a><p>Thank you,</p><p>SmartBids.ai Team</p>'
    subject = 'Email verification'
    send_email(subject, msg, email.email)

    return {"message": "Verification email sent"}


@app.get("/verify_client", response_class=HTMLResponse)
async def verify_client(token: str, email: str, phone: Optional[str] = None, db_type: str = "users"):
    collection = users_collection if db_type == "users" else leads_collection
    record = collection.find_one({'email': email, 'token': token})

    if record:
        if record.get('verified', False):
            return """
            <h1>This email has already been verified!</h1>
            <p>You are fully verified and can now login.</p>
            <a href="https://app.smartbids.ai">Click here to login</a>
            """
        else:
            collection.update_one(
                {'_id': record['_id']},
                {"$set": {'verified': True}}
            )
            return """
            <h1>Your email has been successfully verified!</h1>
            <p>You are fully verified and can now login.</p>
            <a href="https://app.smartbids.ai">Click here to login</a>
            """

    raise HTTPException(status_code=400, detail="Invalid token or email")

