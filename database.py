import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# Railway/Postgres URL
DB_URL = os.environ.get("DATABASE_URL")

# Initialize Connection Pool (Min 1, Max 10 connections)
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DB_URL)
    if connection_pool:
        print("✅ Database connection pool created successfully")
except Exception as e:
    print(f"❌ Error creating connection pool: {e}")

@contextmanager
def get_db_connection():
    """Yields a connection from the pool and ensures it's returned."""
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)

def save_chat_log(user_id, role, message):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_history (user_id, role, message_text) VALUES (%s, %s, %s)",
                    (user_id, role, message)
                )
            conn.commit()
    except Exception as e:
        print(f"Failed to save chat log: {e}")

def get_recent_history(user_id, limit=6):
    """Fetches context for the AI so it remembers the conversation."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT role, message_text FROM chat_history 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC LIMIT %s
                """, (user_id, limit))
                rows = cur.fetchall()
        
        # Reverse to ensure chronological order (Oldest -> Newest)
        history = [{"role": row[0], "content": row[1]} for row in rows[::-1]]
        return history
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []