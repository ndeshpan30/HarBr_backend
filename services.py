import sqlite3
import random
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import difflib
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')
app = FastAPI(title="HarBr v2.0")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        
        city_val = random.choice(neighborhoods)
        bhk_val = random.choice([1, 2, 3, 4])
        amenities_val = random.sample(amenity_options, random.randint(1, 3))
        furnishing_val = random.choice(["Fully Furnished", "Semi Furnished", "Unfurnished"])
        
        listings.append({
            "ulpin": f"10002000{random.randint(100000, 999999)}",
            "owner_name": owner_name,
            "city": city_val,
            "bhk": bhk_val,
            "area_sqft": random.randint(500, 2400),
            "rent": rent,
            "deposit": deposit,
            "floor_info": random.choice(['Ground Floor', '2nd of 4 floors', '5th of 10 floors', 'Penthouse']),
            "lift": random.choice([True, False]),
            "transport": [round(random.uniform(0.1, 5.0), 1), round(random.uniform(0.1, 2.0), 1)],
            "dietary_tags": random.sample(dietary_options, random.randint(1, 2)),
            "pet_policy": random.choice(pet_options),
            "utilities": random.sample(utility_options, random.randint(1, 3)),
            "amenities": amenities_val,
            "doc_tags": [doc_val] if doc_val != 'Disputed' else [],
            "water_tags": ["Cauvery Connection"] if "Cauvery Water" in utility_options else ["Borewell"],
            "commute_tags": [],
            "furnishing": furnishing_val,
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

@app.post("/shield-audit")
async def run_shield_audit(property_data: dict):
    try:
        prompt = f"""
        Act as the 'HarBr Shield Agent', a professional legal and lifestyle auditor for Bangalore rentals.
        Analyze this property: {property_data}
        
        Provide a high-density 'Trust Report' in exactly 3 bullet points:
        1. Legal Standing: Analyze the ULPIN/Khata status mentioned.
        2. Infrastructure Health: Comment on water source and amenities.
        3. Harmony Verdict: Is this property actually worth the deposit based on market trends?
        
        Tone: Professional, institutional, and direct.
        """
        response = model.generate_content(prompt)
        return {"audit_report": response.text}
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"audit_report": "⚠️ Shield Agent is currently offline. Basic verification applies."}

@app.post("/list-house")
def list_house(listing: PropertyListing):
    LISTINGS.append(listing.model_dump())
    return {"message": "Listing added successfully", "total_listings": len(LISTINGS)}

# --- NEW ORCHESTRATOR LOGIC ---

def query_neon_db(budget_max: int, neighborhood: str, bhk: int, pet_friendly: bool = False, dietary_pref: str = "Any", must_have_amenity: str = "Any") -> list:
    """For searching the 100+ property listings in the database. Call this to find homes. Returns a list of properties."""
    matches = []
    # simplistic matching
    for lst in LISTINGS:
        if budget_max > 0 and lst["rent"] > budget_max: continue
        if bhk > 0 and lst["bhk"] != bhk: continue
        if neighborhood and neighborhood.lower() not in lst["city"].lower(): continue
        if pet_friendly and lst["pet_policy"] == "No Pets": continue
        if dietary_pref != "Any" and dietary_pref not in lst["dietary_tags"]: continue
        if must_have_amenity != "Any" and must_have_amenity not in lst["amenities"]: continue
        matches.append(lst)
    return matches[:3]

def post_to_neon_db(ulpin: str, owner_name: str, rent: int, bhk: int, city: str, floor_info: str) -> str:
    """For finalized property listings. Call this ONLY when all information is gathered."""
    payload = {
        "ulpin": ulpin, "owner_name": owner_name, "city": city, "bhk": bhk,
        "area_sqft": 1000, "rent": rent, "deposit": rent*10, "floor_info": floor_info,
        "lift": True, "transport": [1.0, 0.5], "dietary_tags": [], "pet_policy": "No Pets",
        "utilities": [], "amenities": [], "doc_tags": ["A-Khata"], "water_tags": ["Cauvery Connection"],
        "commute_tags": [], "furnishing": "Semi Furnished", "facing": "East",
        "wfh_friendly": True, "pet_friendly": False
    }
    LISTINGS.append(payload)
    return f"Success! Property {ulpin} listed in {city} for {rent}."

def verify_ulpin(ulpin: str) -> dict:
    """To check the government land records."""
    record = get_legal_record(ulpin)
    if record: return {"status": record["status"], "owner": record["owner_name"]}
    return {"status": "Unverified", "owner": "Unknown"}

orchestrator_sys_prompt = """
1. Core Identity & Ethos
You are HarBr, the primary intelligence behind the HarBr Trust Infrastructure. Your purpose is to eliminate friction and distrust in the Bangalore rental market. You are sophisticated, highly interactive, and charismatic. You are not a bland search engine; you are an elite, proactive real-estate concierge.
Your tone is inspired by Claude AI: clear, intellectual, yet deeply conversational and warm. 
CRITICAL RULE: NEVER be boring. ALWAYS ask engaging follow-up questions to dig deeper into the user's lifestyle needs, commute preferences, or listing details.

2. The Three Pillars of Execution
Pillar I: Effortless Listing (The Ingestor)
If a user expresses intent to list, do not ask for all details at once. Ask for information in small, logical chunks (BHK, Rent, Location, ULPIN). Be conversational ("That sounds like a great property! Which neighborhood is it in?"). Once all data is gathered, trigger the post_to_neon_db function.

Pillar II: Precision Discovery (The Scout)
Convert vague, natural language queries into strict database parameters using query_neon_db. If they don't specify max budget, use 100000. If they don't specify bhk, use 0. If they don't specify neighborhood, use "".
If a user gives a vague query (e.g., just "find me a home"), DO NOT search the database yet. Interview them interactively! Ask about their lifestyle, if they have pets, what their office commute looks like, or if they need specific amenities. Only call the database when you have a good profile.
CRITICAL: When you find properties using query_neon_db, present them using this EXACT HTML block for EACH property. Ensure you replace the bracketed tags with the actual values returned by the database function:
<div class="glass-card">
    <h3 style="margin-top:0; color:#F9E076;">[owner_name]'s [bhk] BHK in [city]</h3>
    <p style="color: #A0A0A0; font-size: 0.9em; margin-bottom: 4px;">ULPIN: [ulpin] • [floor_info]</p>
    <div style="margin-bottom: 12px;">
        <span class="badge">[pet_policy]</span>
        <span class="badge">[first dietary tag]</span>
        <span class="badge">[first amenity]</span>
    </div>
    <p style="color: #E0E0E0; font-family: 'Fraunces', serif; font-size: 1rem; margin-bottom: 12px;"><strong>Why it matches:</strong> [Generate a 1-sentence reason based on the user's query]</p>
    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px; margin-top: 4px;">
        <span style="font-size: 1.2em; font-weight: bold; color: #E0E0E0;">₹[rent]<span style="font-size: 0.6em; color: #A0A0A0; font-weight: normal;"> /mo</span></span>
    </div>
</div>

Pillar III: The Shield Agent (The Auditor)
Provide real-time legal and fairness audits. You are an expert on the Karnataka Rent Control Act and the Model Tenancy Act (2021). If a user mentions a 10-month deposit, explain standard norms. Start your analysis with a "Scanning..." message. Use <div class="audit-report"> for legal deep-dives.

4. Operational Guardrails
Zero-Form Policy: Do not ask the user to fill out a form. Ask conversationally.
"""

orchestrator_model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=[query_neon_db, post_to_neon_db, verify_ulpin],
    system_instruction=orchestrator_sys_prompt
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

@app.post("/orchestrator/chat")
def orchestrator_chat(req: ChatRequest):
    history = []
    if len(req.messages) > 1:
        for msg in req.messages[:-1]:
            # Gemini roles: 'user' or 'model'
            role = "model" if msg.role == "assistant" else "user"
            history.append({"role": role, "parts": [msg.content]})
            
    try:
        chat = orchestrator_model.start_chat(history=history, enable_automatic_function_calling=True)
        
        # Track history length before sending message
        hist_len_before = len(chat.history)
        
        current_prompt = req.messages[-1].content
        response = chat.send_message(current_prompt)
        
        thinking_process = []
        for msg in chat.history[hist_len_before:]:
            for part in msg.parts:
                # Some parts might not have a function_call attribute directly, depending on protobuf wrappers
                # In google.generativeai, it's typically accessed via part.function_call
                if getattr(part, 'function_call', None):
                    # Extract arguments handling protobuf MapComposite
                    args_dict = {k: v for k, v in part.function_call.args.items()}
                    thinking_process.append({
                        "agent": "HarBr Orchestrator",
                        "function": part.function_call.name,
                        "args": args_dict
                    })
                    
        return {"reply": response.text, "thinking_process": thinking_process}
    except Exception as e:
        print(f"Orchestrator API Error: {e}")
        return {"reply": f"Neural link severed: {e}", "thinking_process": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

