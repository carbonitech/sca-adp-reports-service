import os
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
                company=user[1]
                un=user[2]
                pw=user[3]
                email=user[4]
                last_call = user[6]

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


@adp.route('/users', methods=['GET','POST'])
def register_user():

    if "facebookexternalhit" in str(request.user_agent):
        return Response("Go Away",418)

    if request.method == 'POST':

        company = request.form.get('company', type=str)
        user = request.form.get('user', type=str)
        password = request.form.get('password', type=str)
        email = request.form.get('email', type=str)

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
                with open('./static/schemas.sql','r') as file:
                    conn.execute(file.read())

            conn.execute(
                f"""
                INSERT INTO {TABLE} (company, username, password, email_address, api_key, last_request) 
                VALUES(%s, %s, %s, %s, %s, %s);
                """,
                (company, user, password, email, api_key,datetime.now()-timedelta(seconds=300)))
            resp = emailHelper.send_email([email],"Registration Complete",msg)
            if 200 <= resp.status_code < 299:
                return Response("successfully registered",resp.status_code)
            else:
                return Response("Error occured", resp.status_code)
    
    return render_template('register_user.html')