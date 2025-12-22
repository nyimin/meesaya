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

def save_chat_log(user_id, role, text):
    """
    Saves a message to the database.
    role: 'user' or 'bot'
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO chat_history (user_id, role, message_text)
            VALUES (%s, %s, %s)
        """, (user_id, role, text))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging chat: {e}")