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
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import HTMLResponse
load_dotenv(".env")

app = FastAPI()
airtable = Airtable(os.environ['AIRTABLE_BASE_ID'], os.environ['AIRTABLE_TABLE_NAME'], api_key=os.environ['AIRTABLE_API_KEY'])
email_base_url = os.environ['EMAIL_BASE_URL']
print(email_base_url)
class EmailSchema(BaseModel):
    email: EmailStr
    id: Optional[str]

def send_email(subject, message, to_address):
    print('trying to send email')
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
    print('email sent')
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
    msg = f'<p>Welcome to SmartBids.ai!</p><p>Please click on the following link to verify your email:</p><a href="{email_base_url}/verify_email?token={token}&email={quote(email.email)}">Verify Email</a><p>Thank you,</p><p>SmartBids.ai Team</p>'
    subject = 'Email verification'

    # send the email
    send_email(subject, msg, email.email)

    return {"message": "Verification email sent"}



@app.get("/verify_email", response_class=HTMLResponse)
async def verify_email(token: str, email: str):
    # search for the record with the given email and token
    records = airtable.search('email', email)
    for record in records:
        if record['fields'].get('token') == token:
            # check if the email is already verified
            if record['fields'].get('verified', False):
                return """
                <h1>This email has already been verified!</h1>
                <p>You are fully verified and can now login.</p>
                <a href="https://app.smartbids.ai">Click here to login</a>
                """
            else:
                # if not verified, update the verified field to True
                airtable.update(record['id'], {'verified': True})
                return """
                <h1>Your email has been successfully verified!</h1>
                <p>You are fully verified and can now login.</p>
                <a href="https://app.smartbids.ai">Click here to login</a>
                """

    raise HTTPException(status_code=400, detail="Invalid token or email")


