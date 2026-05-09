import sqlite3
import random

# --- CONFIGURATION ---
NEIGHBORHOODS = ["Indiranagar", "Koramangala", "HSR Layout", "Whitefield", "Hebbal", "Jayanagar", "Mathikere", "Electronic City"]
WATER_SOURCES = ["Cauvery Only", "Borewell + Tanker", "Dual Source (Cauvery/Bore)]"]
DOC_TYPES = ["A-Khata", "B-Khata", "E-Khata"]
LIFESTYLE_TAGS = ["Veg-Only", "No Pets", "WFH-Ready", "Near Metro", "Bachelors OK", "Family Only", "Late Night OK"]
OWNERS = ["Priya S.", "Anish K.", "Vikram Rao", "Sanjay Dutt", "Meera Nair", "Rahul B.", "Kavitha M.", "Aditi G."]

def generate_bulk_data(count=100):
    conn = sqlite3.connect('harbr_seed.db')
    cursor = conn.cursor()

    # Clear existing
    cursor.execute("DELETE FROM mock_land_records")
    
    records = []
    for i in range(count):
        ulpin = f"10002000{random.randint(100000, 999999)}"
        owner = random.choice(OWNERS)
        area = random.choice([600, 1200, 1500, 2400])
        city = random.choice(NEIGHBORHOODS)
        # 15% of records are "Disputed" to test your Shield Agent
        status = "Disputed" if random.random() < 0.15 else "Clear"
        
        records.append((ulpin, owner, area, city, status))

    cursor.executemany("INSERT INTO mock_land_records VALUES (?,?,?,?,?)", records)
    conn.commit()
    conn.close()
    print(f"✅ Successfully seeded {count} Government Land Records.")

if __name__ == "__main__":
    generate_bulk_data(100)