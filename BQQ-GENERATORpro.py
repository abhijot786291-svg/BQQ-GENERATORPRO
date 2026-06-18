import streamlit as st
import datetime
import pandas as pd
import time
import random

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="PitMaster Extreme Pro",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CONSTANTS & PRICING DATABASES
# ==========================================
# Construction material base rates (Price per Linear Foot)
DEFAULT_MATERIALS = {
    "Basic Stucco": 150,
    "Premium Brick": 280,
    "Natural Ledge Stone": 400,
    "Polished Concrete": 200
}

# Countertop materials (Price per Linear Foot)
DEFAULT_COUNTERS = {
    "Tile": 50,
    "Poured Concrete": 120,
    "Level 1 Granite": 200,
    "Premium Quartz": 350
}

# Furniture / Hardware (Fixed Cost)
DEFAULT_HARDWARE = {
    "Built-in Pellet Smoker": 1500,
    "Kamado Ceramic Grill": 1200,
    "36-inch Gas Griddle": 800,
    "Outdoor Fridge / Kegerator": 1100,
    "Stainless Steel Double Doors": 300,
    "Plumbed Sink": 450,
    "Wood-fired Pizza Oven": 2500
}

# BBQ Cooking profiles (Hours per pound at 225F)
MEAT_PROFILES = {
    "Brisket (Packer)": {"time_per_lb": 1.25, "wrap_temp": 165, "pull_temp": 203, "rest_hours": 2},
    "Pork Butt": {"time_per_lb": 1.5, "wrap_temp": 165, "pull_temp": 205, "rest_hours": 1},
    "Pork Ribs (3-2-1 Method)": {"time_per_lb": 0, "fixed_time": 6, "wrap_temp": None, "pull_temp": None, "rest_hours": 0.5},
    "Whole Chicken": {"time_per_lb": 0.75, "wrap_temp": None, "pull_temp": 165, "rest_hours": 0.5}
}

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'custom_rates' not in st.session_state:
        st.session_state.custom_rates = DEFAULT_HARDWARE.copy()
    if 'privacy_settings' not in st.session_state:
        st.session_state.privacy_settings = {
            "share_cook_data": False,
            "cloud_sync": True,
            "public_profile": False,
            "location_tracking": False # For weather APIs
        }

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def calculate_timeline(meat_type, weight, serve_time):
    """Calculates a chronological timeline based on meat type and weight."""
    profile = MEAT_PROFILES[meat_type]
    
    if "fixed_time" in profile:
        cook_time_hours = profile["fixed_time"]
    else:
        cook_time_hours = weight * profile["time_per_lb"]
        
    rest_time_hours = profile["rest_hours"]
    total_time_hours = cook_time_hours + rest_time_hours
    
    # Calculate timestamps
    serve_dt = datetime.datetime.combine(datetime.date.today(), serve_time)
    start_dt = serve_dt - datetime.timedelta(hours=total_time_hours)
    prep_dt = start_dt - datetime.timedelta(minutes=45)
    
    timeline = []
    timeline.append({"Action": "Trim & Season Meat (Prep)", "Time": prep_dt.strftime("%I:%M %p")})
    timeline.append({"Action": "Light Smoker (Target 225°F)", "Time": (start_dt - datetime.timedelta(minutes=30)).strftime("%I:%M %p")})
    timeline.append({"Action": "Meat on Smoker", "Time": start_dt.strftime("%I:%M %p")})
    
    if profile.get("wrap_temp"):
        wrap_dt = start_dt + datetime.timedelta(hours=(cook_time_hours * 0.6)) # Estimate stall at 60% time
        timeline.append({"Action": f"Check for Stall / Wrap (Target {profile['wrap_temp']}°F)", "Time": wrap_dt.strftime("%I:%M %p")})
        
    pull_dt = serve_dt - datetime.timedelta(hours=rest_time_hours)
    if profile.get("pull_temp"):
        timeline.append({"Action": f"Pull from Smoker (Target {profile['pull_temp']}°F)", "Time": pull_dt.strftime("%I:%M %p")})
    else:
        timeline.append({"Action": "Pull from Smoker", "Time": pull_dt.strftime("%I:%M %p")})
        
    timeline.append({"Action": "Rest in Cooler / Cambro", "Time": pull_dt.strftime("%I:%M %p")})
    timeline.append({"Action": "Slice & Serve", "Time": serve_dt.strftime("%I:%M %p")})
    
    return pd.DataFrame(timeline)

def generate_ai_response(prompt):
    """Mocks an AI pitmaster response based on keywords."""
    prompt = prompt.lower()
    if "stall" in prompt or "stuck" in prompt:
        return "It sounds like you've hit the stall! This happens around 160°F-165°F as evaporative cooling from the meat matches the heat of the smoker. You can 'Texas Crutch' it by wrapping in butcher paper or foil to push through."
    elif "brisket" in prompt:
        return "For brisket, always trim the fat cap to about 1/4 inch. Smoke at 225°F-250°F using post oak or hickory. Don't pull by time alone—pull when the probe slides into the thickest part of the flat like warm butter (usually around 200°F-205°F)."
    elif "cost" in prompt or "expensive" in prompt:
        return "Building an outdoor kitchen? Remember that plumbing a sink or running a dedicated gas line are hidden costs. Always factor in an extra 15% for permits and utility trenching."
    else:
        responses = [
            "Keep the dirty smoke away! Make sure your fire is burning clean and blue.",
            "Resting is just as important as cooking. Give large cuts at least 1-2 hours in a dry cooler.",
            "If you're looking, you ain't cooking! Keep that lid closed.",
            "Every piece of meat is different. Cook to temperature and feel, not just time."
        ]
        return random.choice(responses)

# ==========================================
# UI COMPONENTS (PAGES)
# ==========================================

def page_login():
    """Renders the login/authentication screen."""
    st.markdown("<h1 style='text-align: center;'>🔥 PitMaster Extreme Pro</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>The Ultimate BBQ & Builder Platform</h4>", unsafe_allow_html=True)
    
    st.write("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Secure Login")
        email = st.text_input("Email Address", placeholder="pitmaster@example.com")
        password = st.text_input("Password", type="password")
        
        if st.button("Access Dashboard", use_container_width=True):
            if email:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Please enter a valid email address.")
                
        st.caption("🔒 256-bit Encrypted Connection. By logging in, you agree to our Privacy Policy.")

def page_dashboard():
    """Main landing dashboard."""
    st.title(f"Welcome back, {st.session_state.user_email.split('@')[0]}!")
    st.write("Here is your Pitmaster command center.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cooks Logged", "42", "+3 this month")
    col2.metric("Current Weather", "78°F, 40% Hum", "Ideal for smoking")
    col3.metric("Hardware Status", "Meater Probe: Online", "100% Battery")
    
    st.write("---")
    st.subheader("Recent Activity / Sensor Data")
    
    # Graphic feature: Mock temperature chart
    chart_data = pd.DataFrame({
        "Smoker Temp (°F)": [220, 224, 226, 225, 222, 225, 228, 225],
        "Meat Temp (°F)": [45, 60, 85, 110, 135, 150, 160, 162]
    }, index=["0h", "1h", "2h", "3h", "4h", "5h", "6h", "7h"])
    st.line_chart(chart_data)

def page_cook_planner():
    """Smart Recipe and Timeline Generator."""
    st.title("⏱️ Dynamic Cook Planner")
    st.write("Plan your cook backwards from your desired serving time.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Cook Parameters")
        meat_type = st.selectbox("Select Meat", list(MEAT_PROFILES.keys()))
        weight = st.slider("Weight (lbs)", min_value=1.0, max_value=25.0, value=10.0, step=0.5)
        serve_time = st.time_input("Target Serve Time", value=datetime.time(18, 0)) # 6:00 PM
        
        # Flavor profile generator
        st.write("---")
        st.subheader("Custom Rub Generator")
        sweet = st.slider("Sweetness", 0, 10, 5)
        heat = st.slider("Heat (Spicy)", 0, 10, 7)
        savory = st.slider("Savory/Umami", 0, 10, 8)
        
        if st.button("Generate Rub Recipe"):
            st.success(f"Mix: {savory} parts Black Pepper, {sweet} parts Brown Sugar, {heat} parts Cayenne/Paprika, 5 parts Kosher Salt.")
            
    with col2:
        st.subheader("Chronological Timeline")
        timeline_df = calculate_timeline(meat_type, weight, serve_time)
        st.table(timeline_df)
        
        st.info("💡 **Pro Tip:** This timeline accounts for a standard 'stall'. If weather is cold or windy, add 10% to your cook time.")

def page_kitchen_estimator():
    """Outdoor Kitchen Builder and Cost Estimator."""
    st.title("🧱 Outdoor Kitchen Builder & Cost Estimator")
    st.write("Design your dream BBQ setup. Adjust sizes, materials, and hardware to calculate total costs.")
    
    # Editable Rates Expander
    with st.expander("⚙️ Edit Base Hardware Rates (Advanced)"):
        st.write("Adjust local pricing for your specific contractors or suppliers.")
        col_rate1, col_rate2 = st.columns(2)
        keys = list(st.session_state.custom_rates.keys())
        half = len(keys) // 2
        for i, key in enumerate(keys):
            if i < half:
                st.session_state.custom_rates[key] = col_rate1.number_input(f"{key} ($)", value=st.session_state.custom_rates[key])
            else:
                st.session_state.custom_rates[key] = col_rate2.number_input(f"{key} ($)", value=st.session_state.custom_rates[key])

    # Builder UI
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("1. Dimensions & Structure")
        linear_feet = st.slider("Total Linear Feet of Counter", min_value=5, max_value=40, value=12)
        shape = st.selectbox("Layout Shape", ["Straight Line", "L-Shape", "U-Shape", "Island"])
        
        st.subheader("2. Materials")
        base_material = st.selectbox("Base Material", list(DEFAULT_MATERIALS.keys()))
        counter_material = st.selectbox("Countertop Material", list(DEFAULT_COUNTERS.keys()))
        
        st.subheader("3. Furniture & Appliances")
        selected_hardware = []
        for item in st.session_state.custom_rates.keys():
            if st.checkbox(item):
                selected_hardware.append(item)
                
    with col2:
        st.subheader("Itemized Estimate")
        
        # Calculations
        base_cost = linear_feet * DEFAULT_MATERIALS[base_material]
        counter_cost = linear_feet * DEFAULT_COUNTERS[counter_material]
        
        # Build Receipt Dataframe
        receipt_items = [
            {"Category": "Structure", "Description": f"{linear_feet} ft of {base_material}", "Cost": base_cost},
            {"Category": "Surfaces", "Description": f"{linear_feet} ft of {counter_material}", "Cost": counter_cost}
        ]
        
        hardware_total = 0
        for hw in selected_hardware:
            cost = st.session_state.custom_rates[hw]
            hardware_total += cost
            receipt_items.append({"Category": "Hardware", "Description": hw, "Cost": cost})
            
        df_receipt = pd.DataFrame(receipt_items)
        
        # Display table cleanly
        st.dataframe(df_receipt, use_container_width=True, hide_index=True)
        
        # Totals
        total_cost = base_cost + counter_cost + hardware_total
        labor_estimate = total_cost * 0.35 # Assume 35% of material/hardware for labor
        
        st.write("---")
        st.metric("Total Material & Hardware", f"${total_cost:,.2f}")
        st.metric("Estimated Contractor Labor (35%)", f"${labor_estimate:,.2f}")
        st.markdown(f"### **Grand Total Estimate: ${total_cost + labor_estimate:,.2f}**")
        st.caption("Pricing is an estimate and does not include local permits, plumbing runs, or electrical trenching.")

def page_ai_bot():
    """AI Pitmaster Chatbot."""
    st.title("🤖 AI Pitmaster Assistant")
    st.write("Ask questions about recipes, meat science, or construction issues.")
    
    # Render chat history
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            
    # Input box
    prompt = st.chat_input("E.g., 'How do I push through a brisket stall?' or 'What is the best stone for a pizza oven?'")
    
    if prompt:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Add AI response
        with st.chat_message("assistant"):
            with st.spinner("Consulting the smoke ring..."):
                time.sleep(1) # Simulate network delay
                response = generate_ai_response(prompt)
                st.write(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

def page_settings():
    """Privacy and Account Settings."""
    st.title("⚙️ App Privacy & Settings")
    
    st.subheader("Account Details")
    st.text_input("Account Email", value=st.session_state.user_email, disabled=True)
    
    st.write("---")
    st.subheader("Data & Privacy")
    st.session_state.privacy_settings["share_cook_data"] = st.toggle("Share Anonymous Cook Logs", value=st.session_state.privacy_settings["share_cook_data"], help="Helps train our 'Stall Predictor' algorithm.")
    st.session_state.privacy_settings["cloud_sync"] = st.toggle("Cloud Sync Hardware Logs", value=st.session_state.privacy_settings["cloud_sync"])
    st.session_state.privacy_settings["public_profile"] = st.toggle("Public Pitmaster Profile", value=st.session_state.privacy_settings["public_profile"])
    st.session_state.privacy_settings["location_tracking"] = st.toggle("Enable Location for Weather API", value=st.session_state.privacy_settings["location_tracking"])
    
    if st.button("Save Settings", type="primary"):
        st.toast("Settings saved successfully!", icon="✅")
        
    st.write("---")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# ==========================================
# MAIN ROUTING LOGIC
# ==========================================
def main():
    init_session_state()
    
    if not st.session_state.logged_in:
        page_login()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.title("🔥 PitMaster Pro")
            st.write(f"User: `{st.session_state.user_email}`")
            st.write("---")
            nav_selection = st.radio(
                "Navigation",
                ["Dashboard", "⏱️ Cook Planner", "🧱 Kitchen Estimator", "🤖 AI Assistant", "⚙️ Settings"]
            )
            
        # Route to appropriate page
        if nav_selection == "Dashboard":
            page_dashboard()
        elif nav_selection == "⏱️ Cook Planner":
            page_cook_planner()
        elif nav_selection == "🧱 Kitchen Estimator":
            page_kitchen_estimator()
        elif nav_selection == "🤖 AI Assistant":
            page_ai_bot()
        elif nav_selection == "⚙️ Settings":
            page_settings()

if __name__ == "__main__":
    main()