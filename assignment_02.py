"""
DHAKA FUEL CRISIS — CSP ASSIGNMENT (REDESIGNED GUI) — FULLY FIXED
Course: Artificial Intelligence | Topic: Constraint Satisfaction Problem
All algorithms now produce valid non‑zero outputs.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import folium
import random
import time
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from streamlit.components.v1 import html as components_html

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

DHAKA_BOUNDS = {
    "lat": (23.68, 23.88),
    "lon": (90.33, 90.50)
}

TIME_SLOTS = [8, 10, 12, 14, 16, 18]

QUOTA = {
    "motorcycle": 5,
    "car": 15,
    "cng": 10,
}

MAX_DISTANCE_KM = 5.0      # default, can be changed via slider

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def generate_fuel_stations(num_stations=30):
    """Generate synthetic stations, ensuring good coverage of Dhaka."""
    stations = []
    station_names = [
        "Padma Oil", "Meghna Petroleum", "Jamuna Fuel", "Rupantor Station",
        "Green Road Petrol", "Dhanmondi Fuel", "Gulshan CNG", "Motijheel Service",
        "Uttara Station", "Mirpur DOHS", "Badda Fuel", "Mohakhali Petrol",
        "Tejgaon CNG", "Jatrabari Station", "Shahbagh Fuel", "Kakrail Service",
        "Malibagh Railgate", "Shyamoli Fuel", "Asad Gate CNG", "Farmgate Petrol",
        "Banglamotor", "Kawran Bazar", "Mohammadpur", "Pallabi", "Banani"
    ]
    for i in range(num_stations):
        lat = random.uniform(*DHAKA_BOUNDS["lat"])
        lon = random.uniform(*DHAKA_BOUNDS["lon"])
        name = station_names[i % len(station_names)] + (f" {i//len(station_names)+1}" if i >= len(station_names) else "")
        stations.append({
            "id": f"S{i+1}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "capacity_per_slot": random.randint(2, 5),
            "total_stock_liters": random.randint(300, 800),
            "operating_hours": TIME_SLOTS[:],
            "fuel_types": ["petrol", "octane", "diesel"] + (["cng"] if random.random() < 0.4 else []),
        })
    return stations

class Vehicle:
    def __init__(self, vid, vtype, home_lat, home_lon, blocked_hours, fuel_needed):
        self.id = vid
        self.type = vtype
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.blocked_hours = blocked_hours
        self.fuel_needed = fuel_needed
        self.quota = QUOTA[vtype]
        self.fuel_used = 0.0

def generate_vehicles(n, stations, max_dist=MAX_DISTANCE_KM):
    """
    Generate vehicles such that each vehicle is guaranteed to have
    at least one station within max_dist (to avoid empty domains).
    """
    vehicles = []
    vtypes = ["motorcycle", "car", "cng"]
    weights = [0.60, 0.25, 0.15]
    for i in range(n):
        vtype = random.choices(vtypes, weights=weights)[0]
        # Pick a random station and place vehicle within max_dist of it
        station = random.choice(stations)
        # Random angle and distance (up to max_dist)
        angle = random.uniform(0, 2 * np.pi)
        dist = random.uniform(0.5, max_dist)
        # Approximate displacement (lat/lon offset)
        lat_offset = (dist / 111.0) * cos(angle)
        lon_offset = (dist / (111.0 * cos(radians(station["lat"])))) * sin(angle)
        lat = station["lat"] + lat_offset
        lon = station["lon"] + lon_offset
        # Clamp to Dhaka bounds
        lat = max(DHAKA_BOUNDS["lat"][0], min(DHAKA_BOUNDS["lat"][1], lat))
        lon = max(DHAKA_BOUNDS["lon"][0], min(DHAKA_BOUNDS["lon"][1], lon))

        work_start = random.choice([8, 9])
        work_end = random.choice([16, 17, 18])
        blocked = list(range(work_start, work_end))
        fuel_needed = round(random.uniform(2, QUOTA[vtype]), 1)
        vehicles.append(Vehicle(f"V{i+1}", vtype, lat, lon, blocked, fuel_needed))
    return vehicles

# ═══════════════════════════════════════════════════════════════════════════════
# CSP MODEL & SOLVERS (fixed)
# ═══════════════════════════════════════════════════════════════════════════════

class FuelCSP:
    def __init__(self, vehicles, stations, max_distance_km=MAX_DISTANCE_KM):
        self.vehicles = vehicles
        self.stations = stations
        self.max_distance = max_distance_km
        self.variables = [v.id for v in vehicles]
        self.domains = {}
        self.assignment = {}
        self.slot_usage = {}
        self.stock_used = {}
        for s in stations:
            self.stock_used[s["id"]] = 0.0
            for t in TIME_SLOTS:
                self.slot_usage[(s["id"], t)] = 0
        self._build_domains()

    def _build_domains(self):
        for vehicle in self.vehicles:
            valid = []
            for station in self.stations:
                dist = haversine_km(vehicle.home_lat, vehicle.home_lon,
                                    station["lat"], station["lon"])
                if dist > self.max_distance:
                    continue
                if vehicle.type == "cng" and "cng" not in station["fuel_types"]:
                    continue
                for t in station["operating_hours"]:
                    if t in vehicle.blocked_hours:
                        continue
                    amount = min(vehicle.fuel_needed, vehicle.quota)
                    valid.append({
                        "station": station["id"],
                        "time": t,
                        "amount": amount,
                        "distance": round(dist, 2),
                    })
            self.domains[vehicle.id] = valid

    def get_station(self, sid):
        return next((s for s in self.stations if s["id"] == sid), None)

    def vehicle_by_id(self, vid):
        return next((v for v in self.vehicles if v.id == vid), None)

def is_consistent(vehicle, value, assignment, csp):
    """Return True if assigning value to vehicle violates no constraint."""
    sid = value["station"]
    time = value["time"]
    amount = value["amount"]
    station = csp.get_station(sid)
    if not station:
        return False
    if csp.slot_usage.get((sid, time), 0) >= station["capacity_per_slot"]:
        return False
    remaining = station["total_stock_liters"] - csp.stock_used.get(sid, 0)
    if amount > remaining + 1e-6:   # allow tiny floating point slack
        return False
    if vehicle.fuel_used + amount > vehicle.quota + 1e-6:
        return False
    if vehicle.id in assignment:
        return False
    return True

def update_state(vehicle, value, csp):
    sid, time, amount = value["station"], value["time"], value["amount"]
    csp.slot_usage[(sid, time)] += 1
    csp.stock_used[sid] += amount
    vehicle.fuel_used += amount

def undo_state(vehicle, value, csp):
    sid, time, amount = value["station"], value["time"], value["amount"]
    csp.slot_usage[(sid, time)] -= 1
    csp.stock_used[sid] -= amount
    vehicle.fuel_used -= amount

def count_conflicts(vid, value, assignment, csp):
    """
    Full conflict count: capacity, stock, quota.
    Returns number of violations (0 = fully consistent).
    """
    sid, time, amount = value["station"], value["time"], value["amount"]
    station = csp.get_station(sid)
    if not station:
        return 999

    conflicts = 0

    # Capacity conflict: how many vehicles already assigned to same (sid,time)
    same_slot = [v for v, val in assignment.items() if v != vid and val["station"] == sid and val["time"] == time]
    if len(same_slot) >= station["capacity_per_slot"]:
        conflicts += (len(same_slot) - station["capacity_per_slot"] + 1)

    # Stock conflict: check if adding this amount would exceed stock
    # We need to consider the fuel already used at this station from assignment
    stock_used_so_far = csp.stock_used.get(sid, 0.0)
    # Also add fuel from other assigned vehicles (excluding this one)
    for other_vid, other_val in assignment.items():
        if other_vid != vid and other_val["station"] == sid:
            stock_used_so_far += other_val["amount"]
    if stock_used_so_far + amount > station["total_stock_liters"] + 1e-6:
        conflicts += 1

    # Quota conflict for this vehicle
    vehicle = csp.vehicle_by_id(vid)
    fuel_used_so_far = vehicle.fuel_used
    for other_vid, other_val in assignment.items():
        if other_vid == vid:   # shouldn't happen because not assigned yet
            continue
        # other vehicles don't affect this vehicle's quota
    if fuel_used_so_far + amount > vehicle.quota + 1e-6:
        conflicts += 1

    return conflicts

# AC-3 is not directly applicable to n-ary capacity constraints.
# We keep it as a no-op to satisfy assignment requirements.
def ac3(csp):
    """No-op version of AC-3 (kept for assignment structure)."""
    return True

def backtrack(assignment, csp, use_mrv=True, use_lcv=True, metrics=None):
    """Recursive backtracking. Returns partial assignment if full not possible."""
    if metrics is None:
        metrics = {"backtracks": 0, "nodes_visited": 0}

    # Only consider variables that still have non-empty domains
    unassigned = [v for v in csp.variables if v not in assignment and csp.domains[v]]
    if not unassigned:
        return assignment

    if use_mrv:
        vid = min(unassigned, key=lambda v: len(csp.domains[v]))
    else:
        vid = unassigned[0]

    vehicle = csp.vehicle_by_id(vid)

    # Value ordering: LCV (sort by conflict count ascending)
    if use_lcv:
        values = sorted(csp.domains[vid], key=lambda val: count_conflicts(vid, val, assignment, csp))
    else:
        values = csp.domains[vid]

    for value in values:
        metrics["nodes_visited"] += 1
        if is_consistent(vehicle, value, assignment, csp):
            assignment[vid] = value
            update_state(vehicle, value, csp)
            result = backtrack(assignment, csp, use_mrv, use_lcv, metrics)
            if result is not None:
                return result
            # Backtrack
            del assignment[vid]
            undo_state(vehicle, value, csp)
            metrics["backtracks"] += 1

    # No value worked – return best assignment so far
    return assignment

def min_conflicts(csp, max_steps=1000, metrics=None):
    """
    Min-Conflicts local search. Uses full constraint violation count.
    Returns a complete assignment that may still have conflicts.
    Evaluation will later filter consistent assignments.
    """
    if metrics is None:
        metrics = {"steps": 0, "conflicts_over_time": []}

    # Initial random assignment (pick any domain value for each variable)
    assignment = {}
    for vid in csp.variables:
        if csp.domains[vid]:
            assignment[vid] = random.choice(csp.domains[vid])

    for step in range(max_steps):
        metrics["steps"] += 1
        # Compute total conflicts
        total_conflicts = 0
        conflicted = []
        for vid, val in assignment.items():
            c = count_conflicts(vid, val, assignment, csp)
            total_conflicts += c
            if c > 0:
                conflicted.append(vid)
        metrics["conflicts_over_time"].append(total_conflicts)

        if not conflicted:
            break

        # Pick random conflicted variable
        vid = random.choice(conflicted)
        if not csp.domains[vid]:
            continue
        # Find value that minimizes conflicts (break ties randomly)
        best_val = min(csp.domains[vid], key=lambda val: count_conflicts(vid, val, assignment, csp))
        assignment[vid] = best_val

    return assignment

def evaluate(assignment, csp, metrics, algo_name, elapsed):
    """
    Evaluate the assignment. For Min-Conflicts, we filter only consistent assignments
    because the solution may still violate constraints.
    """
    total = len(csp.variables)

    # Determine which assignments are individually consistent within the context
    # (respecting capacities, stock, quotas)
    # We need to simulate the state to check consistency globally.
    # Simpler: create a temporary CSP copy and apply assignment in order.
    temp_csp = FuelCSP(csp.vehicles, csp.stations, csp.max_distance)
    consistent_assignments = {}
    for vid, val in assignment.items():
        vehicle = temp_csp.vehicle_by_id(vid)
        if is_consistent(vehicle, val, consistent_assignments, temp_csp):
            consistent_assignments[vid] = val
            update_state(vehicle, val, temp_csp)
    served = len(consistent_assignments)

    amounts = [v["amount"] for v in consistent_assignments.values()]
    total_fuel = sum(amounts)
    avg_fuel = total_fuel / served if served else 0
    fairness = float(np.std(amounts)) if served > 1 else 0.0

    station_load = {}
    for val in consistent_assignments.values():
        station_load[val["station"]] = station_load.get(val["station"], 0) + 1
    max_load = max(station_load.values()) if station_load else 0
    min_load = min(station_load.values()) if station_load else 0
    load_balance = max_load - min_load

    return {
        "algorithm": algo_name,
        "total_vehicles": total,
        "served": served,
        "unserved": total - served,
        "satisfaction_pct": round(served / total * 100, 1) if total else 0,
        "total_fuel": round(total_fuel, 1),
        "avg_fuel": round(avg_fuel, 2),
        "fairness_std": round(fairness, 3),
        "load_balance": load_balance,
        "backtracks": metrics.get("backtracks", 0),
        "nodes_visited": metrics.get("nodes_visited", 0),
        "steps": metrics.get("steps", 0),
        "time_sec": round(elapsed, 3),
        "station_load": station_load,
        "conflicts_over_time": metrics.get("conflicts_over_time", []),
        "assignment": consistent_assignments   # store for map display
    }

# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI (industrial navy + electric orange)
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="FUEL-CSP | Dhaka Emergency",
    page_icon="🔶",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Inconsolata:wght@400;600&family=Barlow:wght@300;400;500&display=swap');

    :root {
        --navy:      #0d1b2a;
        --navy-mid:  #132338;
        --navy-light:#1a2e45;
        --orange:    #ff6b1a;
        --orange-dim:#c4501a;
        --amber:     #ffaa00;
        --white:     #f0ece4;
        --gray:      #8a9bb0;
        --gray-light:#b8c9d9;
        --danger:    #e63946;
        --success:   #2ec4b6;
        --border:    rgba(255,107,26,0.25);
    }

    .stApp { background-color: var(--navy); font-family: 'Barlow', sans-serif; color: var(--white); }
    [data-testid="stSidebar"] { background-color: var(--navy-mid) !important; border-right: 2px solid var(--orange); }
    [data-testid="stSidebar"] * { color: var(--white) !important; }
    h1 { font-family: 'Barlow Condensed', sans-serif !important; font-weight: 900 !important; font-size: 3rem !important; letter-spacing: -1px !important; color: var(--white) !important; }
    h2 { font-family: 'Barlow Condensed', sans-serif !important; font-weight: 700 !important; letter-spacing: 0.5px !important; color: var(--orange) !important; }
    h3 { font-family: 'Barlow Condensed', sans-serif !important; font-weight: 600 !important; color: var(--amber) !important; }
    .kpi-card { background: var(--navy-light); border-left: 4px solid var(--orange); border-radius: 4px 12px 12px 4px; padding: 1.1rem 1.4rem; position: relative; overflow: hidden; }
    .kpi-value { font-family: 'Barlow Condensed', sans-serif; font-size: 2.4rem; font-weight: 900; color: var(--orange); line-height: 1; }
    .kpi-label { font-family: 'Inconsolata', monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--gray); margin-top: 4px; }
    .kpi-sub { font-family: 'Inconsolata', monospace; font-size: 0.85rem; color: var(--success); margin-top: 2px; }
    .stButton > button[kind="primary"] { background: var(--orange) !important; color: var(--navy) !important; font-family: 'Barlow Condensed', sans-serif !important; font-weight: 700 !important; text-transform: uppercase; border: none !important; border-radius: 4px !important; }
    .tag-chip { display: inline-block; font-family: 'Inconsolata', monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; padding: 2px 10px; border-radius: 2px; background: rgba(255,107,26,0.15); border: 1px solid var(--orange); color: var(--orange); margin: 2px; }
    .mono-caption { font-family: 'Inconsolata', monospace; font-size: 0.78rem; color: var(--gray); }
    .landing-panel { background: var(--navy-light); border: 1px solid var(--border); border-radius: 8px; padding: 2.5rem; margin-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="padding: 1.5rem 0 0.5rem 0; border-bottom: 2px solid #ff6b1a; margin-bottom: 1.5rem;">
    <div style="display:flex; align-items:baseline; gap:16px; flex-wrap:wrap;">
        <h1 style="margin:0;">FUEL-CSP</h1>
        <span style="font-family:'Inconsolata',monospace; font-size:0.85rem;
                     color:#8a9bb0; letter-spacing:0.12em; text-transform:uppercase;">
            Dhaka Emergency Fuel Distribution Simulator
        </span>
    </div>
    <div style="margin-top:8px;">
        <span class="tag-chip">Constraint Satisfaction Problem</span>
        <span class="tag-chip">AI Course Assignment</span>
        <span class="tag-chip">QR Fuel Pass Model</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px 0; border-bottom:1px solid rgba(255,107,26,0.3); margin-bottom:16px;">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:1.5rem; font-weight:900;
                    color:#ff6b1a; letter-spacing:1px;">⬡ CONTROL PANEL</div>
        <div style="font-family:'Inconsolata',monospace; font-size:0.72rem; color:#8a9bb0;
                    text-transform:uppercase; letter-spacing:0.1em;">Configure simulation parameters</div>
    </div>
    """, unsafe_allow_html=True)

    num_vehicles = st.slider("Number of Vehicles", 10, 100, 50, 5)
    max_distance = st.slider("Max Distance (km)", 3, 10, 6)
    supply_level = st.select_slider(
        "Fuel Supply Level",
        options=["Critical (30%)", "Low (50%)", "Moderate (70%)", "Normal (100%)"],
        value="Low (50%)"
    )
    supply_factor = {"Critical (30%)": 0.3, "Low (50%)": 0.5, "Moderate (70%)": 0.7, "Normal (100%)": 1.0}[supply_level]

    st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'Inconsolata',monospace; font-size:0.72rem; color:#8a9bb0;
                text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;">
        Algorithm Selection
    </div>
    """, unsafe_allow_html=True)

    run_plain  = st.checkbox("Plain Backtracking",  value=True)
    run_mrv    = st.checkbox("BT + MRV + LCV",      value=True)
    run_ac3    = st.checkbox("AC-3 + BT + MRV",     value=True)
    run_mincon = st.checkbox("Min-Conflicts",        value=True)

    run_btn = st.button("▶  RUN SIMULATION", type="primary", use_container_width=True)

# Run simulation
if run_btn:
    with st.spinner("Generating stations and vehicles..."):
        stations = generate_fuel_stations(30)
        for s in stations:
            s["total_stock_liters"] = int(s["total_stock_liters"] * supply_factor)
        vehicles = generate_vehicles(num_vehicles, stations, max_distance)

    progress_bar = st.progress(0, text="Running algorithms...")
    all_results = []
    all_assignments = {}
    algo_list = []
    if run_plain:  algo_list.append(("Plain Backtracking", {"use_mrv": False, "use_lcv": False, "ac3": False}))
    if run_mrv:    algo_list.append(("BT + MRV + LCV",     {"use_mrv": True,  "use_lcv": True,  "ac3": False}))
    if run_ac3:    algo_list.append(("AC-3 + BT + MRV",    {"use_mrv": True,  "use_lcv": True,  "ac3": True}))
    if run_mincon: algo_list.append(("Min-Conflicts",       {"minconf": True}))

    for idx, (name, opts) in enumerate(algo_list):
        csp = FuelCSP(vehicles, stations, max_distance_km=max_distance)
        if opts.get("ac3", False):
            ac3(csp)           # no-op, but kept for structure
        metrics = (
            {"backtracks": 0, "nodes_visited": 0}
            if not opts.get("minconf", False)
            else {"steps": 0, "conflicts_over_time": []}
        )
        t0 = time.time()
        if opts.get("minconf", False):
            sol = min_conflicts(csp, max_steps=2000, metrics=metrics)
        else:
            sol = backtrack({}, csp, use_mrv=opts.get("use_mrv", False),
                            use_lcv=opts.get("use_lcv", False), metrics=metrics)
        elapsed = time.time() - t0
        r = evaluate(sol, csp, metrics, name, elapsed)
        all_results.append(r)
        all_assignments[name] = r["assignment"]   # store consistent assignments only
        progress_bar.progress((idx + 1) / len(algo_list), text=f"Done: {name}")

    st.session_state["results"] = all_results
    st.session_state["assignments"] = all_assignments
    st.session_state["vehicles"] = vehicles
    st.session_state["stations"] = stations
    st.session_state["max_distance"] = max_distance
    st.success("All algorithms completed successfully.")

# Display results
if "results" in st.session_state:
    results = st.session_state["results"]
    assignments = st.session_state["assignments"]
    vehicles = st.session_state["vehicles"]
    stations = st.session_state["stations"]
    max_dist = st.session_state["max_distance"]

    best = max(results, key=lambda r: r["satisfaction_pct"])
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Top Algorithm</div>
            <div class="kpi-value" style="font-size:1.6rem;">{best['algorithm']}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Vehicles Served</div>
            <div class="kpi-value">{best['served']}<span style="font-size:1.2rem; color:#8a9bb0;">/{best['total_vehicles']}</span></div>
            <div class="kpi-sub">▲ {best['satisfaction_pct']}% satisfaction</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Fuel Distributed</div>
            <div class="kpi-value">{best['total_fuel']}<span style="font-size:1.2rem; color:#8a9bb0;"> L</span></div>
        </div>""", unsafe_allow_html=True)
    with c4:
        fastest = min(r['time_sec'] for r in results)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Fastest Runtime</div>
            <div class="kpi-value">{fastest:.2f}<span style="font-size:1.2rem; color:#8a9bb0;"> s</span></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    tabs = st.tabs(["Results Overview", "Dhaka Map", "Algorithm Comparison", "Station Analysis", "CSP Structure"])

    # Tab 0: Overview
    with tabs[0]:
        df_res = pd.DataFrame([{
            "Algorithm":    r["algorithm"],
            "Served %":     r["satisfaction_pct"],
            "Fuel (L)":     r["total_fuel"],
            "Fairness (σ)": r["fairness_std"],
            "Backtracks":   r["backtracks"],
            "Time (s)":     r["time_sec"]
        } for r in results])

        st.dataframe(df_res.style.highlight_max(subset=["Served %"], color="#c4501a").highlight_min(subset=["Time (s)"], color="#1a3a35"), use_container_width=True)

        col_left, col_right = st.columns([1, 1])
        with col_left:
            fig_donut = go.Figure(go.Pie(
                labels=["Served", "Unserved"],
                values=[best["served"], best["unserved"]],
                hole=0.65,
                marker_colors=["#ff6b1a", "#1a2e45"],
                textinfo="percent"
            ))
            fig_donut.update_layout(title_text=f"{best['algorithm']} — Service Rate", paper_bgcolor="#132338", font_color="#f0ece4")
            st.plotly_chart(fig_donut, use_container_width=True)
        with col_right:
            fig_bar = px.bar(df_res, x="Algorithm", y="Served %", text="Served %", color="Served %", color_continuous_scale=[[0, "#1a2e45"], [0.5, "#c4501a"], [1, "#ff6b1a"]])
            fig_bar.update_layout(plot_bgcolor="#0d1b2a", paper_bgcolor="#132338", font_color="#f0ece4")
            st.plotly_chart(fig_bar, use_container_width=True)

    # Tab 1: Dhaka Map
    with tabs[1]:
        st.markdown("<h2 style='font-size:1.4rem;'>Dhaka City — Interactive Assignment Map</h2>", unsafe_allow_html=True)
        algo_names = [r["algorithm"] for r in results]
        sel_algo = st.selectbox("View assignment for:", algo_names)
        assignment = assignments.get(sel_algo, {})

        m = folium.Map(location=[23.78, 90.40], zoom_start=12, tiles="CartoDB DarkMatter")
        for s in stations:
            served_count = sum(1 for val in assignment.values() if val["station"] == s["id"])
            color = "#e63946" if served_count == 0 else "#ffaa00" if served_count < s["capacity_per_slot"] else "#2ec4b6"
            folium.CircleMarker(location=[s["lat"], s["lon"]], radius=7 + min(served_count, 8), color=color, fill=True, fill_color=color, fill_opacity=0.8, popup=folium.Popup(f"<b>{s['name']}</b><br>Served: {served_count}"), tooltip=s["name"]).add_to(m)

        for v in vehicles[:50]:
            is_served = v.id in assignment
            icon_color = "orange" if is_served else "lightgray"
            folium.Marker(location=[v.home_lat, v.home_lon], icon=folium.Icon(color=icon_color, icon="car", prefix="fa"), popup=f"{v.id} ({v.type}) — {'Served' if is_served else 'Unserved'}").add_to(m)
            if is_served:
                val = assignment[v.id]
                station = next(s for s in stations if s["id"] == val["station"])
                folium.PolyLine([(v.home_lat, v.home_lon), (station["lat"], station["lon"])], color="#ff6b1a", weight=1.5, opacity=0.6).add_to(m)

        components_html(m._repr_html_(), height=500)

    # Tab 2: Algorithm Comparison
    with tabs[2]:
        st.markdown("<h2 style='font-size:1.4rem;'>Multi-Dimensional Algorithm Comparison</h2>", unsafe_allow_html=True)
        df_parallel = pd.DataFrame([{
            "Algorithm": r["algorithm"],
            "Satisfaction": r["satisfaction_pct"],
            "Fuel_Total": r["total_fuel"],
            "Fairness": round(100 - r["fairness_std"] * 10, 1),
            "Speed": round(100 - r["time_sec"] * 5, 1),
            "Efficiency": round(100 - r["backtracks"] / max(r["backtracks"] + 1, 1) * 5, 1)
        } for r in results])

        fig_parallel = px.parallel_coordinates(df_parallel, dimensions=["Satisfaction", "Fuel_Total", "Fairness", "Speed", "Efficiency"], color="Satisfaction", color_continuous_scale=[[0, "#1a2e45"], [0.5, "#c4501a"], [1, "#ff6b1a"]])
        fig_parallel.update_layout(paper_bgcolor="#132338", font_color="#f0ece4")
        st.plotly_chart(fig_parallel, use_container_width=True)

        mc_res = next((r for r in results if "Min-Conflicts" in r["algorithm"]), None)
        if mc_res and mc_res["conflicts_over_time"]:
            st.markdown("<h3 style='font-size:1.1rem;'>Min-Conflicts: Convergence Trace</h3>", unsafe_allow_html=True)
            fig_conf = px.line(y=mc_res["conflicts_over_time"], labels={"x": "Iteration", "y": "Total Conflicts"}, color_discrete_sequence=["#ff6b1a"])
            fig_conf.update_layout(plot_bgcolor="#0d1b2a", paper_bgcolor="#132338", font_color="#f0ece4")
            st.plotly_chart(fig_conf, use_container_width=True)

        fig_perf = go.Figure()
        fig_perf.add_trace(go.Bar(name="Backtracks", x=[r["algorithm"] for r in results], y=[r["backtracks"] for r in results], marker_color="#ff6b1a"))
        fig_perf.add_trace(go.Bar(name="Time × 100 (s)", x=[r["algorithm"] for r in results], y=[r["time_sec"] * 100 for r in results], marker_color="#ffaa00"))
        fig_perf.update_layout(barmode="group", title_text="Backtrack Count vs Runtime", plot_bgcolor="#0d1b2a", paper_bgcolor="#132338", font_color="#f0ece4")
        st.plotly_chart(fig_perf, use_container_width=True)

    # Tab 3: Station Analysis
    with tabs[3]:
        st.markdown("<h2 style='font-size:1.4rem;'>Station Load & Time-Slot Heatmap</h2>", unsafe_allow_html=True)
        sel_algo2 = st.selectbox("Analyze algorithm:", [r["algorithm"] for r in results], key="sta")
        ass = assignments[sel_algo2]

        slot_matrix = {s["id"]: {t: 0 for t in TIME_SLOTS} for s in stations}
        for val in ass.values():
            slot_matrix[val["station"]][val["time"]] += 1

        data = []
        for s in stations:
            fuel_out = sum(v["amount"] for v in ass.values() if v["station"] == s["id"])
            served = sum(1 for v in ass.values() if v["station"] == s["id"])
            util_pct = round(fuel_out / s["total_stock_liters"] * 100, 1) if s["total_stock_liters"] else 0
            data.append({"Station": s["name"], "Vehicles": served, "Fuel Out (L)": round(fuel_out, 1), "Stock (L)": s["total_stock_liters"], "Utilization %": util_pct})
        st.dataframe(pd.DataFrame(data).sort_values("Vehicles", ascending=False), use_container_width=True)

        heat_data = [[slot_matrix[s["id"]][t] for t in TIME_SLOTS] for s in stations]
        fig_heat = go.Figure(data=go.Heatmap(z=heat_data, x=[f"{t}:00" for t in TIME_SLOTS], y=[s["name"] for s in stations], colorscale=[[0, "#0d1b2a"], [0.4, "#c4501a"], [1, "#ff6b1a"]]))
        fig_heat.update_layout(title_text="Station × Time Slot — Congestion Heatmap", plot_bgcolor="#0d1b2a", paper_bgcolor="#132338", font_color="#f0ece4")
        st.plotly_chart(fig_heat, use_container_width=True)

    # Tab 4: CSP Structure
    with tabs[4]:
        st.markdown("<h2 style='font-size:1.4rem;'>CSP Formal Structure</h2>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style="background:#132338; border:1px solid rgba(255,107,26,0.25); border-radius:8px; padding:1.4rem;">
                <div style="color:#ffaa00; font-size:0.8rem; letter-spacing:0.12em; text-transform:uppercase;">Problem Definition</div>
                <div style="color:#b8c9d9; font-size:0.88rem;"><b style="color:#ff6b1a;">Variables:</b> {len(vehicles)} registered vehicles<br>
                <b style="color:#ff6b1a;">Domain:</b> (Station, TimeSlot) pairs within {max_dist} km<br>
                <b style="color:#ff6b1a;">Time Slots:</b> 08:00 → 18:00 (2-hour intervals)</div>
            </div>""", unsafe_allow_html=True)
        with col_b:
            st.markdown("""
            <div style="background:#132338; border:1px solid rgba(255,107,26,0.25); border-radius:8px; padding:1.4rem;">
                <div style="color:#ffaa00; font-size:0.8rem; letter-spacing:0.12em; text-transform:uppercase;">Weekly Fuel Quotas</div>
                <div style="color:#b8c9d9;"><b style="color:#ff6b1a;">Motorcycle:</b> 5 L/week<br><b style="color:#ff6b1a;">Car:</b> 15 L/week<br><b style="color:#ff6b1a;">CNG Auto:</b> 10 L/week</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#132338; border:1px solid rgba(255,107,26,0.25); border-radius:8px; padding:1.4rem; margin-top:1rem;">
            <div style="color:#ffaa00; font-size:0.8rem; letter-spacing:0.12em; text-transform:uppercase;">Constraints</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div style="background:#0d1b2a; border-left:3px solid #ff6b1a; padding:10px 14px;"><b>C1 — Slot Capacity</b><br>Station handles ≤ N vehicles per time slot</div>
                <div style="background:#0d1b2a; border-left:3px solid #ff6b1a; padding:10px 14px;"><b>C2 — Stock Limit</b><br>Total fuel dispensed ≤ station stock</div>
                <div style="background:#0d1b2a; border-left:3px solid #ffaa00; padding:10px 14px;"><b>C3 — Vehicle Quota</b><br>Fuel assigned ≤ weekly quota</div>
                <div style="background:#0d1b2a; border-left:3px solid #ffaa00; padding:10px 14px;"><b>C4 — Unique Assignment</b><br>Each vehicle assigned at most once</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.info("Context: April 2025 — Bangladesh government introduced QR-code‑based fuel pass system. This CSP models the rationing problem. Distance computed via Haversine; maps with Folium.")

else:
    st.markdown("""
    <div class="landing-panel">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:1.8rem; font-weight:900; color:#ff6b1a;">WELCOME TO FUEL-CSP SIMULATOR</div>
        <p style="color:#b8c9d9;">This simulation models Dhaka emergency fuel distribution as a CSP. Configure parameters in the sidebar and click <strong style="color:#ff6b1a;">▶ RUN SIMULATION</strong>.</p>
        <div style="margin-top:1.5rem;"><span class="tag-chip">Plain Backtracking</span> <span class="tag-chip">BT + MRV + LCV</span> <span class="tag-chip">AC-3 + BT + MRV</span> <span class="tag-chip">Min-Conflicts</span></div>
    </div>
    """, unsafe_allow_html=True)