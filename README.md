# Safety-Aware Urban Route Planner

This repository contains `assignment_01_final_code.py`, a Pygame-based interactive route planner that compares graph search algorithms while accounting for safety, gender, group travel, and time-of-day risk preferences.

## Overview

`assignment_01_final_code.py` simulates an urban map with 22 nodes and weighted edges.
The application supports:

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

## Requirements

- Python 3.8+
- `pygame` library

## Installation

Install Pygame with pip:

```bash
pip install pygame
```

## Run the application

From the repository folder, run:

```bash
python assignment_01_final_code.py
```

## Controls

- Click a node on the map to select the start point
- Click a second node to select the end point
- Use the right-hand panel to choose:
  - traveler gender
  - solo or group travel
  - day or night conditions
  - safe or risky route priority
  - search algorithm
- Click `RUN SEARCH` to compute and display the path
- Toggle `Compare All Algorithms` to view algorithm comparison results
- Click `Reset` to clear the current selection

## Notes

- The risk model multiplies base edge risk by gender, group, and time factors.
- The safe mode places heavier weight on risk, while the risky mode emphasizes shorter and faster routes.
- The visualization includes path highlighting, explored nodes, and edge risk coloring.

## File

- `assignment_01_final_code.py` — main application script

## License

This repository is intended for academic assignment use and demonstration.
