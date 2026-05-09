import sqlite3

# This creates a file named 'harbr_vault.db' in your folder automatically
def init_db():
    conn = sqlite3.connect('harbr_vault.db')
    cursor = conn.cursor()
    
    # Create the Listings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ulpin TEXT,
            rent INTEGER,
            deposit INTEGER,
            dietary_pref TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_listing(ulpin, rent, deposit, dietary):
    conn = sqlite3.connect('harbr_vault.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO listings (ulpin, rent, deposit, dietary_pref) VALUES (?, ?, ?, ?)', 
                   (ulpin, rent, deposit, dietary))
    conn.commit()
    conn.close()
import redis
import os
from dotenv import load_dotenv

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

cache = None
if REDIS_URL:
    try:
        cache = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print(f"Redis initialization failed: {e}")

def cache_harmony_score(tenant_id, house_id, score):
    if cache:
        cache.setex(f"harmony:{tenant_id}:{house_id}", 600, score)

def get_cached_score(tenant_id, house_id):
    if cache:
        return cache.get(f"harmony:{tenant_id}:{house_id}")
    return None
