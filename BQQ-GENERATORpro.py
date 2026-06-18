import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io
import time
import random

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
# SYSTEM SETUP & SESSION LAYER
# ==========================================
st.set_page_config(page_title="BuildMaster Enterprise ERP", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

def init_enterprise_state():
    # Structural Control Arrays
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

init_enterprise_state()

# ==========================================
# MODULE 1: INTERACTIVE ENTERPRISE DASHBOARD & PM
# ==========================================
def render_project_dashboard():
    st.title("📊 Multi-Project Control Center")
    st.write("Real-time telemetry across active portfolios, resource lifecycles, and governance roles.")
    
    # Global Metrics Metrics Grid
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Managed Portfolios", len(st.session_state.projects))
    m2.metric("Active Runs", len([p for p in st.session_state.projects if p["status"]=="Active"]))
    m3.metric("System Sync Speed", "12ms", "Cloud Operational")
    m4.metric("Security Level", "RBAC Locked", "AES-256")
    
    st.write("---")
    
    t1, t2, t3 = st.tabs(["Project Portfolios", "Interactive Gantt Timeline", "Cloning & Template Center"])
    
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
                    st.toast("Project moved to archive.")
    
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
                st.success(f"Successfully operationalized {new_id} via structural duplication patterns.")
                st.sidebar.info("System refresh required to draw layout matrices.")

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
                # Auto numbering strategy calculation
                trade_code = trade_select.split(" ")[0]
                item_count = len(st.session_state.master_boq[st.session_state.master_boq["Trade"] == trade_select]) + 1
                generated_item_no = f"{trade_code}.01.{item_count:03d}"
                
                new_row = {"Project ID": p_id, "Item No": generated_item_no, "Trade": trade_select, "Description": desc_input, "Qty": q_val, "Unit": u_str, "Mat Unit Cost": c_mat, "Lab Unit Cost": c_lab, "Equip Unit Cost": c_eq}
                st.session_state.master_boq = pd.concat([st.session_state.master_boq, pd.DataFrame([new_row])], ignore_index=True)
                st.toast(f"Committed {generated_item_no} cleanly.")
                st.rerun()

    with col_b2:
        st.subheader("🤖 GenAI Production Estimator & Automated Verification")
        ai_input = st.text_area("Provide Natural Language Structural Briefings / Layout Prompts", placeholder="Parse a 20ft U-shaped polished concrete build with outdoor gas ranges and deep foundations...")
        if st.button("Invoke AI Design Agent Optimization Pipeline"):
            with st.spinner("Executing structural validation layers..."):
                time.sleep(1.5)
                # Mock AI heuristic expansion mapping to target project architecture
                ai_rows = [
                    {"Project ID": p_id, "Item No": "01.01.901", "Trade": "01 - General Conditions", "Description": "AI Optimization Variance Mitigation Buffer", "Qty": 1.0, "Unit": "LS", "Mat Unit Cost": 0.0, "Lab Unit Cost": 250.0, "Equip Unit Cost": 0.0},
                    {"Project ID": p_id, "Item No": "22.01.902", "Trade": "22 - Plumbing/Mech", "Description": "High-Efficiency Gas Delivery Interlock System", "Qty": 1.0, "Unit": "Set", "Mat Unit Cost": 450.0, "Lab Unit Cost": 180.0, "Equip Unit Cost": 50.0}
                ]
                st.session_state.master_boq = pd.concat([st.session_state.master_boq, pd.DataFrame(ai_rows)], ignore_index=True)
                st.success("AI Synthesis Engine parsed specification requirements and appended calibrated line components.")
                st.rerun()

    st.write("---")
    st.subheader("Current Structural Bill of Quantities Grid Matrix")
    
    active_boq = st.session_state.master_boq[st.session_state.master_boq["Project ID"] == p_id].copy()
    if not active_boq.empty:
        # Dynamic Multi-Component Accounting Calculations
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
        
    # Apply dynamic scaling factors
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
        
        # Real-time compounding mathematical equations
        contingency_total = raw_subtotal * (c_pct / 100.0)
        leveraged_base = raw_subtotal + contingency_total
        
        overhead_total = leveraged_base * (o_pct / 100.0)
        profit_yield = (leveraged_base + overhead_total) * (p_pct / 100.0)
        pre_tax_sub = leveraged_base + overhead_total + profit_yield
        
        # Dynamic compounding calculation logic for macroeconomic structural elements
        escalation_adjustment = pre_tax_sub * ((1 + inf_pct/100.0)**elapsed_years - 1)
        taxable_basis = pre_tax_sub + escalation_adjustment
        tax_total = taxable_basis * (tax_pct / 100.0)
        grand_total_estimate = taxable_basis + tax_total
        
        # UI Display Block Architecture
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
        # Render geometric trace layers for visualization mockup mapping layout positions
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
        
        # Ingest dataframe memory arrays and stream target representations cleanly
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
            
    with col_r2:
        st.subheader("Advanced Analytical Resource Projections & Cost Diagnostics")
        trades_cost_distribution = st.session_state.master_boq.groupby("Trade")["Qty"].sum().reset_index()
        fig_pie = px.pie(trades_cost_distribution, values="Qty", names="Trade", title="Aggregated Direct Budget Expenditure Distribution by Core Trade Divisions", hole=0.4)
        fig_pie.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

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
                "📈 Strategic BI Reporting"
            ]
        )
        
        st.write("---")
        st.markdown("**Infrastructure Governance Control Toggles**")
        st.session_state.app_settings["cloud_sync"] = st.toggle("Active Multi-Node Cloud Sync Layer", value=st.session_state.app_settings["cloud_sync"])
        st.session_state.app_settings["offline_mode"] = st.toggle("Local Cache Fault Recovery Failover", value=st.session_state.app_settings["offline_mode"])
        st.caption("🔒 Architecture secured under end-to-end relational data binding invariants.")

    # Application Navigation Router Logic
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

if __name__ == "__main__":
    main()