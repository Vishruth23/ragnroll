from snowflake.snowpark import Session
from snowflake.cortex import Summarize, Translate, Sentiment, Complete
from dotenv import load_dotenv
import os


def connect():
    load_dotenv()
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    database = os.getenv("SNOWFLAKE_DATABASE")
    connection_parameters = {
        "account": account,
        "user": user,
        "password": password,
        "warehouse": warehouse,
        "database": database
    }
    session=Session.builder.configs(connection_parameters).create()
    return session





if __name__ == "__main__":
    session = connect()
    res=session.sql("USE SCHEMA CORTEX;").collect()
    res=session.sql("SELECT SNOWFLAKE.CORTEX.SENTIMENT('I am happy');")
    print(res.collect())