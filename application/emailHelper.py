"""subclass EmailMessage to simplify file attachments and building/sending an email"""
import os
from typing import List
import mimetypes
import base64
import requests
from dotenv import load_dotenv
import application.auth.auth_confidential_client_secret as azure_auth

load_dotenv()

LOGIN_EMAIL_ADDRESS = os.environ.get("LOGIN_EMAIL_ADDRESS")
LOGIN_EMAIL_PASSWORD = os.environ.get("LOGIN_EMAIL_PASSWORD")
SENDER_EMAIL_ADDRESS = os.environ.get("SENDER_EMAIL_ADDRESS")
SENDER_USER_ID = os.environ.get("SENDER_USER_ID")

def send_email(recipients: list, subject: str, message: str=None, attachments: List[tuple]=None):
    """ Send email as the Carboni Tech Services user using Microsoft Graph API"""

    recipients_formatted = [{"emailAddress": {"address": recipient}} for recipient in recipients]
    sendmail_request_body = {
        "subject": f"{subject}",
        "toRecipients": recipients_formatted,
        "from": {
                "emailAddress": {
                    "address": f"{SENDER_EMAIL_ADDRESS}"
                }
        },
        "body": {
            "contentType": "HTML",
            "content": f"{message}"
        }
    }
    if attachments:
        attachments_formatted = [
            {                
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"{name}",
                "contentType": f"{mimetypes.guess_type(name)[0] or 'application/octet-stream'}",
                "contentBytes": f"{base64.b64encode(content).decode('utf-8')}" # why is this encode -> decode necessary??
            } for name, content in attachments
        ]
        sendmail_request_body.update({"attachments": attachments_formatted})

    api_url = f"https://graph.microsoft.com/v1.0/users/{SENDER_USER_ID}/sendMail"
    headers = {
        "Content-type": "application/json",
        "Authorization": 'Bearer ' + azure_auth.get_auth_token_for_ms_graph()}
    r = requests.post(api_url, headers=headers, json={"message": sendmail_request_body})

    return r