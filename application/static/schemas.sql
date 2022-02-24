CREATE TABLE adp_users (
    id SERIAL PRIMARY KEY,
    company text,
    username text,
    password text,
    email_address text,
    api_key text,
    last_request timestamp
);