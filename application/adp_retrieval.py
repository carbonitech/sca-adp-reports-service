import traceback
import requests
import json
import os
from bs4 import BeautifulSoup
from application import emailHelper, formatting

_HERE = os.path.dirname(__file__)

with open(os.path.join(_HERE,'./config.json'),'r') as config_file:
    CONFIGS = json.load(config_file)

URL_LOGIN, URL_A, URL_B, URL_C = CONFIGS["URLS"].values()

class LoginError(Exception):
    pass

def fetch_data(**kwargs) -> bytes:
    company = kwargs['company']
    user = kwargs['user']
    password = kwargs['password']
    
    with requests.Session() as session:

        session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0"}
        )

        payload_login = {
            "login_submit": "on",
            "login_do_redirect": "1",
            "no_cert_storing": "on",
            "lennox_company": f"{company}",
            "j_user": f"{company}.{user}",
            "j_authscheme": "default",
            "lennox_uid": f"{user}",
            "j_password": f"{password}",
            "saveid": "on",
            "j_authscheme": "ADP_Auth"
        }

        payload_a = {
            "NavigationTarget": "navurl://981bf7b1999315eef10dc916d4220d96",
            "LightDTNKnobID": "1705057238",
            "ClientWindowID": "WID1640133263081",
            "$Roundtrip": "true",
            "$DebugAction": "null"
            }

        # get logged in
        resp = session.post(URL_LOGIN, data=payload_login)
        if BeautifulSoup(resp.text, "html.parser").find("span",string="User authentication failed"):
            raise LoginError("Authentication failed. Check credentials and try again")

        # get page with body values for next request
        resp = session.post(URL_A, data=payload_a)

        # find values and build next payload
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form",{"id": "form_Redirect_9223372035027316663"}).find_all("input")
        payload_b = {child['name']:child['value'] for child in form}

        # send request with new payload
        resp = session.post(URL_B, data=payload_b)

        # find values and build next payload
        soup = BeautifulSoup(resp.text, "html.parser")
        names_to_find =["sap-ext-sid","sap-wd-cltwndid","sap-wd-norefresh","sap-wd-secure-id"]
        payload_c = {name:soup.find("input", {"name":name})["value"] for name in names_to_find}
        payload_c.update({"SAPEVENTQUEUE":"Button_Press\ue002Id\ue004aaaa.SalesmanReportCompView.btnGenerateExcel\ue003\ue002ClientAction\ue004submit\ue003\ue002urEventName\ue004BUTTONCLICK\ue003\ue001Form_Request\ue002Id\ue004...form\ue005Async\ue004false\ue005FocusInfo\ue004@{\"sFocussedId\": \"aaaa.SalesmanReportCompView.btnGenerateExcel\"}\ue005Hash\ue004\ue005DomChanged\ue004false\ue005IsDirty\ue004false\ue003\ue002EnqueueCardinality\ue004single\ue003\ue002\ue003"})

        # send request with new payload
        resp = session.post(URL_C, data=payload_c)

        # remove unusual tags so BS can parse the html
        cleaned = resp.text.replace("<![CDATA[","").replace("]]>","").replace("<initialize-ids>","") \
            .replace("</initialize-ids>","").replace("<script-call>","").replace("<\script-call>","")

        # get final download link
        download_link = BeautifulSoup(cleaned,'html.parser').find('a')['href']
        
        # get data
        resp = session.get(download_link.replace("../../", "https://adpinside.com/webdynpro/resources/"))

        return resp.content


def run_service(**kwargs) -> None:
    email = kwargs.get('email')
    try:
        report_bytes: bytes = fetch_data(
            company=kwargs.get('company'),
            user=kwargs.get('user'),
            password=kwargs.get('password')
        )
    except LoginError:
        emailHelper.send_email(
            [email],
            "Failed to Login to ADPinside.com",
            "Failed to login with credentials"
        )
    except Exception as e:
        emailHelper.send_email(
            ["jcarboni@shupecarboni.com"],
            "Error occurred in adp-report-api",
            traceback.format_exc(e),
        )
    else:
        emailHelper.send_email(
            [email],
            "ADP Open Orders & Shipments",
            attachments=[("ADP Report.xlsx",formatting.format_tables(report_bytes))]
        )
