# connection.py
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Read environment variables
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Construct the database URL
database_url = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

try:
    # Connect to the database
    client = psycopg2.connect(database_url)
    db = client.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # ========== CREATE TABLE ==========

    table_name = "driver"

    def create_table():
        create_driver_query = """ 
        CREATE TABLE IF NOT EXISTS driver (
        id SERIAL PRIMARY KEY,
        no VARCHAR(40) NOT NULL,
        name VARCHAR(40) NOT NULL,
        loc_25 VARCHAR(40) NOT NULL,
        lat VARCHAR(40) NOT NULL,
        lon VARCHAR(40) NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.execute(create_driver_query)
        client.commit()
        print("Table created successfully in PostgreSQL ")

    # ========== CHECK IF TABLE EXISTS ==========

    def check_if_exists(table_name):
        try:
            db.execute("""
                        SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_catalog = 'postgres'
                        AND table_schema = 'public'
                        AND table_name = %s
                        );
                    """, (table_name,))
            return db.fetchone()[0]
        except psycopg2.Error as e:
            print("Error: ", e)
            return False

    print(f"Table {table_name} exists: {check_if_exists(table_name)}")

    if not check_if_exists(table_name):
        create_table()
    else:
        print("Table already exists")

    print(f"Table {table_name} exists: {check_if_exists(table_name)}")

except psycopg2.Error as e:
    print("Error connecting to the database:", e)
