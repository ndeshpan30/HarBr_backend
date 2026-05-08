import sqlite3
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("--- Step 1: Starting SQLite Setup ---")

def setup_sqlite():
    try:
        conn = sqlite3.connect('harbr_seed.db')
        cursor = conn.cursor()
        cursor.executescript("""
        DROP TABLE IF EXISTS mock_land_records;
        DROP TABLE IF EXISTS mock_blacklist;
        DROP TABLE IF EXISTS pmay_subsidy_table;
        DROP TABLE IF EXISTS mock_listings;

        CREATE TABLE mock_land_records (ulpin TEXT PRIMARY KEY, owner_name TEXT, area_sqft INTEGER, city TEXT, status TEXT);
        CREATE TABLE mock_blacklist (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_name TEXT, reason TEXT, flagged_date TEXT);
        CREATE TABLE pmay_subsidy_table (id INTEGER PRIMARY KEY AUTOINCREMENT, income_bracket TEXT, annual_income_max INTEGER, monthly_subsidy INTEGER);
        CREATE TABLE mock_listings (id INTEGER PRIMARY KEY AUTOINCREMENT, ulpin TEXT, owner_name TEXT, city TEXT, rent INTEGER, deposit INTEGER, lifestyle_tags TEXT);
        """)

        cursor.executemany("INSERT INTO mock_land_records VALUES (?,?,?,?,?)", [
            ('10002000300044', 'Aravind Rao', 1200, 'Bengaluru', 'Clear'),
            ('10002000300055', 'Suresh M.', 1500, 'Bengaluru', 'Clear'),
            ('10002000300077', 'Rajesh Kumar', 2400, 'Delhi', 'Dispute')
        ])
        conn.commit()
        conn.close()
        print("✅ Checkpoint: SQLite Seeding Complete.")
    except Exception as e:
        print(f"❌ SQLite Error: {e}")

async def setup_postgres():
    print("--- Step 2: Starting Neon Postgres Setup ---")
    pg_url = os.getenv("POSTGRES_URL")
    
    if not pg_url:
        print("❌ ERROR: POSTGRES_URL is missing from your .env file!")
        return

    try:
        engine = create_async_engine(pg_url, echo=False)
        
        commands = [
            "CREATE TABLE IF NOT EXISTS owners (id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, contact VARCHAR(80), is_verified BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW());",
            "CREATE TABLE IF NOT EXISTS properties (id SERIAL PRIMARY KEY, ulpin VARCHAR(14) UNIQUE NOT NULL, owner_id INTEGER REFERENCES owners(id), area_sqft INTEGER, city VARCHAR(80), land_status VARCHAR(20), created_at TIMESTAMP DEFAULT NOW());",
            "CREATE TABLE IF NOT EXISTS listings (id SERIAL PRIMARY KEY, property_id INTEGER REFERENCES properties(id), owner_id INTEGER REFERENCES owners(id), rent INTEGER NOT NULL, deposit INTEGER NOT NULL, lifestyle_tags TEXT, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW());",
            "CREATE TABLE IF NOT EXISTS tenants (id SERIAL PRIMARY KEY, name VARCHAR(120), annual_income INTEGER, income_bracket VARCHAR(20), lifestyle_tags TEXT, created_at TIMESTAMP DEFAULT NOW());",
            "CREATE TABLE IF NOT EXISTS agreements (id SERIAL PRIMARY KEY, listing_id INTEGER REFERENCES listings(id), owner_id INTEGER REFERENCES owners(id), tenant_id INTEGER REFERENCES tenants(id), agreement_text TEXT, status VARCHAR(20) DEFAULT 'Draft', created_at TIMESTAMP DEFAULT NOW());"
        ]

        async with engine.begin() as conn:
            for cmd in commands:
                await conn.execute(text(cmd))
        
        print("✅ Checkpoint: PostgreSQL Schema Ready.")
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Postgres Error: {e}")

if __name__ == "__main__":
    setup_sqlite()
    asyncio.run(setup_postgres())
    print("--- ALL DONE! ---")