import os
import pandas
from datetime import datetime
from hashlib import sha256
from flask import render_template, request, Response, Blueprint
from sqlalchemy import create_engine
from application import adp_retrieval, emailHelper

DATABASE = os.environ.get('DATABASE_URL').replace("postgres://","postgresql://") # corrects for heroku DATABASE URL
TABLE = 'users'

adp = Blueprint('adp', __name__)

@adp.route('/adp-reports')
def request_report():

    if "facebookexternalhit" in str(request.user_agent):
        return Response("Go Away",418)
        
    key = request.args.get('api-key')
    if not key:
        return Response("Enter your api key into the url set to the parameter 'api-key'",200)
    engine = create_engine(DATABASE)
    with engine.connect() as conn:
        db_tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """).fetchall()
        db_tables_namelist = [tab[0] for tab in db_tables]
        if TABLE not in db_tables_namelist:
            return Response("No users have been initialized. Register the first user.", 500)
        else:
            user = conn.execute(f"SELECT * FROM {TABLE} WHERE api_key = %s;", [key]).fetchone()
            if user:
                try:
                    last_call = user[5]
                    now = datetime.now()
                    if last_call:
                        if (now-last_call).seconds <= 120:
                            return Response(f"Last request was at {user[5]}. Please wait a few minutes before sending another request.",200)
                    report_bytes: bytes = adp_retrieval.fetch_data(
                        company=user[0],
                        user=user[1],
                        password=user[2]
                    )
                except adp_retrieval.LoginError:
                    emailHelper.send_email(
                        user[3],
                        "Failed to Login",
                        "Failed to log-in to ADPinside.com with your credentials",
                        "",""
                    )
                    return Response("Failed to log in to ADPinside.com",200)
                else:
                    emailHelper.send_email(
                        user[3],
                        "ADP Open Order & Shipments",
                        "","","",
                        (report_bytes, "ADP Report.xls")
                    )
                    conn.execute("UPDATE users SET last_request = %s WHERE api_key = %s",(now, key))
                    return Response(f"Successfully sent report. Check your email address {user[3]}",200)
            else:
                return Response(f"User with api key {key} not found", 200)


@adp.route('/adp-reports/new_user')
def register_user():

    if "facebookexternalhit" in str(request.user_agent):
        return Response("Go Away",418)

    company = request.args.get('company', type=str)
    user = request.args.get('user', type=str)
    password = request.args.get('password', type=str)
    email = request.args.get('email', type=str)

    if not company or not user or not password or not email:
        return render_template('register_user.html')

    engine = create_engine(DATABASE)
    with engine.connect() as conn:
        api_key = sha256((company+user+email+password).encode()).hexdigest()
        db_tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """).fetchall()
        db_tables_namelist = [tab[0] for tab in db_tables]
        if TABLE not in db_tables_namelist:
            first_user = pandas.DataFrame(
                {'company': [company],
                'username': [user],
                'password': [password],
                'email_address': [email],
                'api_key': [api_key]}
                )
            first_user.to_sql(TABLE, conn, index=False)
            emailHelper.send_email(email,"Resgistration Complete",msg,"","")
            return Response("Database initialized and first user created", 200)
        else:
            conn.execute(
                f"""
                INSERT INTO {TABLE} (company, username, password, email_address, api_key) 
                VALUES(%s, %s, %s, %s, %s);
                """,
                (company, user, password, email, api_key))
            msg = f"""
            <p>Successfully Registered.</p>
            <p>Use this key to have the ADP reports automatically emailed to you upon request</p>
            <p style="margin-left: 15px">{api_key}</p>
            <p>Bookmark this link and click it when you want your report --> https://adp-report-api.herokuapp.com/adp-reports?api-key=<b><u>{api_key}</u></b>
            """
            emailHelper.send_email(email,"Resgistration Complete",msg,"","")
            return Response("successfully registered",200)