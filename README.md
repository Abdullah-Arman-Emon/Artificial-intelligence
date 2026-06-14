# Artificial Intelligence Assignments

This repository contains multiple AI assignments for the course, including both Assignment 1 and Assignment 2.

---

## Assignment 1 — Safety-Aware Urban Route Planner

This assignment includes `assignment_01_final_code.py`, a Pygame-based interactive route planner that compares graph search algorithms while accounting for safety, gender, group travel, and time-of-day risk preferences.

### Overview

`assignment_01_final_code.py` simulates an urban map with 22 nodes and weighted edges. The application supports:

- Interactive selection of start and end nodes on a city map
- Multiple search algorithms:
  - BFS
  - DFS
  - Uniform Cost Search (UCS)
  - Depth-Limited Search (DLS)
  - Iterative Deepening Search (IDS)
  - A*
  - Weighted A*
  - Greedy Best-First Search
- Safety-aware risk scoring based on:
  - traveler gender (`female` / `male`)
  - travel group (`solo` / `group`)
  - time of day (`day` / `night`)
- Route priority modes:
  - `safe` (risk-averse)
  - `risky` (distance/time-focused)
- Visual path and exploration display
- Algorithm comparison mode

### Requirements

- Python 3.8+
- `pygame`

### Installation

```powershell
python -m pip install pygame
```

### Run

```powershell
python assignment_01_final_code.py
```

### Notes

- The risk model multiplies base edge risk by gender, group, and time factors.
- Safe mode places heavier weight on risk, while risky mode emphasizes shorter and faster routes.
- The visualization includes path highlighting, explored nodes, and edge risk coloring.

---

## Assignment 2 — Fuel Crisis CSP

This assignment includes `assignment_02.py`, a Streamlit-based fuel crisis CSP simulation, and the report file `Assignment_2_Fuel_Crisis_CSP_report.docx`.

### Files included

- `assignment_02.py`
- `README.md`
- `Assignment_2_Fuel_Crisis_CSP_report.docx`

### Description

The project models a Dhaka fuel crisis with a QR-based fuel pass system. It includes a simulation of vehicles, fuel stations, capacity constraints, and scheduling.

### Run instructions

1. Activate the Python virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Install required packages if needed:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install streamlit plotly pandas folium streamlit-folium
   ```
3. Run the Streamlit app:
   ```powershell
   python -m streamlit run u.py
   ```

### Notes

- If `streamlit` is not found, use `python -m streamlit run u.py`.
- The app may require OSM data downloads on first run.

