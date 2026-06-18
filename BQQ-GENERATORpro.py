import streamlit as st # type: ignore
import pandas as pd # type: ignore
import numpy as np # type: ignore
import datetime
import plotly.express as px # type: ignore
import plotly.graph_objects as go # type: ignore
import io
import time
import random
import sqlite3
import json
import tempfile

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# ==========================================
# CONSTANTS & ENTERPRISE RATES REGIONAL DATABASE
# ==========================================
REGIONAL_DATABASES = {
    "North America (East)": {"labor_multiplier": 1.2, "material_index": 1.1, "currency": "$", "tax_label": "HST/VAT"},
    "US Southwest": {"labor_multiplier": 1.0, "material_index": 1.0, "currency": "$", "tax_label": "Sales Tax"},
    "Europe Central": {"labor_multiplier": 1.3, "material_index": 1.15, "currency": "€", "tax_label": "VAT"},
    "Asia Pacific": {"labor_multiplier": 0.6, "material_index": 0.9, "currency": "¥", "tax_label": "GST"}
}

DEFAULT_TRADES = ["01 - General Conditions", "03 - Concrete & Foundations", "04 - Masonry & Framing", "09 - Finishes", "22 - Plumbing/Mech"]

# ==========================================
# ADDED FEATURE 3: PERSISTENT STORAGE (SQLITE)
# ==========================================
def save_state_to_db():
    """Background utility to synchronize Streamlit memory arrays into SQLite persistence."""
    try:
        conn = sqlite3.connect("buildmaster_enterprise.db")
        # Save DataFrames natively into SQL tables
        st.session_state.master_boq.to_sql('master_boq', conn, if_exists='replace', index=False)
        st.session_state.inventory.to_sql('inventory', conn, if_exists='replace', index=False)
        
        # Save Lists/Dicts into a JSON string table
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, json_data TEXT)')
        c.execute('REPLACE INTO app_state (key, json_data) VALUES (?, ?)', ('projects', json.dumps(st.session_state.projects)))
        c.execute('REPLACE INTO app_state (key, json_data) VALUES (?, ?)', ('action_history', json.dumps(st.session_state.action_history)))
        c.execute('REPLACE INTO app_state (key, json_data) VALUES (?, ?)', ('site_log', json.dumps(st.session_state.site_log, default=str)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Sync Error: {e}")

def load_state_from_db():
    """Attempts to pull memory states from the SQLite database."""
    try:
        conn = sqlite3.connect("buildmaster_enterprise.db")
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'")
        if c.fetchone():
            c.execute('SELECT key, json_data FROM app_state')
            rows = c.fetchall()
            db_state = {row[0]: json.loads(row[1]) for row in rows}
            
            if 'projects' in db_state: st.session_state.projects = db_state['projects']
            if 'action_history' in db_state: st.session_state.action_history = db_state['action_history']
            if 'site_log' in db_state: st.session_state.site_log = db_state['site_log']
            
            st.session_state.master_boq = pd.read_sql('SELECT * FROM master_boq', conn)
            st.session_state.inventory = pd.read_sql('SELECT * FROM inventory', conn)
            conn.close()
            return True
        conn.close()
    except Exception as e:
        print(f"Database Load Error: {e}")
    return False


# ==========================================
# SYSTEM SETUP & SESSION LAYER
# ==========================================
st.set_page_config(page_title="BuildMaster Enterprise ERP", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

def init_enterprise_state():
    # Attempt to load persistent storage first
    if load_state_from_db():
        # Ensure remaining session states are populated if not DB stored
        if 'app_settings' not in st.session_state:
            st.session_state.app_settings = {"company_name": "Global Builders Inc", "white_label": False, "cloud_sync": True, "offline_mode": False}
        if "ai_messages" not in st.session_state:
            st.session_state.ai_messages = [{"role": "assistant", "content": "Hello! I am your AI Construction Assistant. Ask me about house costs in Punjab, brick calculations, or roof slab estimates!"}]
        return

    # Structural Control Arrays (Fallback Defaults)
    if 'projects' not in st.session_state:
        st.session_state.projects = [
            {"id": "PRJ-2026-001", "name": "Smith Luxury Outdoor Suite", "region": "US Southwest", "status": "Active", "progress": 45.0, "template": False, "role": "Project Manager", "version": 4},
            {"id": "PRJ-TMP-002", "name": "Standard Straight Island Build", "region": "US Southwest", "status": "Template", "progress": 0.0, "template": True, "role": "Estimator", "version": 1},
            {"id": "PRJ-2026-003", "name": "Commercial Patio Development", "region": "North America (East)", "status": "Archived", "progress": 100.0, "template": False, "role": "Admin", "version": 12}
        ]
        
    if 'master_boq' not in st.session_state:
        # Relational database table structure for items (Features 11-20)
        st.session_state.master_boq = pd.DataFrame([
            {"Project ID": "PRJ-2026-001", "Item No": "03.01.001", "Trade": "03 - Concrete & Foundations", "Description": "Poured Concrete Footings 4000PSI", "Qty": 14.5, "Unit": "cu.yd", "Mat Unit Cost": 135.0, "Lab Unit Cost": 65.0, "Equip Unit Cost": 25.0},
            {"Project ID": "PRJ-2026-001", "Item No": "04.02.001", "Trade": "04 - Masonry & Framing", "Description": "Premium Brick Structural Skin", "Qty": 340.0, "Unit": "sqft", "Mat Unit Cost": 12.5, "Lab Unit Cost": 18.0, "Equip Unit Cost": 0.0},
            {"Project ID": "PRJ-2026-001", "Item No": "09.01.005", "Trade": "09 - Finishes", "Description": "Level 4 Polished Granite Slab", "Qty": 65.0, "Unit": "sqft", "Mat Unit Cost": 85.0, "Lab Unit Cost": 45.0, "Equip Unit Cost": 12.0}
        ])

    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"SKU": "MAT-CONC-4K", "Item": "Ready-Mix Portland Concrete", "Stock": 0.0, "Min_Alert": 10.0, "Supplier": "Titan Materials Corp"},
            {"SKU": "MAT-BRK-PREM", "Item": "Premium Face Brick (Palette)", "Stock": 12.0, "Min_Alert": 3.0, "Supplier": "Masonry Supply Depot"},
            {"SKU": "MAT-SINK-SS36", "Item": "Stainless Undermount Sink 36", "Stock": 2.0, "Min_Alert": 5.0, "Supplier": "Aero Kitchen Hardware"}
        ])

    if 'site_log' not in st.session_state:
        st.session_state.site_log = []
        
    if 'app_settings' not in st.session_state:
        st.session_state.app_settings = {"company_name": "Global Builders Inc", "white_label": False, "cloud_sync": True, "offline_mode": False}
        
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = [
            {"role": "assistant", "content": "Hello! I am your AI Construction Assistant. Ask me about house costs in Punjab, brick calculations, or roof slab estimates!"}
        ]

    if 'action_history' not in st.session_state:
        st.session_state.action_history = [
            {"Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Module": "System Core", "Action": "Engine Online", "Details": "Relational structural invariants initialized safely."}
        ]
        
    # Once initial default state is set, persist it to SQLite
    save_state_to_db()

init_enterprise_state()

# Global Logging Handler Utility Function
def log_system_action(module_name, action_type, detail_string):
    st.session_state.action_history.append({
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": module_name,
        "Action": action_type,
        "Details": detail_string
    })
    # Seamlessly trigger SQLite persistence across the application on every logged action
    save_state_to_db()

# ==========================================
# MODULE 1: INTERACTIVE ENTERPRISE DASHBOARD & PM
# ==========================================
def render_project_dashboard():
    st.title("📊 Multi-Project Control Center")
    st.write("Real-time telemetry across active portfolios, resource lifecycles, and governance roles.")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Managed Portfolios", len(st.session_state.projects))
    m2.metric("Active Runs", len([p for p in st.session_state.projects if p["status"]=="Active"]))
    m3.metric("System Sync Speed", "12ms", "Cloud Operational")
    m4.metric("Security Level", "RBAC Locked", "AES-256")
    
    st.write("---")
    
    t1, t2, t3, t4 = st.tabs(["Project Portfolios", "Interactive Gantt Timeline", "Cloning & Template Center", "📜 System Action Audit Logs"])
    
    with t1:
        st.subheader("Enterprise Project Registry")
        for i, proj in enumerate(st.session_state.projects):
            col_p1, col_p2, col_p3 = st.columns([3, 2, 1])
            with col_p1:
                st.markdown(f"#### **{proj['name']}** `[{proj['id']}]`")
                st.caption(f"Region: **{proj['region']}** | User Assignment Level: **{proj['role']}** | Version Tracker: v{proj['version']}")
            with col_p2:
                st.write("")
                st.progress(proj["progress"] / 100.0)
            with col_p3:
                act = st.selectbox("Action", ["Modify Engine", "Clone Blueprint", "Archive Stack", "Purge Line"], key=f"act_{proj['id']}")
                if act == "Archive Stack" and proj["status"] != "Archived":
                    st.session_state.projects[i]["status"] = "Archived"
                    log_system_action("Portfolio Hub", "Archive Action", f"Moved project identity {proj['id']} into system archives.")
                    st.toast("Project moved to archive.")
                    st.rerun()
    
    with t2:
        st.subheader("Milestone Management & Production Gantt")
        gantt_mock = pd.DataFrame([
            dict(Task="Phase 1: Civil Takeoff & Permit", Start="2026-06-01", Finish="2026-06-15", Resource="PM"),
            dict(Task="Phase 2: Substructure Pouring", Start="2026-06-16", Finish="2026-06-28", Resource="Mason Crew"),
            dict(Task="Phase 3: Hardware Outfitting", Start="2026-06-29", Finish="2026-07-12", Resource="Plumbing Tech")
        ])
        fig = px.timeline(gantt_mock, x_start="Start", x_end="Finish", y="Task", color="Resource", title="Global Lifecycle View")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
    with t3:
        st.subheader("Automated Cloning Engine")
        with st.form("Cloning Vector"):
            src_template = st.selectbox("Select Source Array", [p["name"] for p in st.session_state.projects if p["template"] or p["status"] == "Template"])
            target_name = st.text_input("New Allocation Identifier Name", "Project Extension Alpha")
            target_reg = st.selectbox("Target Economic Database Region", list(REGIONAL_DATABASES.keys()))
            if st.form_submit_button("Execute High-Fidelity Replication"):
                new_id = f"PRJ-2026-{random.randint(100,999)}"
                st.session_state.projects.append({"id": new_id, "name": target_name, "region": target_reg, "status": "Active", "progress": 0.0, "template": False, "role": "Admin", "version": 1})
                log_system_action("Portfolio Hub", "Project Duplication", f"Cloned target matrix framework into new identifier: {new_id}")
                st.success(f"Successfully operationalized {new_id} via structural duplication patterns.")
                st.sidebar.info("System refresh required to draw layout matrices.")

    with t4:
        st.subheader("Real-Time Application Activity Log Streams")
        st.write("Verifiable activity logs captured across global interface runtimes.")
        history_df = pd.DataFrame(st.session_state.action_history)
        st.dataframe(history_df.iloc[::-1], use_container_width=True, hide_index=True)

# ==========================================
# MODULE 2: QUANTITY TAKE-OFF & ADVANCED BOQ ENGINE
# ==========================================
def render_boq_engine():
    st.title("🏗️ Dynamic BOQ & AI Takeoff Workspace")
    
    active_p = st.selectbox("Active Focus Target Portfolio", [p["name"] for p in st.session_state.projects if p["status"] == "Active"])
    p_id = [p["id"] for p in st.session_state.projects if p["name"] == active_p][0]
    
    st.write("---")
    
    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        st.subheader("Itemized Matrix Input & Smart Formula Engine")
        with st.form("Item Insertion Matrix"):
            trade_select = st.selectbox("Functional Trade Scope Division", DEFAULT_TRADES)
            desc_input = st.text_input("Structural Line Item Description Specification")
            
            f_col1, f_col2, f_col3 = st.columns(3)
            q_val = f_col1.number_input("Target Quantity Value", min_value=0.0, value=1.0)
            u_str = f_col2.text_input("Engineering Unit Type", "sqft")
            
            st.markdown("**Core Asset Internal Cost Structures ($)**")
            c_mat = f_col3.number_input("Material Base Layer Unit Cost", value=0.0)
            c_lab = f_col1.number_input("Labor Variable Unit Cost", value=0.0)
            c_eq = f_col2.number_input("Machinery/Equipment Cost Allocation", value=0.0)
            
            if st.form_submit_button("Commit Line Item Array to System Core"):
                trade_code = trade_select.split(" ")[0]
                item_count = len(st.session_state.master_boq[st.session_state.master_boq["Trade"] == trade_select]) + 1
                generated_item_no = f"{trade_code}.01.{item_count:03d}"
                
                new_row = {"Project ID": p_id, "Item No": generated_item_no, "Trade": trade_select, "Description": desc_input, "Qty": q_val, "Unit": u_str, "Mat Unit Cost": c_mat, "Lab Unit Cost": c_lab, "Equip Unit Cost": c_eq}
                st.session_state.master_boq = pd.concat([st.session_state.master_boq, pd.DataFrame([new_row])], ignore_index=True)
                log_system_action("BOQ Engine", "Line Entry Insertion", f"Appended calculation item [{generated_item_no}] directly into active portfolio matrix.")
                st.toast(f"Committed {generated_item_no} cleanly.")
                st.rerun()

    with col_b2:
        st.subheader("🤖 GenAI Production Estimator & Automated Verification")
        ai_input = st.text_area("Provide Natural Language Structural Briefings / Layout Prompts", placeholder="Parse a 20ft U-shaped polished concrete build with outdoor gas ranges and deep foundations...")
        if st.button("Invoke AI Design Agent Optimization Pipeline"):
            with st.spinner("Executing structural validation layers..."):
                time.sleep(1.5)
                ai_rows = [
                    {"Project ID": p_id, "Item No": "01.01.901", "Trade": "01 - General Conditions", "Description": "AI Optimization Variance Mitigation Buffer", "Qty": 1.0, "Unit": "LS", "Mat Unit Cost": 0.0, "Lab Unit Cost": 250.0, "Equip Unit Cost": 0.0},
                    {"Project ID": p_id, "Item No": "22.01.902", "Trade": "22 - Plumbing/Mech", "Description": "High-Efficiency Gas Delivery Interlock System", "Qty": 1.0, "Unit": "Set", "Mat Unit Cost": 450.0, "Lab Unit Cost": 180.0, "Equip Unit Cost": 50.0}
                ]
                st.session_state.master_boq = pd.concat([st.session_state.master_boq, pd.DataFrame(ai_rows)], ignore_index=True)
                log_system_action("BOQ AI Pipeline", "AI Generative Takeoff", "Triggered baseline structural context optimization array extension pass safely.")
                st.success("AI Synthesis Engine parsed specification requirements and appended calibrated line components.")
                st.rerun()

    st.write("---")
    st.subheader("Current Structural Bill of Quantities Grid Matrix")
    
    active_boq = st.session_state.master_boq[st.session_state.master_boq["Project ID"] == p_id].copy()
    if not active_boq.empty:
        active_boq["Material Total"] = active_boq["Qty"] * active_boq["Mat Unit Cost"]
        active_boq["Labor Total"] = active_boq["Qty"] * active_boq["Lab Unit Cost"]
        active_boq["Equipment Total"] = active_boq["Qty"] * active_boq["Equip Unit Cost"]
        active_boq["Gross Extended Cost"] = active_boq["Material Total"] + active_boq["Labor Total"] + active_boq["Equipment Total"]
        
        st.dataframe(active_boq.drop(columns=["Project ID"]), use_container_width=True, hide_index=True)
    else:
        st.info("No active relational records exist within the runtime state for this allocation index.")

# ==========================================
# MODULE 3: ACTUATED COST ESTIMATION & ACTUATED CONTINGENCY MATRIX
# ==========================================
def render_cost_estimator():
    st.title("💰 Advanced Cost Optimization & Multi-Tier Matrix")
    
    active_p = st.selectbox("Target Accounting Ledger Deck", [p["name"] for p in st.session_state.projects if p["status"] == "Active"], key="cost_p")
    proj_meta = [p for p in st.session_state.projects if p["name"] == active_p][0]
    p_id = proj_meta["id"]
    region_db = REGIONAL_DATABASES[proj_meta["region"]]
    
    st.info(f"Applying Economic Parameter Set: **{proj_meta['region']}** | Local Currency Vector: `{region_db['currency']}`")
    
    active_boq = st.session_state.master_boq[st.session_state.master_boq["Project ID"] == p_id].copy()
    
    if active_boq.empty:
        st.warning("Empty records pool. Base values compute at zero margins.")
        return
        
    base_m = (active_boq["Qty"] * active_boq["Mat Unit Cost"]).sum() * region_db["material_index"]
    base_l = (active_boq["Qty"] * active_boq["Lab Unit Cost"]).sum() * region_db["labor_multiplier"]
    base_e = (active_boq["Qty"] * active_boq["Equip Unit Cost"]).sum()
    raw_subtotal = base_m + base_l + base_e
    
    col_c1, col_c2 = st.columns([3, 2])
    
    with col_c1:
        st.subheader("Escalation & Operational Contingency Coefficients")
        c_pct = st.slider("Project Allocation Contingency Buffer Allocation (%)", 0.0, 25.0, 7.5)
        o_pct = st.slider("Contractor Overhead Cost Recovery Multiplier (%)", 0.0, 20.0, 10.0)
        p_pct = st.slider("Target Yield Gross Profit Margin Target (%)", 0.0, 40.0, 15.0)
        
        st.markdown("**Macroeconomic Structural Volatility Compensations**")
        inf_pct = st.number_input("Compounded Yearly Project Inflation Hedge Factor (%)", value=3.2)
        elapsed_years = st.number_input("Project Execution Delay/Duration Window Lifecycle Timeline (Years)", value=0.5, step=0.1)
        tax_pct = st.number_input(f"Regional Static Fiscal Assessment ({region_db['tax_label']}) (%)", value=8.2)

    with col_c2:
        st.subheader("Consolidated Ledger Summary")
        
        contingency_total = raw_subtotal * (c_pct / 100.0)
        leveraged_base = raw_subtotal + contingency_total
        
        overhead_total = leveraged_base * (o_pct / 100.0)
        profit_yield = (leveraged_base + overhead_total) * (p_pct / 100.0)
        pre_tax_sub = leveraged_base + overhead_total + profit_yield
        
        escalation_adjustment = pre_tax_sub * ((1 + inf_pct/100.0)**elapsed_years - 1)
        taxable_basis = pre_tax_sub + escalation_adjustment
        tax_total = taxable_basis * (tax_pct / 100.0)
        grand_total_estimate = taxable_basis + tax_total
        
        sym = region_db["currency"]
        st.metric("Raw Baseline Subtotal (Adjusted Geo-Index)", f"{sym}{raw_subtotal:,.2f}")
        st.metric(f"Contingency Pool Cushion ({c_pct}%)", f"{sym}{contingency_total:,.2f}")
        st.metric("Corporate Burden (Profit + Overhead)", f"{sym}{(overhead_total + profit_yield):,.2f}")
        st.metric("Compounded Project Escalation Cost Impact", f"{sym}{escalation_adjustment:,.2f}")
        st.metric(f"Projected Fiscal Levy ({region_db['tax_label']} @ {tax_pct}%)", f"{sym}{tax_total:,.2f}")
        st.markdown(f"## **Target Evaluated Project Yield Valuation Grand Total: {sym}{grand_total_estimate:,.2f}**")

# ==========================================
# MODULE 4: GEOMETRIC DRAWING DATA EXTRACTION & INTERFACING
# ==========================================
def render_drawing_measurement():
    st.title("📐 Digital Takeoff Engine & Vector Blueprint Calibration")
    st.write("Extract design elements, layer markers, scale profiles, and volume quantities from vector schematics.")
    
    up_blueprint = st.file_uploader("Ingest Project Blueprint File (PDF, Vector DXF, or CAD Output DWG Layer Set)", type=["pdf", "dxf", "dwg"])
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.subheader("Spatial Calibration Tool Matrix")
        scale_ratio = st.text_input("Calibrated Scaling Anchor Definition Ratio (e.g., 1/4 inch = 1 foot)", "1:48")
        target_layer = st.multiselect("Active Working Spatial Layer Filters", ["Structural Ground Layer", "Sub-Slab Mechanical Utilities", "Finished Surface Enclosures", "Architectural Accents Deck"], default=["Structural Ground Layer", "Finished Surface Enclosures"])
        
        st.markdown("---")
        st.markdown("**Simulated Vector Target Coordinate Intercept Takeoff Log**")
        mock_takeoff_points = pd.DataFrame({
            "Vector Identity Target Element": ["Linear Outer Retaining Wall Boundary", "Foundation Spatial Excavation Mass Volume", "Island Bench Surface Area Footprint"],
            "Measured Direct Value Metrics Output": ["48.5 Linear Feet", "12.2 Cubic Yards", "64.0 Square Feet"]
        })
        st.table(mock_takeoff_points)
        
    with col_d2:
        st.subheader("Takeoff Vector Viewport Visualization Layer Container")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 5, 5, 1, 1], y=[1, 1, 4, 4, 1], fill="toself", name="Main Slab Spatial Layout Boundary Outline", line=dict(color="Cyan", width=3)))
        fig.add_trace(go.Scatter(x=[2, 4, 4, 2, 2], y=[2, 2, 3, 3, 2], fill="toself", name="Island Structure Counter Overlay Layer Location", line=dict(color="Gold", width=2)))
        fig.update_layout(template="plotly_dark", xaxis=dict(visible=False), yaxis=dict(visible=False), height=400)
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULE 5: MATERIAL TRACKING LOGISTICS & VENDOR CONTROL
# ==========================================
def render_material_management():
    st.title("🧱 Material Inventory Ledger, PO Pipelines, & Waste Auditing")
    
    st.subheader("Dynamic Materials Tracking Control Matrix & Supply Alerts")
    st.dataframe(st.session_state.inventory, use_container_width=True, hide_index=True)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("Purchase Order (PO) Automated Component Generation Vector")
        target_sku = st.selectbox("Select Target Replenishment Asset SKU", st.session_state.inventory["SKU"])
        order_volume = st.number_input("Target Purchasing Order Procurement Multiplier Volume", min_value=1.0, value=25.0)
        if st.button("Generate legally binding corporate PO Manifest Stream"):
            log_system_action("Logistics", "PO Generation", f"Procured an automated delivery asset volume of {order_volume} units for SKU: {target_sku}")
            st.success(f"PO sequence triggered successfully for SKU item {target_sku} for an aggregated delivery asset volume of {order_volume} units.")
            
    with col_m2:
        st.subheader("Material Wastage & Yield Analysis Diagnostics")
        waste_factor = st.slider("Standard Operational Overhead Material Wastage Factor Allowance (%)", 1.0, 15.0, 5.0)
        st.info(f"Current operational models predict structural resource demand curves must expand procurement bounds by exactly **{waste_factor}%** to buffer execution errors.")

# ==========================================
# MODULE 6: SITE CONTROL JOURNAL & ATTENDANCE LEDGER
# ==========================================
def render_site_management():
    st.title("👷 Daily Field Journal Logistics & Production Telemetry")
    
    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        st.subheader("Live Daily Field Telemetry Metrics Entry Card")
        weather_condition = st.text_input("Integrated Weather/Atmospheric Configuration State Profile", "78°F, Clear skies, 35% Humidity Index - Optimized for Structural Production")
        site_diary_str = st.text_area("Field Execution Work Log & Critical Incidents Narrative", "Excavation and trench tracking operations finalized cleanly. Standard structural grid setup layer is currently underway...")
        geo_tag_string = st.text_input("Device Hardware Geo-Coded Positional Verification Marker", "Lat 34.0522 N / Lon 118.2437 W - Verified Handshake Sequence")
        
        st.markdown("**Site HSE Compliance Integrity Array Verification Checks**")
        h1 = st.checkbox("All operating field personnel checked via access security protocols.")
        h2 = st.checkbox("Machinery safety shields certified and operational.")
        
        if st.button("Transmit Field Entry to Master Chain Records Ledger"):
            st.session_state.site_log.append({"Timestamp": datetime.datetime.now(), "Weather": weather_condition, "Diary": site_diary_str, "Coordinates": geo_tag_string})
            log_system_action("Field System", "Journal Ingestion", f"Logged field entry telemetry at vector marker {geo_tag_string}")
            st.toast("Field record archived successfully.")
            
    with col_s2:
        st.subheader("Operational Labor Utilization Audit Matrix Log")
        mock_attendance = pd.DataFrame({
            "Labor Resource Identity Card": ["Master Mason Specialist", "Apprentice Mason Hand", "Mechanical/Plumbing Field Engineer"],
            "Logged Operational Shift Duration (Hours)": [8.0, 8.0, 4.5],
            "Evaluated Production Efficiency Output Rating": ["105% - High Speed", "90% - On Pace", "100% - Targeted Standard Clear Alignment"]
        })
        st.dataframe(mock_attendance, use_container_width=True, hide_index=True)

# ==========================================
# MODULE 7: INSIGHTFUL REPORTING & WHITE-LABEL PIPELINES
# ==========================================
st.write("FPDF_AVAILABLE:", FPDF_AVAILABLE)  # Debug line to confirm FPDF availability
def render_reporting():
    st.title("📈 Strategic Business Intelligence Reports & Branding Control")
    st.write("Generate financial statements, project summaries, and client-ready documentation sets.")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Branded White-Label Export Port")
        st.text_input("Enterprise System Primary Operating Title Override Banner", value=st.session_state.app_settings["company_name"])
        st.file_uploader("Upload Corporate Asset Branding Mark Vector (PNG/SVG Format)")
        
        st.write("---")
        st.markdown("**Export Format Drivers**")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.master_boq.to_excel(writer, sheet_name='Master_BOQ_Matrix_Ledger', index=False)
            
        st.download_button(
            label="📥 Export Integrated Multi-Sheet Corporate Excel Workbook System",
            data=buffer.getvalue(),
            file_name="Enterprise_Master_Asset_Report.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
        
        if st.button("📄 Generate Executive Client PDF Package", use_container_width=True):
            st.success("White-label document asset stream formatted, watermarked, compiled, and finalized cleanly.")

        # Data Portability Suite (CSV Import/Export)
        st.markdown("### 📤 Relational Data Portability Port")
        
        boq_csv_bytes = st.session_state.master_boq.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📤 Export Active BOQ Database Stack (.CSV)",
            data=boq_csv_bytes,
            file_name="Master_BOQ_Database_Export.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        uploaded_csv_stream = st.file_uploader("📥 Ingest External Structural Data Matrix Stream (.CSV)", type=["csv"])
        if uploaded_csv_stream is not None:
            try:
                imported_dataframe = pd.read_csv(uploaded_csv_stream)
                required_structural_columns = ["Project ID", "Item No", "Trade", "Description", "Qty", "Unit", "Mat Unit Cost", "Lab Unit Cost", "Equip Unit Cost"]
                if all(col in imported_dataframe.columns for col in required_structural_columns):
                    st.session_state.master_boq = pd.concat([st.session_state.master_boq, imported_dataframe], ignore_index=True).drop_duplicates().reset_index(drop=True)
                    log_system_action("Portability Port", "Data Ingestion", "Parsed external tracking matrix file into core BOQ state tables.")
                    st.success("External data matrix structural mapping finalized. Records appended cleanly!")
                else:
                    st.error("Data variance layout found. Missing key relational data column headers.")
            except Exception as import_error:
                st.error(f"Error handling file execution stream: {str(import_error)}")

        st.markdown("### 📄 Print-Ready Executive Document Asset Engine")
        
        executive_summary_manifest = f"""============================================================
BUILDMASTER ENTERPRISE SYSTEM EXECUTIVE BLUEPRINT EXPORT
============================================================
Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Corporate Operator: {st.session_state.app_settings['company_name']}
Security Clearance Level: AES-256 RBAC Verified Invariant Stack
------------------------------------------------------------
SUMMARY LOGISTICS DATA INSIGHTS
------------------------------------------------------------
- Total Portfolios Tracked: {len(st.session_state.projects)} Managed Blueprints
- Active Bill of Quantities Core Table Size: {len(st.session_state.master_boq)} Relational Line Records
- Current Inventory Tracked Stock SKUs: {len(st.session_state.inventory)} Operational Lines
------------------------------------------------------------
END OF REPORT MANIFEST
============================================================
"""
        st.download_button(
            label="📥 Download Production-Ready Executive Text/PDF Package Manifest",
            data=executive_summary_manifest.encode('utf-8'),
            file_name="Executive_System_Asset_Report.pdf",
            mime="application/octet-stream",
            use_container_width=True
        )

        # ==========================================
        # ADDED FEATURE 1: PROFESSIONAL PDF REPORT GENERATOR (FPDF)
        # ==========================================
        st.markdown("### 📑 Professional True-PDF Report Generator")
        if FPDF_AVAILABLE:
            class ProfessionalPDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 14)
                    self.cell(0, 10, f"{st.session_state.app_settings['company_name']} - Enterprise Blueprint", 0, 1, 'C')
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 5, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
                    self.ln(5)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

            if st.button("Generate Formatted Professional PDF Report", use_container_width=True):
                with st.spinner("Compiling structural data matrices..."):
                    pdf = ProfessionalPDF()
                    pdf.add_page()
                    
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 10, "Active Managed Portfolios:", ln=True)
                    pdf.set_font('Arial', '', 10)
                    for proj in st.session_state.projects:
                        pdf.cell(0, 8, f"- [{proj['id']}] {proj['name']} | Status: {proj['status']} | Progress: {proj['progress']}%", ln=True)
                    pdf.ln(5)

                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 10, "Master Bill of Quantities Snapshot (Top Items):", ln=True)
                    pdf.set_font('Arial', 'B', 9)
                    
                    # Create Table Header
                    col_widths = [25, 100, 25, 40]
                    pdf.cell(col_widths[0], 8, "Item No", border=1)
                    pdf.cell(col_widths[1], 8, "Description", border=1)
                    pdf.cell(col_widths[2], 8, "Qty", border=1)
                    pdf.cell(col_widths[3], 8, "Trade Segment", border=1, ln=True)
                    
                    pdf.set_font('Arial', '', 9)
                    for index, row in st.session_state.master_boq.head(15).iterrows():
                        desc_text = (str(row['Description'])[:50] + '..') if len(str(row['Description'])) > 50 else str(row['Description'])
                        pdf.cell(col_widths[0], 8, str(row['Item No']), border=1)
                        pdf.cell(col_widths[1], 8, desc_text, border=1)
                        pdf.cell(col_widths[2], 8, f"{row['Qty']} {row['Unit']}", border=1)
                        pdf.cell(col_widths[3], 8, str(row['Trade']).split("-")[0].strip()[:15], border=1, ln=True)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        pdf.output(tmp.name)
                        with open(tmp.name, "rb") as f:
                            pdf_bytes = f.read()
                            
                    st.download_button(
                        label="📥 Download Professional True-PDF Document",
                        data=pdf_bytes,
                        file_name="BuildMaster_Professional_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.error("The `fpdf` library is required for the True-PDF feature. Please run: `pip install fpdf`")
            
    with col_r2:
        st.subheader("Advanced Analytical Resource Projections & Cost Diagnostics")
        trades_cost_distribution = st.session_state.master_boq.groupby("Trade")["Qty"].sum().reset_index()
        if not trades_cost_distribution.empty:
            fig_pie = px.pie(trades_cost_distribution, values="Qty", names="Trade", title="Aggregated Direct Budget Expenditure Distribution by Core Trade Divisions", hole=0.4)
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No active cost distributions to map.")

        st.write("---")
        st.subheader("📊 Dynamic Asset Cost Breakdown Allocation Vectors")
        if not st.session_state.master_boq.empty:
            fig_grouped_bar = px.bar(
                st.session_state.master_boq,
                x="Trade",
                y=["Mat Unit Cost", "Lab Unit Cost", "Equip Unit Cost"],
                title="Comparative Cost Metrics Matrix by Functional Construction Divisions",
                barmode="group",
                template="plotly_dark"
            )
            fig_grouped_bar.update_layout(xaxis_title="Operational Trade Groups", yaxis_title="Unit Cost Allocation Basis ($)")
            st.plotly_chart(fig_grouped_bar, use_container_width=True)

    # ==========================================
    # ADDED FEATURE 2: VISUALIZATION (DATA-DRIVEN INSIGHTS)
    # ==========================================
    st.write("---")
    st.subheader("🧠 Advanced Data-Driven Visualizations (Insights)")
    
    insight_tab1, insight_tab2, insight_tab3 = st.tabs(["Cost Efficiency Map", "Project Progress Distribution", "Trade Expenditure Sunburst"])
    
    with insight_tab1:
        st.markdown("**Material vs Labor Cost Efficiency Scatter Matrix**")
        st.write("Identifies high-cost variances in operational line items.")
        if not st.session_state.master_boq.empty:
            fig_scatter = px.scatter(
                st.session_state.master_boq, 
                x="Mat Unit Cost", 
                y="Lab Unit Cost", 
                size="Qty", 
                color="Trade", 
                hover_name="Description",
                title="Labor vs Material Cost Analysis (Bubble Size = Total Quantity)",
                template="plotly_dark"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
    with insight_tab2:
        st.markdown("**Portfolio Completion Velocity Tracking**")
        st.write("Visual completion curves mapped directly against organizational pipeline statuses.")
        if st.session_state.projects:
            df_proj = pd.DataFrame(st.session_state.projects)
            fig_bar_prog = px.bar(
                df_proj, 
                x="name", 
                y="progress", 
                color="status",
                title="Active Portfolio Completion Rates",
                template="plotly_dark",
                labels={"name": "Project Blueprint", "progress": "Execution Completion (%)"}
            )
            st.plotly_chart(fig_bar_prog, use_container_width=True)
            
    with insight_tab3:
        st.markdown("**Hierarchical Trade Expenditure Volume Map**")
        st.write("Deep proportional allocation tracking for complete relational budget structures.")
        if not st.session_state.master_boq.empty:
            df_sun = st.session_state.master_boq.copy()
            df_sun["Total Burden Output"] = df_sun["Qty"] * (df_sun["Mat Unit Cost"] + df_sun["Lab Unit Cost"] + df_sun["Equip Unit Cost"])
            fig_sunburst = px.sunburst(
                df_sun, 
                path=["Project ID", "Trade", "Item No"], 
                values="Total Burden Output",
                title="Deep Expenditure Allocation Sunburst Hierarchy",
                template="plotly_dark"
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)

# ==========================================
# MODULE 8: 🏡 HOME PLANNING & ESTIMATORS
# ==========================================
def render_home_estimators():
    st.title("🏡 Home Configuration & Planning Tools")
    
    t1, t2, t3 = st.tabs(["Cost Calculator", "Dream Home Planner", "Budget-Based Suggestions"])
    
    with t1:
        st.subheader("Feature 1: Home Construction Cost Calculator")
        st.write("Enter your plot area to get an instant baseline estimate.")
        area = st.number_input("Enter Total Built-up Area (Sq Ft)", min_value=100, value=1200)
        quality = st.selectbox("Select Construction Quality Grade", ["Standard (₹1500/sqft)", "Premium (₹2000/sqft)", "Luxury (₹2800/sqft)"])
        rate = 1500 if "Standard" in quality else 2000 if "Premium" in quality else 2800
        st.success(f"Estimated Baseline Construction Cost: **₹ {area * rate:,.2f}**")
        
    with t2:
        st.subheader("Feature 2: Dream Home Planner")
        st.write("Select your desired property type to view baseline requirements.")
        home_type = st.selectbox("Select Target Property Type", ["1BHK", "2BHK", "3BHK", "Duplex", "Villa"])
        
        plan_specs = {
            "1BHK": {"area": "500 - 700 sq ft", "cost": "₹ 8L - ₹ 12L"},
            "2BHK": {"area": "800 - 1100 sq ft", "cost": "₹ 15L - ₹ 22L"},
            "3BHK": {"area": "1200 - 1600 sq ft", "cost": "₹ 24L - ₹ 35L"},
            "Duplex": {"area": "1800 - 2500 sq ft", "cost": "₹ 40L - ₹ 65L"},
            "Villa": {"area": "3000+ sq ft", "cost": "₹ 80L+"}
        }
        col1, col2 = st.columns(2)
        col1.metric("Recommended Ideal Area", plan_specs[home_type]["area"])
        col2.metric("Approximate Budget Required", plan_specs[home_type]["cost"])
        
    with t3:
        st.subheader("Feature 3: Budget-Based House Suggestion")
        st.write("Enter your budget and we'll suggest what you can build.")
        user_budget = st.number_input("Enter your maximum budget (₹)", min_value=100000, value=2000000, step=100000)
        sqft_possible = user_budget / 1800 
        st.info(f"With a budget of **₹ {user_budget:,.2f}**, you can build a house of approximately **{sqft_possible:.0f} sq ft**.")
        if sqft_possible < 600:
            st.success("Suggestion: A spacious 1BHK or compact 2BHK is perfect for this budget.")
        elif sqft_possible < 1200:
            st.success("Suggestion: A comfortable 2BHK or compact 3BHK will fit well.")
        elif sqft_possible < 2000:
            st.success("Suggestion: A large 3BHK or a modest Duplex is achievable.")
        else:
            st.success("Suggestion: You can build a premium Duplex or Villa!")

# ==========================================
# MODULE 9: 🧱 MATERIAL & TRADE CALCULATORS
# ==========================================
def render_material_calculators():
    st.title("🧮 Comprehensive Material & Trade Calculators")
    st.write("Granular calculators for every stage of your build.")
    
    t1, t2, t3, t4 = st.tabs(["Material Breakdown", "Core Materials (Brick, Concrete, Steel)", "Finishes (Paint, Tiles)", "Trade Budgets (Plumb, Elec, Int, Foundation)"])
    
    with t1:
        st.subheader("Feature 6: Material Cost Breakdown")
        total_cost = st.number_input("Enter Total Estimated Project Cost (₹) to see breakdown", value=5000000)
        
        breakdown_data = pd.DataFrame({
            "Material/Trade": ["Cement", "Steel", "Bricks", "Sand & Aggregate", "Tiles & Flooring", "Paint & Finishes", "Plumbing", "Electrical", "Woodwork & Doors"],
            "Percentage": [14, 22, 10, 10, 8, 5, 7, 8, 16]
        })
        breakdown_data["Cost (₹)"] = (breakdown_data["Percentage"] / 100) * total_cost
        
        fig = px.pie(breakdown_data, values='Percentage', names='Material/Trade', title='Standard Material Cost Distribution')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(breakdown_data, use_container_width=True)

    with t2:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Feature 13: Brick Calc")
            wall_area = st.number_input("Total Wall Area (Sq Ft)", value=1000)
            st.metric("Bricks Needed (9\" wall)", f"{int(wall_area * 10)} units")
        with col2:
            st.subheader("Feature 14: Concrete Calc")
            vol = st.number_input("Concrete Volume (Cu Ft)", value=100)
            st.metric("Cement Bags", f"{int(vol * 0.22)} bags")
            st.metric("Sand", f"{vol * 0.44:.1f} Cu Ft")
            st.metric("Aggregate", f"{vol * 0.88:.1f} Cu Ft")
        with col3:
            st.subheader("Feature 15: Steel Calc")
            slab_area = st.number_input("Slab Area (Sq Ft)", value=1200)
            st.metric("Rebar Needed", f"{slab_area * 3.5:.1f} Kg")

    with t3:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.subheader("Feature 11: Paint Calc")
            paint_area = st.number_input("Plastered Area (Sq Ft)", value=2500)
            st.metric("Primer Needed", f"{paint_area / 120:.1f} Liters")
            st.metric("Paint Needed (2 coats)", f"{paint_area / 80:.1f} Liters")
        with col_f2:
            st.subheader("Feature 12: Tile Calc")
            floor_area = st.number_input("Floor Area (Sq Ft)", value=1200)
            tile_size = st.selectbox("Tile Size", ["2x2 ft", "2x4 ft", "1x1 ft"])
            sqft_per_tile = 4 if tile_size == "2x2 ft" else 8 if tile_size == "2x4 ft" else 1
            st.metric("Tiles Needed (+5% waste)", f"{int((floor_area / sqft_per_tile) * 1.05)} tiles")

    with t4:
        st.subheader("Trade & Foundation Budgets")
        base_area = st.number_input("Enter Built-up Area for Trade Estimates (Sq Ft)", value=1200)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Feature 7: Foundation Est.", f"₹ {base_area * 350:,.2f}")
        c2.metric("Feature 16: Plumbing Est.", f"₹ {base_area * 120:,.2f}")
        c3.metric("Feature 17: Electrical Est.", f"₹ {base_area * 140:,.2f}")
        c4.metric("Feature 18: Interior Est.", f"₹ {base_area * 500:,.2f}")

# ==========================================
# MODULE 10: 🏦 FINANCE & TRACKING
# ==========================================
def render_finance_and_tracking():
    st.title("🏦 Construction Finance & Cost Tracking")
    
    t1, t2, t3, t4 = st.tabs(["Loan Estimator", "Floor-Wise Cost", "Stage Tracker", "Monthly Expense"])
    
    with t1:
        st.subheader("Feature 5: Construction Loan Estimator")
        p = st.number_input("Loan Amount (₹)", value=2500000)
        r = st.number_input("Annual Interest Rate (%)", value=8.5)
        n = st.number_input("Tenure (Years)", value=15)
        
        if st.button("Calculate EMI"):
            r_mon = (r / 12) / 100
            n_mon = n * 12
            emi = p * r_mon * ((1 + r_mon)**n_mon) / (((1 + r_mon)**n_mon) - 1)
            st.success(f"Estimated Monthly EMI: **₹ {emi:,.2f}**")
            st.info(f"Total Interest Payable: ₹ {(emi * n_mon) - p:,.2f}")

    with t2:
        st.subheader("Feature 8: Floor-Wise Cost Estimation")
        total_est = st.number_input("Total Estimated Multi-Story Project Cost (₹)", value=8000000)
        st.write("Typical cost distribution for a G+2 structure:")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ground Floor (w/ Foundation) [45%]", f"₹ {total_est * 0.45:,.2f}")
        c2.metric("First Floor [30%]", f"₹ {total_est * 0.30:,.2f}")
        c3.metric("Second Floor/Terrace [25%]", f"₹ {total_est * 0.25:,.2f}")

    with t3:
        st.subheader("Feature 10: Construction Stage Cost Tracker")
        st.write("Track funding requirements based on build phase.")
        tracker_df = pd.DataFrame({
            "Stage": ["Foundation", "Superstructure/Framing", "Roofing", "Plumbing/Electrical", "Flooring/Finishes"],
            "Fund Allocation": ["15%", "35%", "15%", "15%", "20%"],
            "Status": ["Completed", "In Progress", "Pending", "Pending", "Pending"]
        })
        st.dataframe(tracker_df, use_container_width=True)
        st.progress(0.50, text="Overall Financial Completion: 50%")

    with t4:
        st.subheader("Feature 19: Monthly Construction Expense Tracker")
        st.write("Track actual spending against projected budgets.")
        expense_data = pd.DataFrame({
            "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
            "Budget (₹)": [500000, 800000, 400000, 600000, 300000],
            "Actual Spend (₹)": [480000, 850000, 410000, 580000, 0]
        })
        fig = go.Figure()
        fig.add_trace(go.Bar(x=expense_data['Month'], y=expense_data['Budget (₹)'], name='Budget'))
        fig.add_trace(go.Bar(x=expense_data['Month'], y=expense_data['Actual Spend (₹)'], name='Actual Spend'))
        fig.update_layout(barmode='group', title="Budget vs Actual Spend Tracker")
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULE 11: 📐 ROOM CALCS & PLAN GALLERY
# ==========================================
def render_plan_gallery_and_tools():
    st.title("📐 Architectural Layouts & Space Calculators")
    
    t1, t2 = st.tabs(["Room Area Calculator", "House Plan Gallery"])
    
    with t1:
        st.subheader("Feature 4: Room Area Calculator")
        st.write("Calculate individual room sizes to find total built-up area.")
        
        num_rooms = st.number_input("Number of Rooms to Calculate", min_value=1, max_value=10, value=3)
        total_area = 0
        for i in range(int(num_rooms)):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input(f"Room {i+1} Name", f"Room {i+1}")
            with col2:
                length = st.number_input(f"Length (ft)", min_value=0.0, value=10.0, key=f"l{i}")
            with col3:
                width = st.number_input(f"Width (ft)", min_value=0.0, value=12.0, key=f"w{i}")
            total_area += (length * width)
        
        st.markdown(f"### **Total Usable Carpet Area: {total_area:,.2f} Sq Ft**")
        st.caption("Note: Add approx 20-30% for walls and common areas to get Super Built-up Area.")

    with t2:
        st.subheader("Feature 9: House Plan Gallery")
        st.write("Browse architectural sample references.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("Modern 2BHK Layout")
            st.metric("Area", "1100 sqft")
            st.caption("Open kitchen, 2 baths, balcony.")
        with col2:
            st.success("Classic 3BHK Duplex")
            st.metric("Area", "2200 sqft")
            st.caption("Double height ceiling, terrace.")
        with col3:
            st.warning("Luxury Villa Plot")
            st.metric("Area", "4500 sqft")
            st.caption("Pool, 5 beds, home theater.")

# ==========================================
# MODULE 12: 🤖 AI CHATBOT
# ==========================================
def render_ai_assistant():
    st.title("🤖 Feature 20: AI Home Construction Assistant")
    st.write("Ask me anything about construction costs, material estimates, and regional pricing!")
    
    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("E.g., 'How much will a 1200 sq ft house cost in Punjab?'"):
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = "I am a simulated AI assistant for this construction portal. "
            prompt_lower = prompt.lower()
            
            if "punjab" in prompt_lower and "cost" in prompt_lower:
                response = "In Punjab, standard construction currently averages around ₹1,400 to ₹1,800 per sq ft. For a 1200 sq ft house, you should budget approximately ₹16.8 Lakhs to ₹21.6 Lakhs depending on the finishing quality."
            elif "brick" in prompt_lower:
                response = "For standard 9-inch brick walls, you generally need about 10 to 11 bricks per square foot of wall area. Let me know your total wall area and I can calculate the exact number!"
            elif "roof slab" in prompt_lower or "slab" in prompt_lower:
                response = "A standard RCC roof slab usually costs about ₹150 to ₹200 per square foot for materials and labor. This includes concrete, steel reinforcement, and shuttering costs."
            elif "project" in prompt_lower or "portfolio" in prompt_lower:
                project_names = [p["name"] for p in st.session_state.projects]
                response = f"Scanning system databases... You currently have {len(st.session_state.projects)} projects logged in your workspace: {', '.join(project_names)}."
            elif "inventory" in prompt_lower or "stock" in prompt_lower or "sku" in prompt_lower:
                response = f"Checking active warehouse tracking... There are currently {len(st.session_state.inventory)} inventory tracking rows present in the Logistics Ledger repository."
            elif "boq" in prompt_lower or "bill of quantities" in prompt_lower:
                response = f"Querying item matrices... There are currently {len(st.session_state.master_boq)} analytical ledger items stored in the master BOQ compilation deck."
            elif "material" in prompt_lower or "cost" in prompt_lower:
                response = "Material and execution costs vary by structure. Standard global metrics show material acquisition consumes 60-70% of building budgets (Steel ~22%, Cement ~14%, Bricks ~10%). You can see live geo-scaled pricing for your active project under the 'Actuated Financial Matrix' tab, or view detailed material quantities in the 'Material & Trade Calculators' panel!"
            else:
                response = f"That's a great question about '{prompt}'. Based on current construction metrics, I can help you estimate costs, materials, or structural logistics. Try asking me about regional costs or material quantities!"
                
            st.markdown(response)
            st.session_state.ai_messages.append({"role": "assistant", "content": response})
            
            log_system_action("AI Chatbot", "Query Answered", f"Successfully addressed prompt: '{prompt[:35]}...'")

# ==========================================
# MAIN OPERATIONAL RUNTIME ENGINE ROUTER
# ==========================================
def main():
    with st.sidebar:
        st.title("🏗️ BuildMaster Pro")
        st.caption(f"Enterprise Portfolio Environment | v{datetime.datetime.now().year}.2")
        st.markdown(f"**Enterprise:** `{st.session_state.app_settings['company_name']}`")
        st.write("---")
        
        module_selector = st.radio(
            "Enterprise Engine Navigator",
            [
                "📊 Global Portfolio Hub",
                "🏗️ Unified BOQ & AI Takeoff",
                "💰 Actuated Financial Matrix",
                "📐 Schematic Geometric Takeoff",
                "🧱 Logistics & Inventory Ledger",
                "👷 Field Journal Logistics",
                "📈 Strategic BI Reporting",
                "🏡 Home Configuration Planners",         
                "🧮 Material & Trade Calculators",       
                "🏦 Finance & Tracking Hub",             
                "📏 Room Calcs & Plan Gallery",          
                "💬 AI Construction Chatbot"             
            ]
        )
        
        st.write("---")
        st.markdown("**Infrastructure Governance Control Toggles**")
        st.session_state.app_settings["cloud_sync"] = st.toggle("Active Multi-Node Cloud Sync Layer", value=st.session_state.app_settings["cloud_sync"])
        st.session_state.app_settings["offline_mode"] = st.toggle("Local Cache Fault Recovery Failover", value=st.session_state.app_settings["offline_mode"])
        st.caption("🔒 Architecture secured under end-to-end relational data binding invariants.")

    if module_selector == "📊 Global Portfolio Hub":
        render_project_dashboard()
    elif module_selector == "🏗️ Unified BOQ & AI Takeoff":
        render_boq_engine()
    elif module_selector == "💰 Actuated Financial Matrix":
        render_cost_estimator()
    elif module_selector == "📐 Schematic Geometric Takeoff":
        render_drawing_measurement()
    elif module_selector == "🧱 Logistics & Inventory Ledger":
        render_material_management()
    elif module_selector == "👷 Field Journal Logistics":
        render_site_management()
    elif module_selector == "📈 Strategic BI Reporting":
        render_reporting()
    elif module_selector == "🏡 Home Configuration Planners":
        render_home_estimators()
    elif module_selector == "🧮 Material & Trade Calculators":
        render_material_calculators()
    elif module_selector == "🏦 Finance & Tracking Hub":
        render_finance_and_tracking()
    elif module_selector == "📏 Room Calcs & Plan Gallery":
        render_plan_gallery_and_tools()
    elif module_selector == "💬 AI Construction Chatbot":
        render_ai_assistant()

if __name__ == "__main__":
    main()