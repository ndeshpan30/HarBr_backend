import sqlite3
import random
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import difflib

app = FastAPI(title="HarBr v2.0")

def string_similarity(s1: str, s2: str) -> float:
    return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

class PropertyListing(BaseModel):
    ulpin: str
    owner_name: str
    city: str
    bhk: int
    area_sqft: int
    rent: int
    deposit: int
    floor_info: str
    lift: bool
    transport: List[float] # [metro_km, bus_km]
    dietary_tags: List[str]
    pet_policy: str
    utilities: List[str]
    amenities: List[str]
    doc_tags: List[str]
    water_tags: List[str]
    commute_tags: List[str]
    furnishing: str
    facing: str
    wfh_friendly: bool
    pet_friendly: bool

class TenantProfile(BaseModel):
    rent_min: int
    rent_max: int
    dietary_pref: List[str]
    pet_pref: str
    utilities_pref: List[str]
    floor_pref: List[str]
    transport_pref: List[str]
    weights: Dict[str, int]

class ShieldRequest(BaseModel):
    ulpin: str
    owner_name: str
    rent: int
    deposit: int
    doc_tags: List[str]

def generate_bulk_listings(count=100) -> List[dict]:
    listings = []
    neighborhoods = ["Indiranagar", "HSR Layout", "Whitefield", "Mathikere", "Hebbal"]
    dietary_options = ['Veg-Only', 'Non-Veg OK', 'Vegan', 'No Alcohol/Smoking']
    pet_options = ['No Pets', 'Small Pets Only', 'All Pets Welcome']
    utility_options = ['Cauvery Water', 'Borewell', 'Power Backup', 'Piped Gas', 'EV Charging']
    amenity_options = ['Gym', 'Clubhouse', '24/7 Security', 'Covered Parking']
    seeded_owners = ['Rajesh Kumar', 'Aravind Rao']
    other_owners = ['Suresh M.', 'Priya S.', 'Vikram Rao', 'Sanjay Dutt', 'Meera Nair', 'Aditi G.']
    
    for i in range(count):
        is_seeded = random.random() < 0.1
        owner_name = random.choice(seeded_owners) if is_seeded else random.choice(other_owners)
        rent = random.randint(15000, 85000)
        deposit = rent * random.choice([5, 10])
        doc_val = random.choice(['A-Khata', 'B-Khata', 'Disputed'])
        
        listings.append({
            "ulpin": f"10002000{random.randint(100000, 999999)}",
            "owner_name": owner_name,
            "city": random.choice(neighborhoods),
            "bhk": random.choice([1, 2, 3, 4]),
            "area_sqft": random.randint(500, 2400),
            "rent": rent,
            "deposit": deposit,
            "floor_info": random.choice(['Ground Floor', '2nd of 4 floors', '5th of 10 floors', 'Penthouse']),
            "lift": random.choice([True, False]),
            "transport": [round(random.uniform(0.1, 5.0), 1), round(random.uniform(0.1, 2.0), 1)],
            "dietary_tags": random.sample(dietary_options, random.randint(1, 2)),
            "pet_policy": random.choice(pet_options),
            "utilities": random.sample(utility_options, random.randint(1, 3)),
            "amenities": random.sample(amenity_options, random.randint(1, 3)),
            "doc_tags": [doc_val] if doc_val != 'Disputed' else [],
            "water_tags": ["Cauvery Connection"] if "Cauvery Water" in utility_options else ["Borewell"],
            "commute_tags": [],
            "furnishing": random.choice(["Fully Furnished", "Semi Furnished", "Unfurnished"]),
            "facing": random.choice(["North-East", "East", "Vastu-Compliant", "Other"]),
            "wfh_friendly": True,
            "pet_friendly": True
        })
    return listings

LISTINGS = generate_bulk_listings(100)

def get_legal_record(ulpin: str):
    try:
        conn = sqlite3.connect('harbr_seed.db')
        cursor = conn.cursor()
        cursor.execute("SELECT owner_name, status FROM mock_land_records WHERE ulpin=?", (ulpin,))
        row = cursor.fetchone()
        conn.close()
        if row: return {"owner_name": row[0], "status": row[1]}
    except Exception as e:
        print(f"SQLite Error: {e}")
    return None

@app.post("/shield/audit")
def shield_audit(req: ShieldRequest):
    shield_score = 0.0
    if req.deposit > (req.rent * 10):
        return {"legal": False, "status": "High Initial Capital", "message": f"Deposit is {req.deposit/req.rent:.1f}x rent!", "shield_score": shield_score}
    elif req.deposit > (req.rent * 5):
        msg_prefix = "Deposit > 5x rent. "
    else:
        msg_prefix = ""
        
    record = get_legal_record(req.ulpin)
    if not record:
        return {"legal": True, "status": "Unverified", "message": msg_prefix + "ULPIN not found.", "shield_score": shield_score}
    
    is_a_khata = "A-Khata" in req.doc_tags
    if record["status"] != "Clear":
        return {"legal": False, "status": "Dispute Warning", "message": "Dispute detected!", "shield_score": shield_score}
    else:
        if is_a_khata: shield_score = 1.0 
            
    similarity = string_similarity(req.owner_name, record["owner_name"])
    if similarity >= 0.9:
        return {"legal": True, "status": "Shield Certified", "message": f"{msg_prefix}Verified! (Score: {shield_score})", "shield_score": shield_score}
    else:
        return {"legal": True, "status": "Audit Pending", "message": f"{msg_prefix}Identity pending. (Score: {shield_score})", "shield_score": shield_score}

@app.post("/matcher/calculate")
def matcher_calculate(req: TenantProfile):
    matches = []
    
    w_budget = req.weights.get("budget", 0)
    w_diet = req.weights.get("diet", 0)
    w_pets = req.weights.get("pets", 0)
    
    total_weight = w_budget + w_diet + w_pets
    if total_weight == 0: total_weight = 1
    
    for lst in LISTINGS:
        effective_rent = lst["rent"]
        
        is_dealbreaker = False
        
        # Budget Check
        if req.rent_min <= effective_rent <= req.rent_max:
            c_budget = 1.0
        elif effective_rent > req.rent_max:
            c_budget = max(0.0, 1.0 - ((effective_rent - req.rent_max) / req.rent_max))
            if w_budget == 100: is_dealbreaker = True
        else:
            c_budget = 1.0
            
        # Diet Check
        c_diet = 1.0
        if req.dietary_pref and "Any" not in req.dietary_pref:
            if not any(pref in lst["dietary_tags"] for pref in req.dietary_pref):
                c_diet = 0.0
                if w_diet == 100: is_dealbreaker = True
                
        # Pet Check
        c_pets = 1.0
        if req.pet_pref != "No Pets":
            if req.pet_pref == "Small Pets Only" and lst["pet_policy"] == "No Pets":
                c_pets = 0.0
            elif req.pet_pref == "All Pets Welcome" and lst["pet_policy"] != "All Pets Welcome":
                c_pets = 0.0
            if c_pets == 0.0 and w_pets == 100: is_dealbreaker = True
        
        if is_dealbreaker:
            continue
            
        weighted_sum = (w_budget * c_budget) + (w_diet * c_diet) + (w_pets * c_pets)
        score = (weighted_sum / total_weight) * 100
        
        bachelor_score = 100
        if "Veg-Only" in lst["dietary_tags"]: bachelor_score -= 30
        if "No Alcohol/Smoking" in lst["dietary_tags"]: bachelor_score -= 30
        if lst["pet_policy"] == "No Pets": bachelor_score -= 20
        
        matches.append({
            "listing": lst,
            "score": round(score, 1),
            "reason": "AI Matrix Match",
            "effective_rent": effective_rent,
            "subsidy": 0,
            "bachelor_score": max(0, bachelor_score)
        })
            
    matches.sort(key=lambda x: x["score"], reverse=True)
    return {"matches": matches}

@app.post("/list-house")
def list_house(listing: PropertyListing):
    LISTINGS.append(listing.model_dump())
    return {"message": "Listing added successfully", "total_listings": len(LISTINGS)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
