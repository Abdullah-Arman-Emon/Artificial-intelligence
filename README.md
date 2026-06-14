# Assignment 2 — Fuel Crisis CSP

This repository contains the second AI assignment for the Fuel Crisis CSP simulation.

## Files included

- `assignment_02.py`
- `README.md`
- `Assignment_2_Fuel_Crisis_CSP_report.docx`

## Description

The project models a Dhaka fuel crisis with a QR-based fuel pass system.
It includes a simulation of vehicles, fuel stations, capacity constraints, and scheduling.

## Run instructions

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

## Notes

- This repository is intended for the `main` branch on GitHub.
- If Streamlit is not found, use `python -m streamlit run u.py`.
