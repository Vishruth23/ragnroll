import snowflake.connector
from loaddotenv import load_dotenv
import os

def connect():
    load_dotenv()
    conn = snowflake.connector.connect(
        user = os.getenv('SNOWFLAKE_USER'),
        password = os.getenv('SNOWFLAKE_PASSWORD'),
        account = os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse = os.getenv('SNOWFLAKE_WAREHOUSE'),
        database = os.getenv('SNOWFLAKE_DATABASE'),)
    return conn