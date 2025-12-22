import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using the DATABASE_URL environment variable.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    
    conn = psycopg2.connect(db_url)
    return conn