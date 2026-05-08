import streamlit as st
import requests
from pdf_gen import generate_health_card

API_URL = "http://127.0.0.1:8080" 

st.set_page_config(layout="centered", page_title="HarBr | Trust Infrastructure", page_icon="🛡️", initial_sidebar_state="collapsed")

if "role" not in st.session_state:
    st.session_state.role = "owner"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #E0E0E0;
    }
    .stApp { background-color: #2E2E2E; }
    
    .block-container {
        max-width: 850px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .notion-card {
        border: 1px solid #4D4D4D;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
        background-color: #3B3B3B;
    }

    .metadata {
        font-size: 0.85rem;
        color: #A0A0A0;
        font-family: 'Inter', sans-serif;
    }

    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 4px;
        background-color: #f1f1ef;
        color: #37352f;
        text-transform: uppercase;
        margin-top: 4px;
    }
    .badge-certified { background-color: #27AE60; color: white; }
    .badge-pending { background-color: #2F80ED; color: white; }
    .badge-unverified { background-color: #7F8C8D; color: white; }
    .badge-subsidy { background-color: #9B51E0; color: white; }
    .badge-water { background-color: #2D9CDB; color: white; }
    .badge-alert { background-color: #EB5757; color: white; }
    
    .stButton > button {
        border-radius: 4px !important;
        border: 1px solid #666;
        background-color: transparent;
        color: #E0E0E0;
        padding: 4px 12px;
        font-size: 0.9em;
    }
    .stButton > button:hover {
        border-color: #2F80ED;
        color: #2F80ED;
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

st.title("HarBr 2.0")

col1, col2 = st.columns(2)
with col1:
    if st.button("🏠 Owner Portal", use_container_width=True):
        st.session_state.role = "owner"
with col2:
    if st.button("👤 Tenant Discovery", use_container_width=True):
        st.session_state.role = "tenant"
        st.session_state.selected_ulpin = None

st.divider()

if st.session_state.role == "owner":
    st.header("List Your Property")
    st.info("Switch to 'Tenant Discovery' to view the 100 seeded properties!")

elif st.session_state.role == "tenant":
    st.markdown("### 🔍 Search & Harmony Filters")
    st.caption("Adjust your preferences to find your perfect match.")

    # 2. The Core Filters (Always Visible)
    col1, col2 = st.columns(2)
    with col1:
        rent_range = st.select_slider(
            "Monthly Rent Budget (₹)",
            options=[i for i in range(10000, 155000, 1000)],
            value=(20000, 45000)
        )
    with col2:
        diet_pref = st.multiselect("Dietary Preference", ["Veg-Only", "Non-Veg OK", "Vegan"], default=["Veg-Only"])

    # 3. The "Priority" Section
    with st.expander("⚖️ Adjust Priority Weights", expanded=False):
        st.info("Set which factors matter most to your Harmony Score.")
        pw_col1, pw_col2, pw_col3 = st.columns(3)
        
        priority_map = {"Essential": 100, "High": 10, "Medium": 5, "Low": 2}
        
        with pw_col1:
            budget_w = st.selectbox("Budget Priority", list(priority_map.keys()), index=0)
        with pw_col2:
            diet_w = st.selectbox("Dietary Priority", list(priority_map.keys()), index=1)
        with pw_col3:
            pet_w = st.selectbox("Pet Priority", list(priority_map.keys()), index=2)

    # 4. Advanced Property Specs
    with st.container(border=True):
        spec_col1, spec_col2 = st.columns(2)
        with spec_col1:
            pets = st.selectbox("Pet Policy", ["No Pets", "Small Pets Only", "All Pets Welcome"])
            utilities = st.multiselect("Utilities Needed", ["Cauvery Water", "Power Backup", "EV Charging", "Piped Gas"])
        with spec_col2:
            floor = st.multiselect("Floor Preference", ["Ground", "Middle Floors", "Top Floor / Penthouse"])
            transport = st.multiselect("Access", ["< 500m to Metro", "< 1km to Metro", "Near Bus Stop"])

    if st.button("Calculate Harmony Score", type="primary", use_container_width=True):
        st.toast("AI Matcher is analyzing 100+ listings...")
        st.session_state.search_params = {
            "rent_min": rent_range[0],
            "rent_max": rent_range[1],
            "dietary_pref": diet_pref,
            "pet_pref": pets,
            "utilities_pref": utilities,
            "floor_pref": floor,
            "transport_pref": transport,
            "weights": {
                "budget": priority_map[budget_w],
                "diet": priority_map[diet_w],
                "pets": priority_map[pet_w]
            }
        }
        st.session_state.selected_ulpin = None
        
    if "search_params" in st.session_state:
        try:
            res = requests.post(f"{API_URL}/matcher/calculate", json=st.session_state.search_params)
            res.raise_for_status()
            matches = res.json()["matches"]
            
            if matches:
                for i, m in enumerate(matches[:30]):
                    lst = m["listing"]
                    shield_res = requests.post(f"{API_URL}/shield/audit", json={"ulpin": lst["ulpin"], "owner_name": lst["owner_name"], "rent": lst["rent"], "deposit": lst["deposit"], "doc_tags": lst["doc_tags"]})
                    
                    status_str = "Unverified"
                    badge_cls = "badge-unverified"
                    shield_msg = ""
                    if shield_res.status_code == 200:
                        data = shield_res.json()
                        status_str = data["status"]
                        shield_msg = data["message"]
                        if status_str == "Shield Certified": badge_cls = "badge-certified"
                        elif status_str == "Audit Pending": badge_cls = "badge-pending"
                        elif status_str == "High Initial Capital" or status_str == "ILLEGAL": badge_cls = "badge-alert"

                    with st.container():
                        st.markdown(f"#### 🏠 {lst['city']} {lst['bhk']} BHK")
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.caption(f"📍 {lst['floor_info']}")
                        c2.caption(f"🛗 Lift: {'Yes' if lst['lift'] else 'No'}")
                        c3.caption(f"🚇 {lst['transport'][0]}km Metro")
                        c4.caption(f"💧 {lst['utilities'][0] if lst['utilities'] else 'City Water'}")

                        doc_badge = ''.join([f"<span class='badge' style='background-color: #4D4D4D; color: #E0E0E0;'>{tag}</span>" for tag in lst["doc_tags"]])
                        tags_html = "".join([f'<span class="badge">{t}</span>' for t in lst['dietary_tags'] + lst['amenities']])
                        water_trust = "<span class='badge badge-water'>Cauvery Water: High Trust</span>" if "Cauvery Water" in lst['utilities'] else "<span class='badge badge-alert'>Tanker Dependent</span>"
                        
                        html_content = f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<div>
<span class='badge {badge_cls}'>{status_str}</span>
{doc_badge}
{water_trust}
</div>
<div style="text-align: right;">
<div style="font-weight: bold; color: #F2C94C; font-size: 1.2em;">{m['score']}% Harmony</div>
<div style="font-size: 0.8em; color: #828282;">{m['bachelor_score']}/100 Bachelor Friendly</div>
</div>
</div>
<div>{tags_html}</div>
<div style="font-size: 0.9em; margin-top: 8px;">
<b>₹{lst['rent']}/mo</b> • Deposit: ₹{lst['deposit']} 
<span style='float: right;'>"""
                        st.markdown(html_content, unsafe_allow_html=True)
                        
                        if st.button(f"Peek {lst['ulpin']}", key=f"view_{lst['ulpin']}_{i}"):
                            st.session_state.selected_ulpin = lst['ulpin']
                            st.session_state.selected_match = m
                            st.session_state.selected_shield = shield_msg
                            
                        st.markdown("</span></div><hr style='margin: 12px 0; border-color: #4D4D4D;'/>", unsafe_allow_html=True)
            else:
                st.info("No matching records found. Your Essential priority might be blocking options, or your budget is too narrow.")
        except Exception as e:
            st.error(f"Backend offline. Please restart python services.py. {e}")

if st.session_state.get("selected_ulpin"):
    with st.sidebar:
        sel = st.session_state.selected_match
        lst = sel["listing"]
        shield_msg = st.session_state.get("selected_shield", "")
        
        st.markdown(f"### Property Detail Peek")
        st.caption(f"ULPIN: {lst['ulpin']}")
        st.write(f"**Owner:** {lst['owner_name']}")
        st.write(f"**Market Rent:** ₹{lst['rent']}")
        st.write(f"**Deposit:** ₹{lst['deposit']} *(Ratio: {lst['deposit']/lst['rent']:.1f}x)*")
        
        st.markdown(f"<div style='background-color:#383838; padding: 10px; border-left: 3px solid #2F80ED; margin: 10px 0;'><small>{shield_msg}</small></div>", unsafe_allow_html=True)
        
        st.write("**Tags & Utilities:**")
        for tag in lst["utilities"] + lst["amenities"]:
            st.markdown(f"<span class='badge' style='background-color: #555; color: white;'>{tag}</span>", unsafe_allow_html=True)
            
        st.write(f"**Pet Policy:** {lst['pet_policy']}")
        
        if st.button("Close Peek"):
            st.session_state.selected_ulpin = None
            st.rerun()
