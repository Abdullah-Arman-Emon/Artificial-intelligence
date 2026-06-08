"""
AI Lab: Safety-Aware Urban Route Planning
=========================================
A fully interactive map with 22 nodes, multiple search algorithms,
gender/time/group-sensitive risk scoring, and algorithm comparison.
"""

import pygame
import math
import heapq
import random
import sys
import time
from collections import deque

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
W, H = 1400, 860
MAP_W, MAP_H = 820, 620
MAP_X, MAP_Y = 20, 120

FPS = 60

# Colors
BG          = (15, 17, 26)
PANEL_BG    = (22, 26, 38)
PANEL_BORDER= (45, 52, 72)
CARD_BG     = (28, 33, 48)
WHITE       = (240, 245, 255)
GRAY        = (120, 130, 155)
LIGHT_GRAY  = (180, 190, 210)
DARK_GRAY   = (40, 46, 62)

# Node colors
NODE_DEFAULT= (55, 130, 200)
NODE_HOVER  = (80, 175, 255)
NODE_START  = (50, 200, 120)
NODE_END    = (220, 70, 80)
NODE_PATH   = (255, 200, 50)
NODE_EXPLORED=(180, 100, 220)
NODE_TEXT   = (240, 245, 255)

# Edge colors
EDGE_DEFAULT= (50, 60, 85)
EDGE_SAFE   = (40, 90, 140)
EDGE_RISKY  = (120, 45, 45)
EDGE_PATH   = (255, 200, 50)
EDGE_EXPLORED=(100, 60, 150)

# UI colors
ACCENT      = (80, 160, 255)
ACCENT2     = (120, 200, 140)
DANGER      = (220, 80, 80)
WARNING     = (255, 170, 50)
SUCCESS     = (60, 200, 120)
PURPLE      = (160, 100, 220)

# ─── CITY MAP DATA ────────────────────────────────────────────────────────────
# 22 nodes with names, positions on MAP canvas, and type info
NODES = {
    'A': {'pos': (80,  80),  'name': 'City Hall',        'type': 'civic'},
    'B': {'pos': (200, 55),  'name': 'University',       'type': 'education'},
    'C': {'pos': (340, 70),  'name': 'Hospital',         'type': 'medical'},
    'D': {'pos': (480, 50),  'name': 'Airport',          'type': 'transit'},
    'E': {'pos': (620, 80),  'name': 'Tech Park',        'type': 'business'},
    'F': {'pos': (120, 200), 'name': 'Central Market',   'type': 'market'},
    'G': {'pos': (260, 185), 'name': 'Police Station',   'type': 'safety'},
    'H': {'pos': (400, 170), 'name': 'Train Station',    'type': 'transit'},
    'I': {'pos': (540, 190), 'name': 'Shopping Mall',    'type': 'market'},
    'J': {'pos': (680, 170), 'name': 'Sports Complex',   'type': 'recreation'},
    'K': {'pos': (760, 110), 'name': 'Industrial Zone',  'type': 'industrial'},
    'L': {'pos': (80,  320), 'name': 'Old Town',         'type': 'residential'},
    'M': {'pos': (210, 310), 'name': 'Park',             'type': 'recreation'},
    'N': {'pos': (350, 300), 'name': 'Bus Terminal',     'type': 'transit'},
    'O': {'pos': (490, 305), 'name': 'Financial District','type': 'business'},
    'P': {'pos': (640, 295), 'name': 'Hotel Zone',       'type': 'hospitality'},
    'Q': {'pos': (760, 280), 'name': 'Dockyard',         'type': 'industrial'},
    'R': {'pos': (130, 450), 'name': 'Slum Area',        'type': 'residential_risk'},
    'S': {'pos': (280, 460), 'name': 'Suburb North',     'type': 'residential'},
    'T': {'pos': (430, 455), 'name': 'Suburb South',     'type': 'residential'},
    'U': {'pos': (580, 460), 'name': 'Night Market',     'type': 'market'},
    'V': {'pos': (710, 450), 'name': 'Outskirts',        'type': 'residential_risk'},
}

# Edges: (node1, node2, distance_km, base_risk_score)
# base_risk_score: 0.0 (very safe) to 1.0 (very risky)
EDGES_RAW = [
    ('A','B', 2.1, 0.1),   ('A','F', 1.8, 0.15),  ('A','L', 3.2, 0.3),
    ('B','C', 2.5, 0.1),   ('B','G', 2.0, 0.1),   ('B','F', 2.3, 0.15),
    ('C','D', 3.0, 0.1),   ('C','H', 2.2, 0.12),  ('C','G', 1.9, 0.1),
    ('D','E', 2.8, 0.15),  ('D','H', 2.5, 0.1),   ('D','I', 3.1, 0.2),
    ('E','J', 2.0, 0.2),   ('E','K', 1.5, 0.35),  ('E','I', 2.4, 0.15),
    ('F','G', 1.5, 0.12),  ('F','L', 2.8, 0.25),  ('F','M', 2.0, 0.15),
    ('G','H', 2.3, 0.1),   ('G','M', 1.8, 0.12),  ('G','N', 2.5, 0.15),
    ('H','I', 2.1, 0.2),   ('H','N', 1.9, 0.18),  ('H','O', 2.6, 0.2),
    ('I','J', 2.0, 0.2),   ('I','O', 2.2, 0.2),   ('I','P', 2.5, 0.2),
    ('J','K', 1.8, 0.4),   ('J','P', 2.3, 0.25),  ('J','Q', 2.0, 0.35),
    ('K','Q', 2.5, 0.5),
    ('L','M', 2.2, 0.2),   ('L','R', 2.5, 0.55),
    ('M','N', 2.0, 0.18),  ('M','S', 2.8, 0.22),
    ('N','O', 2.1, 0.2),   ('N','S', 2.4, 0.25),  ('N','T', 2.6, 0.22),
    ('O','P', 2.0, 0.2),   ('O','T', 2.2, 0.22),
    ('P','Q', 2.8, 0.3),   ('P','U', 2.4, 0.28),
    ('Q','V', 2.0, 0.5),
    ('R','S', 2.3, 0.45),
    ('S','T', 2.5, 0.25),  ('S','R', 2.3, 0.45),
    ('T','U', 2.2, 0.3),   ('T','S', 2.5, 0.25),
    ('U','V', 2.1, 0.4),   ('U','P', 2.4, 0.28),
    ('V','Q', 2.0, 0.5),
]

# ─── RISK MODEL ───────────────────────────────────────────────────────────────
def compute_risk(base_risk, gender, group, time_of_day):
    """
    Compute final risk for an edge based on user profile.
    
    Risk equation:
      Risk = base_risk * gender_multiplier * group_multiplier * time_multiplier
    
    - gender_multiplier: female travelers face higher risk on dark/secluded roads
    - group_multiplier: group travel reduces risk
    - time_multiplier: night increases risk significantly
    """
    # Gender vulnerability multiplier
    # Females face higher risk on high-base-risk roads (non-linear scaling)
    if gender == 'female':
        gender_mult = 1.0 + (base_risk * 1.4)   # up to 2.4x on very risky roads
    else:
        gender_mult = 1.0 + (base_risk * 0.6)   # males still affected, less so

    # Group multiplier — solo travel is riskier
    group_mult = 0.65 if group == 'group' else 1.0

    # Time multiplier — night is significantly more dangerous
    time_mult = 1.7 if time_of_day == 'night' else 1.0

    risk = base_risk * gender_mult * group_mult * time_mult
    return min(risk, 3.0)  # cap

def edge_cost(dist, risk, alpha=0.5, beta=0.3, gamma=0.2):
    """
    Cost(A,B) = α*distance + β*time_proxy + γ*risk
    time_proxy ≈ distance (speed assumed uniform for simplicity)
    """
    time_proxy = dist * 4.0  # minutes at ~15 km/h avg urban speed
    return alpha * dist + beta * time_proxy + gamma * risk * 10.0

# ─── GRAPH BUILDER ────────────────────────────────────────────────────────────
def build_graph(gender, group, time_of_day):
    """Return adjacency dict with computed costs."""
    graph = {n: {} for n in NODES}
    edge_risk_map = {}

    for n1, n2, dist, base_risk in EDGES_RAW:
        risk = compute_risk(base_risk, gender, group, time_of_day)
        cost = edge_cost(dist, risk)
        graph[n1][n2] = {'cost': cost, 'dist': dist, 'risk': risk, 'base_risk': base_risk}
        graph[n2][n1] = {'cost': cost, 'dist': dist, 'risk': risk, 'base_risk': base_risk}
        edge_risk_map[(n1,n2)] = risk
        edge_risk_map[(n2,n1)] = risk

    return graph, edge_risk_map

# ─── HEURISTIC ────────────────────────────────────────────────────────────────
def heuristic(node, goal, gender, group, time_of_day, alpha=0.5, gamma=0.2):
    """
    Admissible heuristic:
      h(n) = α * SLD(n, goal) * scale_factor + γ * absolute_min_risk_remaining
    
    SLD is straight-line distance on the canvas (scaled to km).
    Minimum possible risk is computed as the smallest risk of any single edge.
    """
    nx_, ny_ = NODES[node]['pos']
    gx, gy  = NODES[goal]['pos']
    pixel_dist = math.hypot(nx_ - gx, ny_ - gy)
    # scale: MAP is ~820px wide representing roughly 20km conceptually
    km_scale = 20.0 / MAP_W
    sld_km = pixel_dist * km_scale

    # Minimum risk in the entire graph (never overestimates)
    min_base_risk = min(e[3] for e in EDGES_RAW)
    min_risk = compute_risk(min_base_risk, gender, group, time_of_day)

    time_proxy = sld_km * 4.0
    h = alpha * sld_km + 0.3 * time_proxy + gamma * min_risk * 10.0
    return h

# ─── SEARCH ALGORITHMS ───────────────────────────────────────────────────────
def reconstruct(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]

def bfs(graph, start, goal):
    """Breadth-First Search — unweighted, finds fewest hops."""
    frontier = deque([(start, [start])])
    visited = {start}
    explored_order = []
    nodes_explored = 0

    while frontier:
        node, path = frontier.popleft()
        explored_order.append(node)
        nodes_explored += 1
        if node == goal:
            return path, nodes_explored, explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                frontier.append((neighbor, path + [neighbor]))
    return None, nodes_explored, explored_order, 0, 0

def dfs(graph, start, goal):
    """Depth-First Search — explores deeply, not optimal."""
    stack = [(start, [start])]
    visited = set()
    explored_order = []
    nodes_explored = 0

    while stack:
        node, path = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        explored_order.append(node)
        nodes_explored += 1
        if node == goal:
            return path, nodes_explored, explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
        for neighbor in reversed(list(graph[node])):
            if neighbor not in visited:
                stack.append((neighbor, path + [neighbor]))
    return None, nodes_explored, explored_order, 0, 0

def ucs(graph, start, goal):
    """Uniform Cost Search — optimal by total cost (Dijkstra)."""
    frontier = [(0, start, [start])]
    cost_so_far = {start: 0}
    explored_order = []
    nodes_explored = 0

    while frontier:
        cost, node, path = heapq.heappop(frontier)
        if node in [n for n in explored_order]:
            continue
        explored_order.append(node)
        nodes_explored += 1
        if node == goal:
            return path, nodes_explored, explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
        for neighbor, data in graph[node].items():
            new_cost = cost + data['cost']
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                heapq.heappush(frontier, (new_cost, neighbor, path + [neighbor]))
    return None, nodes_explored, explored_order, 0, 0

def dls(graph, start, goal, limit=8):
    """Depth-Limited Search — DFS with a depth cutoff."""
    explored_order = []
    nodes_explored = [0]

    def dls_recursive(node, path, depth):
        explored_order.append(node)
        nodes_explored[0] += 1
        if node == goal:
            return path
        if depth == 0:
            return None
        for neighbor in graph[node]:
            if neighbor not in path:
                result = dls_recursive(neighbor, path + [neighbor], depth - 1)
                if result:
                    return result
        return None

    path = dls_recursive(start, [start], limit)
    if path:
        return path, nodes_explored[0], explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
    return None, nodes_explored[0], explored_order, 0, 0

def ids(graph, start, goal, max_depth=15):
    """Iterative Deepening Search — optimal like BFS, memory like DFS."""
    all_explored = []
    total_nodes = 0

    for depth in range(max_depth + 1):
        explored_this = []
        nodes_this = [0]

        def dls_r(node, path, d):
            explored_this.append(node)
            nodes_this[0] += 1
            if node == goal:
                return path
            if d == 0:
                return None
            for neighbor in graph[node]:
                if neighbor not in path:
                    result = dls_r(neighbor, path + [neighbor], d - 1)
                    if result:
                        return result
            return None

        path = dls_r(start, [start], depth)
        total_nodes += nodes_this[0]
        all_explored.extend(explored_this)

        if path:
            return path, total_nodes, all_explored, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))

    return None, total_nodes, all_explored, 0, 0

def astar(graph, start, goal, gender, group, time_of_day):
    """A* Search — optimal + efficient using heuristic."""
    frontier = [(heuristic(start, goal, gender, group, time_of_day), 0, start, [start])]
    cost_so_far = {start: 0}
    explored_order = []
    nodes_explored = 0

    while frontier:
        f, g, node, path = heapq.heappop(frontier)
        if node in explored_order:
            continue
        explored_order.append(node)
        nodes_explored += 1
        if node == goal:
            return path, nodes_explored, explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
        for neighbor, data in graph[node].items():
            new_g = g + data['cost']
            if neighbor not in cost_so_far or new_g < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_g
                h = heuristic(neighbor, goal, gender, group, time_of_day)
                heapq.heappush(frontier, (new_g + h, new_g, neighbor, path + [neighbor]))
    return None, nodes_explored, explored_order, 0, 0

def greedy(graph, start, goal, gender, group, time_of_day):
    """Greedy Best-First — fast but not always optimal."""
    frontier = [(heuristic(start, goal, gender, group, time_of_day), start, [start])]
    visited = set()
    explored_order = []
    nodes_explored = 0

    while frontier:
        h, node, path = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.add(node)
        explored_order.append(node)
        nodes_explored += 1
        if node == goal:
            return path, nodes_explored, explored_order, sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1)), sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
        for neighbor in graph[node]:
            if neighbor not in visited:
                h_n = heuristic(neighbor, goal, gender, group, time_of_day)
                heapq.heappush(frontier, (h_n, neighbor, path + [neighbor]))
    return None, nodes_explored, explored_order, 0, 0

# ─── RUN ALL ALGORITHMS ──────────────────────────────────────────────────────
def run_all_algorithms(start, goal, gender, group, time_of_day):
    graph, edge_risk_map = build_graph(gender, group, time_of_day)
    results = {}

    algos = {
        'BFS':     lambda: bfs(graph, start, goal),
        'DFS':     lambda: dfs(graph, start, goal),
        'UCS':     lambda: ucs(graph, start, goal),
        'DLS':     lambda: dls(graph, start, goal),
        'IDS':     lambda: ids(graph, start, goal),
        'A*':      lambda: astar(graph, start, goal, gender, group, time_of_day),
        'Greedy':  lambda: greedy(graph, start, goal, gender, group, time_of_day),
    }

    for name, fn in algos.items():
        t0 = time.perf_counter()
        path, nodes_exp, exp_order, total_dist, total_risk = fn()
        elapsed = (time.perf_counter() - t0) * 1000  # ms

        total_cost = 0
        if path:
            for i in range(len(path)-1):
                total_cost += graph[path[i]][path[i+1]]['cost']

        results[name] = {
            'path': path,
            'nodes_explored': nodes_exp,
            'explored_order': exp_order,
            'total_dist': round(total_dist, 2),
            'total_risk': round(total_risk, 3),
            'total_cost': round(total_cost, 3),
            'path_len': len(path) if path else 0,
            'time_ms': round(elapsed, 4),
            'found': path is not None,
        }

    return results, graph, edge_risk_map

# ─── PYGAME APP ──────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("AI Lab — Safety-Aware Urban Route Planner")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_lg  = pygame.font.SysFont('Segoe UI', 22, bold=True)
        self.font_md  = pygame.font.SysFont('Segoe UI', 17)
        self.font_sm  = pygame.font.SysFont('Segoe UI', 13)
        self.font_xs  = pygame.font.SysFont('Segoe UI', 11)
        self.font_node= pygame.font.SysFont('Segoe UI', 12, bold=True)
        self.font_title=pygame.font.SysFont('Segoe UI', 28, bold=True)

        # State
        self.start_node   = None
        self.end_node     = None
        self.hover_node   = None
        self.gender       = 'female'   # female / male
        self.group        = 'solo'     # solo / group
        self.time_of_day  = 'night'    # day / night
        self.algorithm    = 'A*'
        self.results      = None
        self.graph        = None
        self.edge_risk_map= None
        self.selected_algo= 'A*'
        self.show_comparison = False
        self.animating    = False
        self.anim_step    = 0
        self.anim_timer   = 0
        self.anim_explored= []
        self.status_msg   = "Click two nodes on the map to set Start and End points"
        self.status_color = LIGHT_GRAY

        # Scroll for result panel
        self.result_scroll = 0

        # Button layout
        self.buttons = {}
        self._build_buttons()

    def _build_buttons(self):
        # Right panel starts at x=860
        px = 860
        # Gender buttons
        self.buttons['gender_female'] = pygame.Rect(px+10, 140, 105, 34)
        self.buttons['gender_male']   = pygame.Rect(px+125, 140, 105, 34)
        # Group
        self.buttons['group_solo']    = pygame.Rect(px+10, 215, 105, 34)
        self.buttons['group_group']   = pygame.Rect(px+125, 215, 105, 34)
        # Time
        self.buttons['time_day']      = pygame.Rect(px+10, 290, 105, 34)
        self.buttons['time_night']    = pygame.Rect(px+125, 290, 105, 34)
        # Algorithms
        algos = ['BFS','DFS','UCS','DLS','IDS','A*','Greedy']
        for i, alg in enumerate(algos):
            row, col = divmod(i, 2)
            bx = px + 10 + col * 120
            by = 375 + row * 42
            self.buttons[f'algo_{alg}'] = pygame.Rect(bx, by, 112, 34)
        # Run
        self.buttons['run']           = pygame.Rect(px+10, 550, 230, 44)
        # Compare
        self.buttons['compare']       = pygame.Rect(px+10, 604, 230, 36)
        # Reset
        self.buttons['reset']         = pygame.Rect(px+10, 648, 230, 36)

    def map_pos(self, node):
        """Convert node position to screen coordinates."""
        x, y = NODES[node]['pos']
        return (MAP_X + x, MAP_Y + y)

    def node_at(self, mx, my):
        """Find which node is at mouse position."""
        for name in NODES:
            nx, ny = self.map_pos(name)
            if math.hypot(mx - nx, my - ny) < 18:
                return name
        return None

    def risk_color(self, risk, base=False):
        """Map risk value to color."""
        r_val = risk if base else min(risk / 2.0, 1.0)
        r = int(50 + r_val * 180)
        g = int(180 - r_val * 150)
        b = int(60)
        return (r, g, b)

    def draw_map_background(self):
        """Draw the map area."""
        pygame.draw.rect(self.screen, (18, 22, 35), (MAP_X, MAP_Y, MAP_W, MAP_H), border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, (MAP_X, MAP_Y, MAP_W, MAP_H), 1, border_radius=12)

        # Grid lines
        for x in range(MAP_X, MAP_X+MAP_W, 60):
            pygame.draw.line(self.screen, (25, 30, 45), (x, MAP_Y), (x, MAP_Y+MAP_H))
        for y in range(MAP_Y, MAP_Y+MAP_H, 60):
            pygame.draw.line(self.screen, (25, 30, 45), (MAP_X, y), (MAP_X+MAP_W, y))

    def draw_edges(self):
        """Draw all edges with risk-based coloring."""
        results = self.results
        sel = self.selected_algo
        path_set = set()
        explored_set = set()

        if results and sel in results and results[sel]['found']:
            path = results[sel]['path']
            path_set = set(zip(path, path[1:]))
            path_set |= set(zip(path[1:], path))  # bidirectional

        if results and sel in results:
            exp = results[sel]['explored_order']
            # Only show explored up to animation step
            if self.animating:
                exp = exp[:self.anim_step]
            explored_set = set(exp)

        for n1, n2, dist, base_risk in EDGES_RAW:
            p1 = self.map_pos(n1)
            p2 = self.map_pos(n2)

            in_path = (n1,n2) in path_set
            both_explored = n1 in explored_set and n2 in explored_set

            if in_path:
                # Draw glow
                for thickness in [7, 5, 3]:
                    alpha_col = (255, 200, 50, 60) if thickness == 7 else EDGE_PATH
                    pygame.draw.line(self.screen, alpha_col, p1, p2, thickness)
            elif both_explored and not in_path:
                pygame.draw.line(self.screen, (80, 50, 120), p1, p2, 2)
            else:
                color = self.risk_color(base_risk, base=True)
                pygame.draw.line(self.screen, color, p1, p2, 2)

            # Distance label on edges (only for path)
            if in_path:
                mx = (p1[0]+p2[0])//2
                my = (p1[1]+p2[1])//2
                txt = self.font_xs.render(f"{dist}km", True, (200,180,80))
                self.screen.blit(txt, (mx-12, my-7))

    def draw_nodes(self):
        """Draw all nodes."""
        results = self.results
        sel = self.selected_algo
        path_set = set()
        explored_set = set()

        if results and sel in results and results[sel]['found']:
            path_set = set(results[sel]['path'])

        if results and sel in results:
            exp = results[sel]['explored_order']
            if self.animating:
                exp = exp[:self.anim_step]
            explored_set = set(exp)

        for name, data in NODES.items():
            pos = self.map_pos(name)
            nx, ny = pos

            # Determine color
            if name == self.start_node:
                color = NODE_START
                ring_color = (100, 255, 150)
                radius = 16
            elif name == self.end_node:
                color = NODE_END
                ring_color = (255, 120, 100)
                radius = 16
            elif name in path_set:
                color = NODE_PATH
                ring_color = (255, 220, 80)
                radius = 15
            elif name in explored_set:
                color = NODE_EXPLORED
                ring_color = (180, 100, 220)
                radius = 13
            elif name == self.hover_node:
                color = NODE_HOVER
                ring_color = ACCENT
                radius = 14
            else:
                color = NODE_DEFAULT
                ring_color = None
                radius = 12

            # Draw outer ring
            if ring_color:
                pygame.draw.circle(self.screen, ring_color, (nx, ny), radius+3, 2)

            # Glow for path nodes
            if name in path_set or name == self.start_node or name == self.end_node:
                glow = pygame.Surface((radius*4, radius*4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color, 40), (radius*2, radius*2), radius*2)
                self.screen.blit(glow, (nx - radius*2, ny - radius*2))

            # Main circle
            pygame.draw.circle(self.screen, color, (nx, ny), radius)
            pygame.draw.circle(self.screen, (200, 220, 255), (nx, ny), radius, 1)

            # Node letter label (inside circle)
            label = self.font_node.render(name, True, NODE_TEXT)
            lw, lh = label.get_size()
            self.screen.blit(label, (nx - lw//2, ny - lh//2))

            # Node full name label (below circle, always visible)
            name_lbl = self.font_xs.render(data['name'], True, (160, 175, 200))
            nlw, nlh = name_lbl.get_size()
            lbl_x = min(max(nx - nlw//2, MAP_X + 2), MAP_X + MAP_W - nlw - 2)
            lbl_y = ny + radius + 3
            # Only draw if it fits inside map vertically
            if lbl_y + nlh < MAP_Y + MAP_H - 2:
                # Subtle dark backing for readability
                pygame.draw.rect(self.screen, (12, 16, 28, 180), (lbl_x - 2, lbl_y - 1, nlw + 4, nlh + 1), border_radius=2)
                self.screen.blit(name_lbl, (lbl_x, lbl_y))

            # Node name tooltip on hover (brighter, larger)
            if name == self.hover_node:
                tip = self.font_sm.render(data['name'], True, WHITE)
                tw, th = tip.get_size()
                tip_x = min(nx - tw//2, MAP_X + MAP_W - tw - 5)
                tip_x = max(tip_x, MAP_X + 5)
                tip_y = ny - radius - 20
                pygame.draw.rect(self.screen, (30, 36, 55), (tip_x-4, tip_y-2, tw+8, th+4), border_radius=4)
                self.screen.blit(tip, (tip_x, tip_y))

    def draw_right_panel(self):
        """Draw the control panel on the right."""
        px = 855
        pygame.draw.rect(self.screen, PANEL_BG, (px, 0, W-px, H))
        pygame.draw.line(self.screen, PANEL_BORDER, (px, 0), (px, H), 1)

        x = px + 10
        y = 15

        # Title
        title = self.font_lg.render("⚙  Route Planner", True, WHITE)
        self.screen.blit(title, (x, y))
        y += 35

        # Selected nodes display
        pygame.draw.rect(self.screen, CARD_BG, (x, y, 240, 52), border_radius=8)
        start_txt = f"Start: {self.start_node} ({NODES[self.start_node]['name']})" if self.start_node else "Start: (click map)"
        end_txt   = f"End:   {self.end_node} ({NODES[self.end_node]['name']})"   if self.end_node   else "End:   (click map)"
        self.screen.blit(self.font_sm.render(start_txt, True, NODE_START if self.start_node else GRAY), (x+8, y+8))
        self.screen.blit(self.font_sm.render(end_txt,   True, NODE_END   if self.end_node   else GRAY), (x+8, y+28))
        y += 62

        # ── GENDER ──
        self.screen.blit(self.font_sm.render("TRAVELER GENDER", True, GRAY), (x, y))
        y += 20
        for key, label, icon in [('female','♀  Female', 'gender_female'), ('male','♂  Male', 'gender_male')]:
            btn = self.buttons[f'gender_{key}']
            active = self.gender == key
            pygame.draw.rect(self.screen, (ACCENT if active else DARK_GRAY), btn, border_radius=8)
            if active: pygame.draw.rect(self.screen, ACCENT, btn, 2, border_radius=8)
            col = WHITE if active else GRAY
            t = self.font_sm.render(label, True, col)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y + 9))
        y += 48

        # ── GROUP ──
        self.screen.blit(self.font_sm.render("JOURNEY TYPE", True, GRAY), (x, y))
        y += 20
        for key, label in [('solo','👤 Solo'), ('group','👥 Group')]:
            btn = self.buttons[f'group_{key}']
            active = self.group == key
            pygame.draw.rect(self.screen, (ACCENT2 if active else DARK_GRAY), btn, border_radius=8)
            if active: pygame.draw.rect(self.screen, ACCENT2, btn, 2, border_radius=8)
            col = WHITE if active else GRAY
            t = self.font_sm.render(label, True, col)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y + 9))
        y += 48

        # ── TIME ──
        self.screen.blit(self.font_sm.render("TIME OF DAY", True, GRAY), (x, y))
        y += 20
        for key, label in [('day','☀ Day'), ('night','🌙 Night')]:
            btn = self.buttons[f'time_{key}']
            active = self.time_of_day == key
            col_active = WARNING if key == 'day' else PURPLE
            pygame.draw.rect(self.screen, (col_active if active else DARK_GRAY), btn, border_radius=8)
            if active: pygame.draw.rect(self.screen, col_active, btn, 2, border_radius=8)
            t = self.font_sm.render(label, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y + 9))
        y += 48

        # ── ALGORITHM ──
        self.screen.blit(self.font_sm.render("SEARCH ALGORITHM", True, GRAY), (x, y))
        y += 20
        algo_colors = {
            'BFS': (60, 140, 200), 'DFS': (180, 80, 80), 'UCS': (60, 180, 120),
            'DLS': (180, 140, 50), 'IDS': (100, 160, 200), 'A*': (160, 80, 220),
            'Greedy': (220, 120, 50),
        }
        algos = ['BFS','DFS','UCS','DLS','IDS','A*','Greedy']
        for alg in algos:
            btn = self.buttons[f'algo_{alg}']
            active = self.algorithm == alg
            ac = algo_colors.get(alg, ACCENT)
            pygame.draw.rect(self.screen, (ac if active else DARK_GRAY), btn, border_radius=7)
            if active: pygame.draw.rect(self.screen, ac, btn, 2, border_radius=7)
            t = self.font_sm.render(alg, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y + 9))

        y = 558

        # ── RUN Button ──
        run_btn = self.buttons['run']
        pygame.draw.rect(self.screen, SUCCESS, run_btn, border_radius=10)
        pygame.draw.rect(self.screen, (100, 255, 150), run_btn, 2, border_radius=10)
        rt = self.font_md.render("▶  RUN SEARCH", True, (10, 20, 15))
        self.screen.blit(rt, (run_btn.x + run_btn.w//2 - rt.get_width()//2, run_btn.y + 12))

        # ── Compare Button ──
        cmp_btn = self.buttons['compare']
        cmp_active = self.show_comparison
        pygame.draw.rect(self.screen, (ACCENT if cmp_active else DARK_GRAY), cmp_btn, border_radius=8)
        ct = self.font_sm.render("📊  Compare All Algorithms", True, WHITE)
        self.screen.blit(ct, (cmp_btn.x + cmp_btn.w//2 - ct.get_width()//2, cmp_btn.y + 9))

        # ── Reset Button ──
        rst_btn = self.buttons['reset']
        pygame.draw.rect(self.screen, DARK_GRAY, rst_btn, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, rst_btn, 1, border_radius=8)
        rt2 = self.font_sm.render("↺  Reset", True, GRAY)
        self.screen.blit(rt2, (rst_btn.x + rst_btn.w//2 - rt2.get_width()//2, rst_btn.y + 9))

        # ── Comparison panel (right side, below Reset) ──
        if self.show_comparison and self.results:
            panel_y = rst_btn.bottom + 10
            panel_h = H - panel_y - 5
            pygame.draw.rect(self.screen, CARD_BG, (x, panel_y, 240, panel_h), border_radius=8)
            pygame.draw.rect(self.screen, PANEL_BORDER, (x, panel_y, 240, panel_h), 1, border_radius=8)
            clip_rect = pygame.Rect(x, panel_y, 240, panel_h)
            self.screen.set_clip(clip_rect)
            self._draw_comparison_panel(x + 4, panel_y + 6 - self.result_scroll, 232)
            self.screen.set_clip(None)
            hint = self.font_xs.render("W/S or mousewheel to scroll", True, GRAY)
            self.screen.blit(hint, (x + 4, H - 16))

    def draw_bottom_panel(self):
        """Draw info/results below the map."""
        by = MAP_Y + MAP_H + 12
        bh = H - by - 5
        pygame.draw.rect(self.screen, PANEL_BG, (MAP_X, by, MAP_W, bh), border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, (MAP_X, by, MAP_W, bh), 1, border_radius=10)

        x = MAP_X + 12
        y = by + 10

        if self.show_comparison and self.results:
            self._draw_comparison(x, y, MAP_W - 24, bh - 15)
        elif self.results:
            self._draw_result_detail(x, y, MAP_W - 24, bh - 15)
        else:
            # Status
            msg = self.font_md.render(self.status_msg, True, self.status_color)
            self.screen.blit(msg, (x, y + 10))

            # Legend
            lx = x
            ly = y + 40
            self.screen.blit(self.font_sm.render("LEGEND:", True, GRAY), (lx, ly))
            ly += 20
            items = [
                (NODE_START, "Start Node"),
                (NODE_END,   "End Node"),
                (NODE_PATH,  "Path Node"),
                (NODE_EXPLORED, "Explored Node"),
                ((60,120,60), "Low Risk Edge"),
                ((180,60,60), "High Risk Edge"),
            ]
            for color, label in items:
                pygame.draw.circle(self.screen, color, (lx+8, ly+7), 7)
                self.screen.blit(self.font_sm.render(label, True, LIGHT_GRAY), (lx+22, ly))
                lx += 160
                if lx > MAP_X + MAP_W - 100:
                    lx = x
                    ly += 22

    def _draw_result_detail(self, x, y, w, h):
        """Draw single algorithm result details."""
        sel = self.selected_algo
        if sel not in self.results:
            return
        r = self.results[sel]

        # Title
        color_map = {'BFS':(60,140,200),'DFS':(180,80,80),'UCS':(60,180,120),
                     'DLS':(180,140,50),'IDS':(100,160,200),'A*':(160,80,220),'Greedy':(220,120,50)}
        ac = color_map.get(sel, ACCENT)
        title = self.font_md.render(f"[ {sel} ]  Result", True, ac)
        self.screen.blit(title, (x, y))

        if not r['found']:
            self.screen.blit(self.font_md.render("No path found!", True, DANGER), (x + 200, y))
            return

        # Path display
        path_str = " → ".join(r['path'])
        path_txt = self.font_sm.render(f"Path: {path_str}", True, NODE_PATH)
        self.screen.blit(path_txt, (x, y + 22))

        # Stats
        stats = [
            (f"Nodes Explored: {r['nodes_explored']}", PURPLE),
            (f"Path Length: {r['path_len']} nodes", ACCENT),
            (f"Total Distance: {r['total_dist']} km", ACCENT2),
            (f"Total Risk Score: {r['total_risk']:.3f}", WARNING if r['total_risk'] > 1.5 else SUCCESS),
            (f"Total Cost: {r['total_cost']:.3f}", WHITE),
            (f"Compute Time: {r['time_ms']:.4f} ms", GRAY),
        ]
        sx = x
        sy = y + 44
        for s, col in stats:
            txt = self.font_sm.render(s, True, col)
            self.screen.blit(txt, (sx, sy))
            sx += 195
            if sx > x + w - 50:
                sx = x
                sy += 18

        sy += 22

        # Why this path was selected
        why = self._explain_algorithm(sel, r)
        self.screen.blit(self.font_sm.render("WHY THIS PATH:", True, GRAY), (x, sy))
        sy += 18
        for line in why:
            self.screen.blit(self.font_xs.render(line, True, LIGHT_GRAY), (x, sy))
            sy += 15

    def _explain_algorithm(self, algo, result):
        gender_note = "female traveler (higher vulnerability multiplier applied)" if self.gender == 'female' else "male traveler"
        time_note = "night time (1.7x risk multiplier active)" if self.time_of_day == 'night' else "daytime (standard risk)"
        group_note = "solo journey (no group safety reduction)" if self.group == 'solo' else "group journey (0.65x risk reduction)"

        explanations = {
            'BFS': [
                f"BFS explores all neighbors level by level (hop-by-hop). Finds shortest hop count path.",
                f"It does NOT consider edge weights or safety — result may not be distance/risk optimal.",
                f"Explored {result['nodes_explored']} nodes in FIFO queue order.",
            ],
            'DFS': [
                f"DFS dives as deep as possible before backtracking. Very fast but path is NOT optimal.",
                f"Useful for quickly finding any path, but ignores cost/safety entirely.",
                f"Explored {result['nodes_explored']} nodes via LIFO stack.",
            ],
            'UCS': [
                f"UCS (Dijkstra) always expands the lowest-cost node first. Guaranteed optimal cost path.",
                f"Cost = α*dist + β*time + γ*risk. Risk adjusted for: {gender_note}, {time_note}, {group_note}.",
                f"Explored {result['nodes_explored']} nodes — more than A* since no heuristic guides it.",
            ],
            'DLS': [
                f"DLS cuts off exploration at depth limit=8. May miss paths longer than the limit.",
                f"Faster than full DFS but completeness sacrificed beyond the limit.",
                f"Explored {result['nodes_explored']} nodes within depth boundary.",
            ],
            'IDS': [
                f"IDS runs DLS repeatedly with increasing depth limits. Optimal like BFS, memory-efficient like DFS.",
                f"Total node count is higher due to repeated re-exploration, but finds optimal hop path.",
                f"Total expanded across all iterations: {result['nodes_explored']} nodes.",
            ],
            'A*': [
                f"A* uses f(n)=g(n)+h(n). g(n)=accumulated cost, h(n)=admissible heuristic (SLD + min risk).",
                f"Heuristic: h(n) = α*SLD(n,goal) + γ*min_possible_risk. Admissible → NEVER overestimates.",
                f"Profile: {gender_note} | {time_note} | {group_note}.",
                f"Only {result['nodes_explored']} nodes explored — far fewer than blind searches. Most efficient!",
            ],
            'Greedy': [
                f"Greedy always picks the node with smallest h(n) (closest to goal). Very fast but NOT optimal.",
                f"It ignores accumulated cost g(n), so may take a shorter-looking but costlier path.",
                f"Explored {result['nodes_explored']} nodes. Good speed, lower accuracy than A*.",
            ],
        }
        return explanations.get(algo, ["Algorithm result."])

    def _draw_comparison(self, x, y, w, h):
        """Draw comparison table of all algorithms."""
        self.screen.blit(self.font_md.render("📊  Algorithm Comparison", True, WHITE), (x, y))
        y += 24

        headers = ['Algo', 'Found', 'Nodes Exp.', 'Path Len', 'Dist(km)', 'Risk', 'Cost', 'Time(ms)', 'Optimal?']
        col_w = [58, 45, 80, 70, 70, 60, 65, 80, 65]
        
        # Header row
        hx = x
        for i, (hdr, cw) in enumerate(zip(headers, col_w)):
            pygame.draw.rect(self.screen, (35, 42, 60), (hx, y, cw-2, 20))
            self.screen.blit(self.font_xs.render(hdr, True, ACCENT), (hx+3, y+4))
            hx += cw
        y += 22

        color_map = {'BFS':(60,140,200),'DFS':(180,80,80),'UCS':(60,180,120),
                     'DLS':(180,140,50),'IDS':(100,160,200),'A*':(160,80,220),'Greedy':(220,120,50)}
        optimal_algos = {'UCS', 'A*', 'BFS', 'IDS'}

        for algo, r in self.results.items():
            hx = x
            ac = color_map.get(algo, WHITE)
            row_bg = (28, 35, 50) if algo == self.selected_algo else (22, 28, 42)
            
            row_data = [
                (algo, ac),
                ('Yes' if r['found'] else 'No', SUCCESS if r['found'] else DANGER),
                (str(r['nodes_explored']), LIGHT_GRAY),
                (str(r['path_len']), LIGHT_GRAY),
                (str(r['total_dist']), ACCENT2),
                (f"{r['total_risk']:.2f}", WARNING if r['total_risk'] > 1.5 else SUCCESS),
                (f"{r['total_cost']:.2f}", LIGHT_GRAY),
                (f"{r['time_ms']:.3f}", GRAY),
                ('✓ Yes' if algo in optimal_algos else '✗ No', SUCCESS if algo in optimal_algos else WARNING),
            ]
            
            row_h = 18
            for i, ((txt, col), cw) in enumerate(zip(row_data, col_w)):
                pygame.draw.rect(self.screen, row_bg, (hx, y, cw-2, row_h))
                self.screen.blit(self.font_xs.render(str(txt), True, col), (hx+3, y+3))
                hx += cw
            y += row_h + 1

        y += 8
        note = "* Optimal = guaranteed to find the best-cost path | A* is optimal AND efficient (fewest nodes explored)"
        self.screen.blit(self.font_xs.render(note, True, GRAY), (x, y))
        y += 16
        note2 = f"Profile: Gender={self.gender.upper()} | Journey={self.group.upper()} | Time={self.time_of_day.upper()}"
        self.screen.blit(self.font_xs.render(note2, True, ACCENT), (x, y))

    def _draw_comparison_panel(self, x, y, w):
        """Vertical comparison table for the right panel (narrow, scrollable)."""
        color_map = {'BFS':(60,140,200),'DFS':(180,80,80),'UCS':(60,180,120),
                     'DLS':(180,140,50),'IDS':(100,160,200),'A*':(160,80,220),'Greedy':(220,120,50)}
        optimal_algos = {'UCS', 'A*', 'BFS', 'IDS'}

        title = self.font_sm.render("📊 Algorithm Comparison", True, WHITE)
        self.screen.blit(title, (x, y)); y += 20

        profile = f"{self.gender.upper()} | {self.group.upper()} | {self.time_of_day.upper()}"
        p_txt = self.font_xs.render(profile, True, ACCENT)
        self.screen.blit(p_txt, (x, y)); y += 16

        for algo, r in self.results.items():
            ac = color_map.get(algo, WHITE)
            is_sel = algo == self.selected_algo
            # Card background
            card_col = (35, 42, 62) if is_sel else (25, 30, 46)
            pygame.draw.rect(self.screen, card_col, (x, y, w, 70), border_radius=6)
            if is_sel:
                pygame.draw.rect(self.screen, ac, (x, y, w, 70), 1, border_radius=6)

            # Algo name
            self.screen.blit(self.font_sm.render(algo, True, ac), (x+6, y+4))
            found_col = SUCCESS if r['found'] else DANGER
            found_txt = "✓ Found" if r['found'] else "✗ Not found"
            ft = self.font_xs.render(found_txt, True, found_col)
            self.screen.blit(ft, (x + w - ft.get_width() - 6, y + 6))

            # Optimal badge
            opt_txt = "OPTIMAL" if algo in optimal_algos else "NOT OPT."
            opt_col = SUCCESS if algo in optimal_algos else WARNING
            self.screen.blit(self.font_xs.render(opt_txt, True, opt_col), (x+6, y+22))

            # Stats row 1
            s1 = f"Nodes: {r['nodes_explored']}  |  Hops: {r['path_len']}"
            self.screen.blit(self.font_xs.render(s1, True, LIGHT_GRAY), (x+6, y+36))
            # Stats row 2
            s2 = f"Dist: {r['total_dist']}km  Risk: {r['total_risk']:.2f}  t:{r['time_ms']:.3f}ms"
            self.screen.blit(self.font_xs.render(s2, True, GRAY), (x+6, y+50))

            y += 76

        # Footer note
        note = self.font_xs.render("* UCS/A*/BFS/IDS = optimal cost path", True, GRAY)
        self.screen.blit(note, (x, y)); y += 14
        note2 = self.font_xs.render("A* = optimal + most efficient", True, ACCENT2)
        self.screen.blit(note2, (x, y))

    def draw_header(self):
        """Draw top header."""
        pygame.draw.rect(self.screen, (18, 22, 35), (0, 0, W, 112))
        pygame.draw.line(self.screen, PANEL_BORDER, (0, 112), (W, 112), 1)

        title = self.font_title.render("AI Lab — Safety-Aware Urban Route Planner", True, WHITE)
        self.screen.blit(title, (20, 15))

        sub = self.font_sm.render(
            "Cost(A,B) = α·Distance + β·Time + γ·Risk_gender   |   "
            "Risk = base_risk × gender_mult × group_mult × time_mult   |   "
            "h(n) = α·SLD(n,goal) + γ·min_risk  [Admissible Heuristic]",
            True, GRAY
        )
        self.screen.blit(sub, (20, 52))

        # Status bar
        pygame.draw.rect(self.screen, CARD_BG, (20, 76, 820, 28), border_radius=6)
        status = self.font_sm.render(self.status_msg, True, self.status_color)
        self.screen.blit(status, (28, 82))

    def handle_click(self, mx, my):
        """Handle mouse clicks."""
        # Check node clicks on map
        if MAP_X <= mx <= MAP_X+MAP_W and MAP_Y <= my <= MAP_Y+MAP_H:
            node = self.node_at(mx, my)
            if node:
                if self.start_node is None:
                    self.start_node = node
                    self.status_msg = f"Start set: {node} ({NODES[node]['name']}). Now click End node."
                    self.status_color = NODE_START
                elif self.end_node is None and node != self.start_node:
                    self.end_node = node
                    self.status_msg = f"End set: {node} ({NODES[node]['name']}). Choose options and click RUN."
                    self.status_color = NODE_END
                else:
                    # Re-select: first click resets start
                    self.start_node = node
                    self.end_node = None
                    self.results = None
                    self.status_msg = f"Start reset: {node}. Click another node for End."
                    self.status_color = NODE_START
            return

        # Check buttons
        for key, rect in self.buttons.items():
            if rect.collidepoint(mx, my):
                self._handle_button(key)
                return

    def _handle_button(self, key):
        if key.startswith('gender_'):
            self.gender = key.split('_')[1]
        elif key.startswith('group_'):
            self.group = key.split('_')[1]
        elif key.startswith('time_'):
            self.time_of_day = key.split('_')[1]
        elif key.startswith('algo_'):
            self.algorithm = key[5:]
            self.selected_algo = self.algorithm
        elif key == 'run':
            self._run_search()
        elif key == 'compare':
            self.show_comparison = not self.show_comparison
        elif key == 'reset':
            self._reset()

    def _run_search(self):
        if not self.start_node or not self.end_node:
            self.status_msg = "Please select both Start and End nodes first!"
            self.status_color = DANGER
            return

        self.selected_algo = self.algorithm
        self.show_comparison = False

        self.results, self.graph, self.edge_risk_map = run_all_algorithms(
            self.start_node, self.end_node, self.gender, self.group, self.time_of_day
        )

        r = self.results[self.algorithm]
        if r['found']:
            self.status_msg = (
                f"{self.algorithm}: Path found! "
                f"{r['path_len']} nodes | {r['total_dist']}km | "
                f"Risk:{r['total_risk']:.3f} | Explored:{r['nodes_explored']} nodes"
            )
            self.status_color = SUCCESS
        else:
            self.status_msg = f"{self.algorithm}: No path found between {self.start_node} and {self.end_node}!"
            self.status_color = DANGER

        # Trigger animation
        self.animating = True
        self.anim_step = 0
        self.anim_timer = 0

    def _reset(self):
        self.start_node = None
        self.end_node = None
        self.results = None
        self.animating = False
        self.anim_step = 0
        self.show_comparison = False
        self.result_scroll = 0
        self.status_msg = "Reset! Click two nodes on the map to set Start and End points."
        self.status_color = LIGHT_GRAY

    def update_animation(self, dt):
        if not self.animating:
            return
        self.anim_timer += dt
        if self.anim_timer > 80:  # ms per step
            self.anim_timer = 0
            sel = self.selected_algo
            if self.results and sel in self.results:
                max_steps = len(self.results[sel]['explored_order'])
                if self.anim_step < max_steps:
                    self.anim_step += 1
                else:
                    self.animating = False

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            mx, my = pygame.mouse.get_pos()
            self.hover_node = self.node_at(mx, my) if (MAP_X <= mx <= MAP_X+MAP_W and MAP_Y <= my <= MAP_Y+MAP_H) else None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(mx, my)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._reset()
                    elif event.key == pygame.K_RETURN:
                        self._run_search()
                    elif event.key == pygame.K_c:
                        self.show_comparison = not self.show_comparison
                    elif event.key == pygame.K_s:
                        self.result_scroll = min(self.result_scroll + 30, 600)
                    elif event.key == pygame.K_w:
                        self.result_scroll = max(self.result_scroll - 30, 0)
                if event.type == pygame.MOUSEWHEEL:
                    mx2, my2 = pygame.mouse.get_pos()
                    if mx2 > 855:  # right panel
                        self.result_scroll = max(0, min(self.result_scroll - event.y * 25, 600))

            self.update_animation(dt)

            # Draw
            self.screen.fill(BG)
            self.draw_header()
            self.draw_map_background()
            self.draw_edges()
            self.draw_nodes()
            self.draw_right_panel()
            self.draw_bottom_panel()

            pygame.display.flip()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = App()
    app.run()