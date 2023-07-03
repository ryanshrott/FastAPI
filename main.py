from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from urllib.parse import quote
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from airtable import Airtable
import secrets
import os
from dotenv import load_dotenv

load_dotenv(".env")

app = FastAPI()
airtable = Airtable(os.environ['AIRTABLE_BASE_ID'], os.environ['AIRTABLE_TABLE_NAME'], api_key=os.environ['AIRTABLE_API_KEY'])

class EmailSchema(BaseModel):
    email: EmailStr
    id: Optional[str]

def send_email(subject, message, to_address):
    print('trying to send email')
    from_address = 'ryan@smartbids.ai'
    password = os.getenv("EMAIL_PASS")
    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))
    server = smtplib.SMTP_SSL('mail.privateemail.com', 465)
    server.login(from_address, password)
    text = msg.as_string()
    server.sendmail(from_address, to_address, text)
    server.quit()

@app.post("/send_verification")
async def send_verification(email: EmailSchema):
    # generate a random token
    token = secrets.token_hex(20)

    # search for the record with the given email
    records = airtable.search('email', email.email)

    if records:
        # if a record exists
        record = records[0]
        if record['fields'].get('verified', False):
            # if the record is already verified, no need to send another email
            return {"message": "Email is already verified"}

        # update the existing record with a new token and set verified to False
        airtable.update(record['id'], {
            "token": token,
            "verified": False
        })
    else:
        # if no record exists, create a new one
        airtable.insert({
            "email": email.email,
            "token": token,
            "verified": False
        })

    # generate the email content
    msg = f'Please click on the following link to verify your email:\nhttp://localhost:8001/verify_email?token={token}&email={quote(email.email)}'
    subject = 'Email verification'

    # send the email
    send_email(subject, msg, email.email)

    return {"message": "Verification email sent"}



@app.get("/verify_email")
async def verify_email(token: str, email: str):
    # search for the record with the given email and token
    records = airtable.search('email', email)
    for record in records:
        if record['fields'].get('token') == token:
            # update the verified field to True
            airtable.update(record['id'], {'verified': True})
            return {"message": "Email verified"}

    raise HTTPException(status_code=400, detail="Invalid token or email")
