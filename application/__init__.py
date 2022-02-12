import os
import pandas
from hashlib import sha256
from flask import Flask, Response, request
from application import adp_retrieval, emailHelper
from sqlalchemy import create_engine


DATABASE = os.environ.get('DATABASE_URL').replace("postgres://","postgresql://")
TABLE = 'users'

def create_app():

    app = Flask(__name__)

    @app.route('/adp-reports')
    def request_report():
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
                        report_bytes: bytes = adp_retrieval.fetch_data(
                            company=user[0],
                            user=user[1],
                            password=user[2]
                        )
                    except adp_retrieval.LoginError:
                        emailHelper.send_email(
                            user[3],
                            "Failed to Login",
                            "Failed to log-in to ADPnow.com with your credentials",
                            "",""
                        )
                        return Response(None,200)
                    else:
                        emailHelper.send_email(
                            user[3],
                            "ADP Open Order & Shipments",
                            "","","",
                            (report_bytes, "ADP Report.xls")
                        )
                        return Response(None,200)
                else:
                    return Response("user not found", 200)


    @app.route('/adp-reports/new_user')
    def register_user():
        company = request.args.get('company', type=str)
        user = request.args.get('user', type=str)
        password = request.args.get('password', type=str)
        email = request.args.get('email', type=str)

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
                <p>Bookmark this link and click it when you want your report --> https://adpreports-heroku.com/adp-reports?api_key=<b><u>{api_key}</u></b>
                """
                emailHelper.send_email(email,"Resgistration Complete",msg,"","")
                return Response("successfully registered",200)

    return app