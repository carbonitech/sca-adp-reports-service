import os
import pandas
from datetime import datetime, timedelta
from hashlib import sha256
from dotenv import load_dotenv
from rq import Queue
from flask import render_template, request, Response, Blueprint
from sqlalchemy import create_engine
from application import adp_retrieval, emailHelper
from worker import conn as redis_conn

load_dotenv()
DATABASE = os.environ.get('DATABASE_URL')
DATABASE = DATABASE.replace("postgres://","postgresql://") # fixes heroku DATABASE_URL
TABLE = os.environ.get('USERS_TABLE')

adp = Blueprint('adp', __name__)
q = Queue(connection=redis_conn)

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
            return Response("No users have been initialized. Register the first user.", 404)
        else:
            user = conn.execute(f"SELECT * FROM {TABLE} WHERE api_key = %s;", [key]).fetchone()
            if user:
                company=user[0]
                un=user[1]
                pw=user[2]
                email=user[3]
                last_call = user[5]

                now = datetime.now()
                if last_call:
                    if (now-last_call).seconds <= 120:
                        return Response(f"Last request was at {last_call}. Please wait a few minutes before sending another request.",200)

                q.enqueue(
                    adp_retrieval.run_service,
                    company=company,
                    user=un,
                    password=pw,
                    email=email
                )
                conn.execute(f"UPDATE {TABLE} SET last_request = %s WHERE api_key = %s",(now, key))

            return Response(f"Request received. Check your email {email} after a few moments.",200)


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
        msg = f"""
            <p>Successfully Registered.</p>
            <p>Use this link to have the ADP reports automatically emailed to you upon request</p>
            <p style="margin-left: 15px">https://adp-report-api.herokuapp.com/adp-reports?api-key={api_key}</p>
            """
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
                'api_key': [api_key],
                'last_request': datetime.now()-timedelta(seconds=300)}
                )
            first_user.to_sql(TABLE, conn, index=False)
            resp = emailHelper.send_email([email],"Registration Complete",msg)
            if 200 <= resp < 299:
                return Response("Database initialized and first user created", resp)
            else:
                return Response("Error occured", resp)
        else:
            conn.execute(
                f"""
                INSERT INTO {TABLE} (company, username, password, email_address, api_key, last_request) 
                VALUES(%s, %s, %s, %s, %s, %s);
                """,
                (company, user, password, email, api_key,datetime.now()-timedelta(seconds=300)))
            resp = emailHelper.send_email([email],"Registration Complete",msg)
            if 200 <= resp < 299:
                return Response("successfully registered",resp)
            else:
                return Response("Error occured", resp)