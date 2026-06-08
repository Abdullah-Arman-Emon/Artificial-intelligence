import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import heapq
import math
from collections import deque
import random

# ============================================================
# Graph Definition: 25 nodes (locations)
# ============================================================
nodes = [
    (0, "TSC", 2.0, 8.0),
    (1, "SH Hall", 1.0, 6.5),
    (2, "DMC", 3.0, 6.0),
    (3, "FH Hall", 4.5, 7.0),
    (4, "Central Field", 3.0, 4.5),
    (5, "Library", 5.0, 5.0),
    (6, "Admin Building", 1.5, 3.5),
    (7, "Cafeteria", 4.0, 3.0),
    (8, "Science Block", 6.0, 6.5),
    (9, "Engineering Hall", 7.0, 4.0),
    (10, "Business School", 5.5, 8.0),
    (11, "Hostel A", 0.5, 9.0),
    (12, "Hostel B", 7.5, 8.5),
    (13, "Gym", 6.0, 2.0),
    (14, "Auditorium", 3.5, 1.5),
    (15, "Health Center", 1.0, 1.0),
    (16, "Parking North", 0.5, 4.0),
    (17, "Parking South", 8.0, 2.5),
    (18, "Guest House", 8.5, 6.0),
    (19, "Stadium", 2.5, 9.5),
    (20, "Campus Gate", 4.0, 9.0),
    (21, "Research Center", 6.5, 7.5),
    (22, "Child Care", 2.0, 2.0),
    (23, "Faculty Club", 5.0, 1.0),
    (24, "Bus Stop", 7.0, 9.0)
]

# Edges: only (u, v, distance) - no hardcoded risk!
edges_raw = [
    (0,1, 1.8), (0,2, 2.0), (0,11, 1.5), (0,19, 1.7), (0,20, 2.2),
    (1,6, 2.5), (1,11, 1.2), (1,16, 2.0),
    (2,3, 2.0), (2,4, 1.5), (2,7, 2.8),
    (3,5, 2.2), (3,8, 2.5), (3,10, 2.0),
    (4,6, 2.0), (4,7, 1.3), (4,14, 2.5), (4,22, 1.8),
    (5,7, 1.5), (5,8, 1.2), (5,10, 1.8),
    (6,15, 2.0), (6,16, 1.3),
    (7,9, 2.5), (7,13, 2.2), (7,14, 1.2),
    (8,9, 1.5), (8,12, 2.0), (8,18, 2.5), (8,21, 1.8),
    (9,13, 1.5), (9,17, 1.8), (9,18, 1.2),
    (10,12, 2.0), (10,20, 1.8), (10,21, 1.5),
    (11,19, 1.8), (11,16, 2.2),
    (12,18, 1.5), (12,24, 1.8),
    (13,14, 1.5), (13,17, 1.8), (13,23, 2.0),
    (14,15, 2.0), (14,22, 1.2), (14,23, 2.2),
    (15,22, 1.5), (15,16, 2.0),
    (17,23, 1.8), (17,24, 2.5),
    (18,21, 1.5), (18,24, 2.0),
    (19,20, 1.2),
    (20,24, 2.2),
    (21,24, 1.8)
]

# ============================================================
# Dynamic Risk Storage (no hardcoding)
# ============================================================
# We'll store base_risk for each directed edge in a dictionary.
# For undirected, we store both directions.
base_risk = {}

def generate_random_risks(risk_min=1.0, risk_max=10.0):
    """Generate fresh random base risks for all edges."""
    global base_risk
    base_risk.clear()
    for u, v, dist in edges_raw:
        risk = random.uniform(risk_min, risk_max)
        base_risk[(u, v)] = risk
        base_risk[(v, u)] = risk   # symmetric
    # Also store adjacency list with distances (risks will be looked up)
    global adj
    adj = [[] for _ in range(len(nodes))]
    for u, v, dist in edges_raw:
        adj[u].append((v, dist))
        adj[v].append((u, dist))

# Initialize with random risks
random.seed(42)  # Optional: remove this line to get truly random each run
generate_random_risks()

# ============================================================
# Dynamic Risk Factors (multipliers)
# ============================================================
def compute_dynamic_risk(base_risk_val, gender, time_of_day, journey_type):
    gender_mult = 1.0 if gender == 'Male' else 1.6
    time_mult = 1.0 if time_of_day == 'Day' else 1.7
    journey_mult = 1.4 if journey_type == 'Alone' else 0.8
    extra_factor = 1.2 if (gender == 'Female' and time_of_day == 'Night') else 1.0
    return base_risk_val * gender_mult * time_mult * journey_mult * extra_factor

# ============================================================
# Cost Function Factory (uses dynamic base_risk lookup)
# ============================================================
def get_cost_function(path_pref, gender, time_of_day, journey_type):
    dist_weight = 1.0 if path_pref == 'Shortest' else 0.2
    risk_weight = 0.2 if path_pref == 'Shortest' else 1.0
    
    def cost(u, v):
        # Find distance
        for nei, dist in adj[u]:
            if nei == v:
                base_risk_val = base_risk.get((u, v), 5.0)  # fallback 5.0 if missing
                dynamic_risk = compute_dynamic_risk(base_risk_val, gender, time_of_day, journey_type)
                return dist * dist_weight + dynamic_risk * risk_weight
        raise ValueError(f"Edge {u}-{v} not found")
    return cost

# ============================================================
# Heuristic (admissible: only distance component)
# ============================================================
def get_heuristic(path_pref):
    dist_weight = 1.0 if path_pref == 'Shortest' else 0.2
    def heuristic(node_idx, goal_idx):
        x1, y1 = nodes[node_idx][2], nodes[node_idx][3]
        x2, y2 = nodes[goal_idx][2], nodes[goal_idx][3]
        return math.hypot(x1 - x2, y1 - y2) * dist_weight
    return heuristic

# ============================================================
# Search Algorithms (unchanged, but they now use dynamic cost_func)
# ============================================================
def bfs(start, goal, cost_func, graph_size, adj_list):
    visited = [False] * graph_size
    parent = [-1] * graph_size
    queue = deque([start])
    visited[start] = True
    nodes_expanded = 0
    while queue:
        u = queue.popleft()
        nodes_expanded += 1
        if u == goal:
            break
        for v, _ in adj_list[u]:
            if not visited[v]:
                visited[v] = True
                parent[v] = u
                queue.append(v)
    if not visited[goal]:
        return None, nodes_expanded
    path = []
    cur = goal
    while cur != -1:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path, nodes_expanded

def dfs(start, goal, cost_func, graph_size, adj_list):
    visited = [False] * graph_size
    parent = [-1] * graph_size
    stack = [start]
    visited[start] = True
    nodes_expanded = 0
    while stack:
        u = stack.pop()
        nodes_expanded += 1
        if u == goal:
            break
        for v, _ in adj_list[u]:
            if not visited[v]:
                visited[v] = True
                parent[v] = u
                stack.append(v)
    if not visited[goal]:
        return None, nodes_expanded
    path = []
    cur = goal
    while cur != -1:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path, nodes_expanded

def ucs(start, goal, cost_func, graph_size, adj_list):
    frontier = [(0.0, start, [start])]
    visited_cost = {}
    nodes_expanded = 0
    while frontier:
        cost, u, path = heapq.heappop(frontier)
        nodes_expanded += 1
        if u == goal:
            return path, nodes_expanded
        if u in visited_cost and visited_cost[u] <= cost:
            continue
        visited_cost[u] = cost
        for v, _ in adj_list[u]:
            edge_cost = cost_func(u, v)
            new_cost = cost + edge_cost
            new_path = path + [v]
            heapq.heappush(frontier, (new_cost, v, new_path))
    return None, nodes_expanded

def a_star(start, goal, cost_func, heuristic_func, graph_size, adj_list):
    frontier = [(0.0, start, [start], 0.0)]
    visited = {}
    nodes_expanded = 0
    while frontier:
        f, u, path, g = heapq.heappop(frontier)
        nodes_expanded += 1
        if u == goal:
            return path, nodes_expanded
        if u in visited and visited[u] <= g:
            continue
        visited[u] = g
        for v, _ in adj_list[u]:
            edge_cost = cost_func(u, v)
            new_g = g + edge_cost
            new_f = new_g + heuristic_func(v, goal)
            new_path = path + [v]
            heapq.heappush(frontier, (new_f, v, new_path, new_g))
    return None, nodes_expanded

def weighted_a_star(start, goal, cost_func, heuristic_func, graph_size, adj_list, weight=1.5):
    frontier = [(0.0, start, [start], 0.0)]
    visited = {}
    nodes_expanded = 0
    while frontier:
        f, u, path, g = heapq.heappop(frontier)
        nodes_expanded += 1
        if u == goal:
            return path, nodes_expanded
        if u in visited and visited[u] <= g:
            continue
        visited[u] = g
        for v, _ in adj_list[u]:
            edge_cost = cost_func(u, v)
            new_g = g + edge_cost
            new_f = new_g + weight * heuristic_func(v, goal)
            new_path = path + [v]
            heapq.heappush(frontier, (new_f, v, new_path, new_g))
    return None, nodes_expanded

def greedy_best_first(start, goal, cost_func, heuristic_func, graph_size, adj_list):
    frontier = [(heuristic_func(start, goal), start, [start])]
    visited = set()
    nodes_expanded = 0
    while frontier:
        _, u, path = heapq.heappop(frontier)
        nodes_expanded += 1
        if u == goal:
            return path, nodes_expanded
        if u in visited:
            continue
        visited.add(u)
        for v, _ in adj_list[u]:
            if v not in visited:
                heapq.heappush(frontier, (heuristic_func(v, goal), v, path + [v]))
    return None, nodes_expanded

def depth_limited_search(start, goal, cost_func, graph_size, adj_list, limit):
    parent = {}
    nodes_expanded = 0
    def recursive_dls(u, depth):
        nonlocal nodes_expanded
        nodes_expanded += 1
        if u == goal:
            return [u]
        if depth == limit:
            return None
        for v, _ in adj_list[u]:
            if v not in parent:
                parent[v] = u
                result = recursive_dls(v, depth + 1)
                if result is not None:
                    return [u] + result
                del parent[v]
        return None
    parent[start] = None
    path = recursive_dls(start, 0)
    if path is None:
        return None, nodes_expanded
    return path, nodes_expanded

def iddfs(start, goal, cost_func, graph_size, adj_list, max_depth=30):
    for depth in range(max_depth):
        path, expanded = depth_limited_search(start, goal, cost_func, graph_size, adj_list, depth)
        if path is not None:
            return path, expanded
    return None, 0

# ============================================================
# GUI Application (with "Regenerate Risks" button)
# ============================================================
class RoutingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Urban Routing System - Fully Dynamic Risk (No Hardcoding)")
        self.root.geometry("1300x750")
        
        self.start_node = None
        self.goal_node = None
        
        self.gender_var = tk.StringVar(value="Male")
        self.journey_var = tk.StringVar(value="Alone")
        self.time_var = tk.StringVar(value="Day")
        self.path_pref_var = tk.StringVar(value="Shortest")
        self.algorithm_var = tk.StringVar(value="A*")
        
        self.algorithms = {
            "BFS": bfs,
            "DFS": dfs,
            "UCS": ucs,
            "DLS (depth=10)": lambda s,g,c,sz,adj: depth_limited_search(s,g,c,sz,adj,10),
            "IDDFS": iddfs,
            "A*": a_star,
            "Weighted A*": lambda s,g,c,h_func,sz,adj: weighted_a_star(s,g,c,h_func,sz,adj,1.5),
            "Greedy Best-First": greedy_best_first
        }
        
        self.setup_ui()
        self.draw_map()
    
    def setup_ui(self):
        left_frame = ttk.Frame(self.root, width=350, padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig = Figure(figsize=(7, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        ttk.Label(left_frame, text="Start & End Nodes:", font=('Arial', 12, 'bold')).pack(pady=5)
        self.start_label = ttk.Label(left_frame, text="Start: Not selected", foreground="blue")
        self.start_label.pack()
        self.goal_label = ttk.Label(left_frame, text="Goal: Not selected", foreground="green")
        self.goal_label.pack()
        ttk.Button(left_frame, text="Clear Selection", command=self.clear_selection).pack(pady=5)
        
        ttk.Separator(left_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        ttk.Label(left_frame, text="Traveler Profile", font=('Arial', 11, 'bold')).pack(pady=5)
        ttk.Radiobutton(left_frame, text="Male", variable=self.gender_var, value="Male").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="Female", variable=self.gender_var, value="Female").pack(anchor=tk.W)
        
        ttk.Label(left_frame, text="Journey Type", font=('Arial', 11, 'bold')).pack(pady=5)
        ttk.Radiobutton(left_frame, text="Alone", variable=self.journey_var, value="Alone").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="Group", variable=self.journey_var, value="Group").pack(anchor=tk.W)
        
        ttk.Label(left_frame, text="Time of Day", font=('Arial', 11, 'bold')).pack(pady=5)
        ttk.Radiobutton(left_frame, text="Day", variable=self.time_var, value="Day").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="Night", variable=self.time_var, value="Night").pack(anchor=tk.W)
        
        ttk.Label(left_frame, text="Path Preference", font=('Arial', 11, 'bold')).pack(pady=5)
        ttk.Radiobutton(left_frame, text="Shortest (faster, less safe)", variable=self.path_pref_var, value="Shortest").pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="Safest (prioritize low risk)", variable=self.path_pref_var, value="Safest").pack(anchor=tk.W)
        
        ttk.Label(left_frame, text="Search Algorithm", font=('Arial', 11, 'bold')).pack(pady=5)
        algo_combo = ttk.Combobox(left_frame, textvariable=self.algorithm_var, values=list(self.algorithms.keys()), state="readonly")
        algo_combo.pack(fill=tk.X)
        algo_combo.current(5)
        
        ttk.Button(left_frame, text="Find Path", command=self.find_path, style="Accent.TButton").pack(pady=5)
        ttk.Button(left_frame, text="Compare All Algorithms", command=self.compare_all).pack(pady=5)
        
        # NEW BUTTON: Regenerate dynamic risks
        ttk.Button(left_frame, text="🔄 Regenerate Risks (Dynamic)", command=self.regenerate_risks).pack(pady=5)
        
        ttk.Label(left_frame, text="Results & Details", font=('Arial', 11, 'bold')).pack(pady=5)
        self.output_text = scrolledtext.ScrolledText(left_frame, height=18, width=45, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="green")
    
    def regenerate_risks(self):
        """Generate brand new random base risks for all edges."""
        generate_random_risks()
        self.draw_map()  # redraw to show new risk numbers
        self.output_text.insert(tk.END, "\n--- RISKS REGENERATED DYNAMICALLY ---\n")
        self.output_text.insert(tk.END, "All base risks have been re-rolled. Any new path search will use the updated risks.\n")
        self.output_text.see(tk.END)
    
    def draw_map(self, path=None):
        self.ax.clear()
        # Draw edges with current dynamic base risk values
        for u, v, dist in edges_raw:
            x1, y1 = nodes[u][2], nodes[u][3]
            x2, y2 = nodes[v][2], nodes[v][3]
            self.ax.plot([x1, x2], [y1, y2], 'gray', linestyle='-', linewidth=1, alpha=0.6)
            risk_val = base_risk.get((u, v), 5.0)
            mx, my = (x1+x2)/2, (y1+y2)/2
            self.ax.annotate(f"{risk_val:.1f}", (mx, my), fontsize=6, color='darkred', alpha=0.7)
        
        # Draw nodes
        xs = [node[2] for node in nodes]
        ys = [node[3] for node in nodes]
        colors = []
        for idx, _, _, _ in nodes:
            if idx == self.start_node:
                colors.append('lime')
            elif idx == self.goal_node:
                colors.append('orange')
            else:
                colors.append('lightblue')
        self.scatter = self.ax.scatter(xs, ys, s=200, c=colors, edgecolors='black', zorder=5, picker=True)
        
        for idx, label, x, y in nodes:
            self.ax.annotate(label, (x, y), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, fontweight='bold')
        
        if path:
            path_coords = [(nodes[idx][2], nodes[idx][3]) for idx in path]
            xs_p, ys_p = zip(*path_coords)
            self.ax.plot(xs_p, ys_p, 'r-', linewidth=3, alpha=0.8, label='Optimal Path')
            self.ax.legend()
        
        self.ax.set_title("Campus Map - Base Risks Shown (Dynamic) | Click nodes to select Start/Goal")
        self.ax.set_xlabel("X coordinate")
        self.ax.set_ylabel("Y coordinate")
        self.ax.grid(True, linestyle=':', alpha=0.3)
        self.canvas.draw()
    
    def on_pick(self, event):
        if event.artist != self.scatter:
            return
        ind = event.ind[0]
        clicked_idx = nodes[ind][0]
        if self.start_node is None:
            self.start_node = clicked_idx
            self.start_label.config(text=f"Start: {nodes[clicked_idx][1]}")
        elif self.goal_node is None and clicked_idx != self.start_node:
            self.goal_node = clicked_idx
            self.goal_label.config(text=f"Goal: {nodes[clicked_idx][1]}")
        else:
            messagebox.showinfo("Info", "Already selected start/goal. Use 'Clear Selection' to reset.")
        self.draw_map()
    
    def clear_selection(self):
        self.start_node = None
        self.goal_node = None
        self.start_label.config(text="Start: Not selected")
        self.goal_label.config(text="Goal: Not selected")
        self.draw_map()
        self.output_text.delete(1.0, tk.END)
    
    def get_current_cost_heuristic(self):
        cost_func = get_cost_function(self.path_pref_var.get(), self.gender_var.get(),
                                      self.time_var.get(), self.journey_var.get())
        heuristic_func = get_heuristic(self.path_pref_var.get())
        return cost_func, heuristic_func
    
    def compute_path_cost(self, path, cost_func):
        if not path or len(path) < 2:
            return 0.0
        total = 0.0
        for i in range(len(path)-1):
            total += cost_func(path[i], path[i+1])
        return total
    
    def get_path_details(self, path, cost_func):
        if not path:
            return "No path found."
        details = "Path: " + " -> ".join([nodes[idx][1] for idx in path]) + "\n"
        total_cost = 0.0
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            edge_cost = cost_func(u, v)
            total_cost += edge_cost
            # Retrieve base risk and distance for display
            for nei, dist in adj[u]:
                if nei == v:
                    base_risk_val = base_risk.get((u, v), 5.0)
                    dynamic_risk = compute_dynamic_risk(base_risk_val, self.gender_var.get(),
                                                        self.time_var.get(), self.journey_var.get())
                    details += f"  {nodes[u][1]} -> {nodes[v][1]}: distance={dist:.1f}, base_risk={base_risk_val:.2f}, dynamic_risk={dynamic_risk:.2f}, cost={edge_cost:.3f}\n"
                    break
        details += f"\nTotal Cost: {total_cost:.4f}\n"
        details += f"Path Preference: {self.path_pref_var.get()}\n"
        details += f"Risk factors: Gender={self.gender_var.get()}, Time={self.time_var.get()}, Journey={self.journey_var.get()}\n"
        return details
    
    def find_path(self):
        if self.start_node is None or self.goal_node is None:
            messagebox.showwarning("Selection Error", "Please select start and goal nodes by clicking on map.")
            return
        
        algo_name = self.algorithm_var.get()
        algo_func = self.algorithms[algo_name]
        cost_func, heuristic_func = self.get_current_cost_heuristic()
        
        if algo_name in ["A*", "Weighted A*", "Greedy Best-First"]:
            path, expanded = algo_func(self.start_node, self.goal_node, cost_func, heuristic_func, len(nodes), adj)
        else:
            path, expanded = algo_func(self.start_node, self.goal_node, cost_func, len(nodes), adj)
        
        self.output_text.delete(1.0, tk.END)
        if path is None:
            self.output_text.insert(tk.END, f"Algorithm {algo_name} could not find a path!\n")
            return
        
        total_cost = self.compute_path_cost(path, cost_func)
        details = self.get_path_details(path, cost_func)
        self.output_text.insert(tk.END, f"Algorithm: {algo_name}\n")
        self.output_text.insert(tk.END, f"Nodes expanded: {expanded}\n")
        self.output_text.insert(tk.END, f"Path length (edges): {len(path)-1}\n")
        self.output_text.insert(tk.END, f"Total cost: {total_cost:.4f}\n")
        self.output_text.insert(tk.END, "\n--- Detailed Path Analysis ---\n")
        self.output_text.insert(tk.END, details)
        
        self.draw_map(path)
    
    def compare_all(self):
        if self.start_node is None or self.goal_node is None:
            messagebox.showwarning("Selection Error", "Please select start and goal nodes first.")
            return
        
        cost_func, heuristic_func = self.get_current_cost_heuristic()
        results = []
        
        for name, func in self.algorithms.items():
            try:
                if name in ["A*", "Weighted A*", "Greedy Best-First"]:
                    path, expanded = func(self.start_node, self.goal_node, cost_func, heuristic_func, len(nodes), adj)
                else:
                    path, expanded = func(self.start_node, self.goal_node, cost_func, len(nodes), adj)
                
                if path:
                    total_cost = self.compute_path_cost(path, cost_func)
                    results.append((name, total_cost, expanded, len(path)-1, path))
                else:
                    results.append((name, float('inf'), expanded, 0, None))
            except Exception as e:
                results.append((name, float('inf'), 0, 0, None))
        
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "===== ALGORITHM COMPARISON =====\n")
        self.output_text.insert(tk.END, f"Settings: Gender={self.gender_var.get()}, Time={self.time_var.get()}, Journey={self.journey_var.get()}, Preference={self.path_pref_var.get()}\n\n")
        self.output_text.insert(tk.END, f"{'Algorithm':<20} {'Total Cost':<12} {'Nodes Expanded':<15} {'Path Length':<12} {'Optimal?'}\n")
        self.output_text.insert(tk.END, "-"*70 + "\n")
        
        best_cost = min((r[1] for r in results if r[1] != float('inf')), default=None)
        for name, cost, expanded, length, _ in results:
            if cost == float('inf'):
                cost_str = "No path"
                opt = ""
            else:
                cost_str = f"{cost:.4f}"
                opt = "Yes" if best_cost is not None and abs(cost - best_cost) < 1e-6 else ""
            self.output_text.insert(tk.END, f"{name:<20} {cost_str:<12} {expanded:<15} {length:<12} {opt}\n")
        
        self.output_text.insert(tk.END, "\n--- Detailed Best Path (lowest cost) ---\n")
        best = min(results, key=lambda x: x[1] if x[1] != float('inf') else float('inf'))
        if best[1] != float('inf'):
            self.output_text.insert(tk.END, f"Algorithm: {best[0]}\n")
            self.output_text.insert(tk.END, self.get_path_details(best[4], cost_func))
        else:
            self.output_text.insert(tk.END, "No algorithm found a valid path.\n")
        
        if best[4]:
            self.draw_map(best[4])
        else:
            self.draw_map()

# ============================================================
# Main execution
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = RoutingApp(root)
    root.mainloop()