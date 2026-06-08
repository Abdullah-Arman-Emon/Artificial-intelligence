"""
AI Lab: Safety-Aware Urban Route Planning
Adapted for standard laptop screens (1280×720, no scaling blur)
"""
import pygame, math, heapq, sys, time
from collections import deque

# ─── SCALED LAYOUT (from 1600×920 to 1280×720) ──────────────────────────────
ORIG_W, ORIG_H = 1280, 720
# Scale factors relative to original 1600x920
sx = 1280 / 1600   # 0.8
sy = 720 / 920     # ≈0.7826

def scale_pos(x, y):
    return (int(x * sx), int(y * sy))

def scale_size(w, h):
    return (int(w * sx), int(h * sy))

MAP_X, MAP_Y   = scale_pos(10, 110)
MAP_W, MAP_H   = scale_size(900, 660)
RP_X           = int(930 * sx)
RP_W           = ORIG_W - RP_X - 6   # ≈ 664 * sx
FPS            = 60

# ─── COLOURS (unchanged) ────────────────────────────────────────────────────
BG    = (13,15,23);  PANEL_BG=(20,24,36);  PANEL_BORDER=(42,50,70)
CARD  = (26,31,46);  CARD2=(32,38,56);     DGRAY=(36,42,60)
WHITE = (238,244,255); GRAY=(110,122,148); LGRAY=(175,188,210)
ACCENT=(72,152,255);  ACCENT2=(100,196,130); DANGER=(215,68,72)
WARNING=(252,165,42); SUCCESS=(52,196,110);  PURPLE=(152,90,218)
ORANGE=(230,130,40);  TEAL=(40,188,188)
NODE_DEFAULT=(50,122,195); NODE_HOVER=(75,170,252); NODE_START=(44,196,112)
NODE_END=(215,62,75);      NODE_PATH=(252,196,44);  NODE_EXPLORED=(172,88,215)
NODE_TEXT=(238,244,255);   EDGE_PATH=(252,196,44)

# ─── MAP DATA (positions scaled) ────────────────────────────────────────────
NODES_RAW = {
    'A':(75, 75), 'B':(195,52), 'C':(335,68), 'D':(475,48), 'E':(615,78),
    'F':(115,195),'G':(255,182),'H':(395,168),'I':(535,185),'J':(675,165),
    'K':(755,105),'L':(75,315), 'M':(205,305),'N':(345,295),'O':(485,300),
    'P':(635,290),'Q':(755,275),'R':(125,445),'S':(275,455),'T':(425,450),
    'U':(575,455),'V':(705,445),
}
NODES = {}
for name, (x,y) in NODES_RAW.items():
    NODES[name] = {'pos': (int(x*sx), int(y*sy)), 'name': name, 'type': 'generic'}
# Assign proper names (unchanged)
names = {
    'A':'City Hall','B':'University','C':'Hospital','D':'Airport','E':'Tech Park',
    'F':'Central Market','G':'Police Station','H':'Train Station','I':'Shopping Mall',
    'J':'Sports Complex','K':'Industrial Zone','L':'Old Town','M':'Park',
    'N':'Bus Terminal','O':'Financial District','P':'Hotel Zone','Q':'Dockyard',
    'R':'Slum Area','S':'Suburb North','T':'Suburb South','U':'Night Market','V':'Outskirts'
}
for k in NODES: NODES[k]['name'] = names[k]

EDGES_RAW = [  # (n1, n2, dist_km, base_risk)
    ('A','B',2.1,.10),('A','F',1.8,.15),('A','L',3.2,.30),
    ('B','C',2.5,.10),('B','G',2.0,.10),('B','F',2.3,.15),
    ('C','D',3.0,.10),('C','H',2.2,.12),('C','G',1.9,.10),
    ('D','E',2.8,.15),('D','H',2.5,.10),('D','I',3.1,.20),
    ('E','J',2.0,.20),('E','K',1.5,.35),('E','I',2.4,.15),
    ('F','G',1.5,.12),('F','L',2.8,.25),('F','M',2.0,.15),
    ('G','H',2.3,.10),('G','M',1.8,.12),('G','N',2.5,.15),
    ('H','I',2.1,.20),('H','N',1.9,.18),('H','O',2.6,.20),
    ('I','J',2.0,.20),('I','O',2.2,.20),('I','P',2.5,.20),
    ('J','K',1.8,.40),('J','P',2.3,.25),('J','Q',2.0,.35),
    ('K','Q',2.5,.50),
    ('L','M',2.2,.20),('L','R',2.5,.55),
    ('M','N',2.0,.18),('M','S',2.8,.22),
    ('N','O',2.1,.20),('N','S',2.4,.25),('N','T',2.6,.22),
    ('O','P',2.0,.20),('O','T',2.2,.22),
    ('P','Q',2.8,.30),('P','U',2.4,.28),
    ('Q','V',2.0,.50),
    ('R','S',2.3,.45),
    ('S','T',2.5,.25),('S','R',2.3,.45),
    ('T','U',2.2,.30),('T','S',2.5,.25),
    ('U','V',2.1,.40),('U','P',2.4,.28),
    ('V','Q',2.0,.50),
]

WEIGHT_PROFILES = {'safe': (0.10, 0.05, 0.85), 'risky': (0.55, 0.35, 0.10)}
DEFAULT_RP = {
    'female_coef':3.5, 'female_exp':1.5, 'male_coef':0.8,
    'night_mult':2.8, 'evening_mult':1.6, 'group_factor':0.50,
}

# ─── RISK MODEL (unchanged) ─────────────────────────────────────────────────
def compute_risk(base_risk, gender, group, tod, rp):
    if gender=='female':
        gm = 1.0 + rp['female_coef'] * (base_risk ** rp['female_exp'])
    else:
        gm = 1.0 + rp['male_coef'] * base_risk
    grm = rp['group_factor'] if group=='group' else 1.0
    tm = rp['night_mult'] if tod=='night' else (rp['evening_mult'] if tod=='evening' else 1.0)
    return base_risk * gm * grm * tm

def edge_cost(dist, risk, mode):
    a,b,g = WEIGHT_PROFILES[mode]
    return a*dist/3.5 + b*dist*4.0/14.0 + g*risk/14.0

def build_graph(gender, group, tod, mode, rp):
    graph={n:{} for n in NODES}; emap={}
    for n1,n2,dist,br in EDGES_RAW:
        risk=compute_risk(br,gender,group,tod,rp)
        cost=edge_cost(dist,risk,mode)
        d={'cost':cost,'dist':dist,'risk':risk,'base_risk':br}
        graph[n1][n2]=d; graph[n2][n1]=d
        emap[(n1,n2)]=risk; emap[(n2,n1)]=risk
    return graph,emap

def heuristic(node, goal, gender, group, tod, mode, rp):
    nx,ny=NODES[node]['pos']; gx,gy=NODES[goal]['pos']
    sld=math.hypot(nx-gx,ny-gy)*(20.0/MAP_W)
    a,b,g=WEIGHT_PROFILES[mode]
    mr=compute_risk(min(e[3] for e in EDGES_RAW),gender,group,tod,rp)
    return a*sld/3.5 + b*sld*4.0/14.0 + g*mr/14.0

# ─── ALGORITHMS (identical) ─────────────────────────────────────────────────
def _t(graph,path):
    d=sum(graph[path[i]][path[i+1]]['dist'] for i in range(len(path)-1))
    r=sum(graph[path[i]][path[i+1]]['risk'] for i in range(len(path)-1))
    return d,r

def bfs(graph,start,goal):
    q=deque([(start,[start])]); vis={start}; exp=[]; ne=0
    while q:
        n,p=q.popleft(); exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb in graph[n]:
            if nb not in vis: vis.add(nb); q.append((nb,p+[nb]))
    return None,ne,exp,0,0

def dfs(graph,start,goal):
    st=[(start,[start])]; vis=set(); exp=[]; ne=0
    while st:
        n,p=st.pop()
        if n in vis: continue
        vis.add(n); exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb in reversed(list(graph[n])):
            if nb not in vis: st.append((nb,p+[nb]))
    return None,ne,exp,0,0

def ucs(graph,start,goal):
    h=[(0,start,[start])]; csf={start:0}; exp=[]; ne=0
    while h:
        c,n,p=heapq.heappop(h)
        if n in exp: continue
        exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb,d in graph[n].items():
            nc=c+d['cost']
            if nb not in csf or nc<csf[nb]:
                csf[nb]=nc; heapq.heappush(h,(nc,nb,p+[nb]))
    return None,ne,exp,0,0

def dls(graph,start,goal,lim=8):
    exp=[]; ne=[0]
    def rec(n,p,d):
        exp.append(n); ne[0]+=1
        if n==goal: return p
        if d==0: return None
        for nb in graph[n]:
            if nb not in p:
                r=rec(nb,p+[nb],d-1)
                if r: return r
        return None
    p=rec(start,[start],lim)
    if p: return p,ne[0],exp,*_t(graph,p)
    return None,ne[0],exp,0,0

def ids(graph,start,goal,mx=15):
    ae=[]; tot=0
    for depth in range(mx+1):
        te=[]; nn=[0]
        def rec(n,p,d):
            te.append(n); nn[0]+=1
            if n==goal: return p
            if d==0: return None
            for nb in graph[n]:
                if nb not in p:
                    r=rec(nb,p+[nb],d-1)
                    if r: return r
            return None
        p=rec(start,[start],depth); tot+=nn[0]; ae.extend(te)
        if p: return p,tot,ae,*_t(graph,p)
    return None,tot,ae,0,0

def astar(graph,start,goal,gender,group,tod,mode,rp):
    h0=heuristic(start,goal,gender,group,tod,mode,rp)
    fr=[(h0,0,start,[start])]; csf={start:0}; exp=[]; ne=0
    while fr:
        f,g,n,p=heapq.heappop(fr)
        if n in exp: continue
        exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb,d in graph[n].items():
            ng=g+d['cost']
            if nb not in csf or ng<csf[nb]:
                csf[nb]=ng; h=heuristic(nb,goal,gender,group,tod,mode,rp)
                heapq.heappush(fr,(ng+h,ng,nb,p+[nb]))
    return None,ne,exp,0,0

def wastar(graph,start,goal,gender,group,tod,mode,rp,W=2.5):
    h0=heuristic(start,goal,gender,group,tod,mode,rp)
    fr=[(W*h0,0,start,[start])]; csf={start:0}; exp=[]; ne=0
    while fr:
        f,g,n,p=heapq.heappop(fr)
        if n in exp: continue
        exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb,d in graph[n].items():
            ng=g+d['cost']
            if nb not in csf or ng<csf[nb]:
                csf[nb]=ng; h=heuristic(nb,goal,gender,group,tod,mode,rp)
                heapq.heappush(fr,(ng+W*h,ng,nb,p+[nb]))
    return None,ne,exp,0,0

def greedy(graph,start,goal,gender,group,tod,mode,rp):
    fr=[(heuristic(start,goal,gender,group,tod,mode,rp),start,[start])]
    vis=set(); exp=[]; ne=0
    while fr:
        h,n,p=heapq.heappop(fr)
        if n in vis: continue
        vis.add(n); exp.append(n); ne+=1
        if n==goal: return p,ne,exp,*_t(graph,p)
        for nb in graph[n]:
            if nb not in vis:
                heapq.heappush(fr,(heuristic(nb,goal,gender,group,tod,mode,rp),nb,p+[nb]))
    return None,ne,exp,0,0

def run_all(start,goal,gender,group,tod,mode,rp):
    graph,emap=build_graph(gender,group,tod,mode,rp); res={}
    algos={'BFS':lambda:bfs(graph,start,goal),
           'DFS':lambda:dfs(graph,start,goal),
           'UCS':lambda:ucs(graph,start,goal),
           'DLS':lambda:dls(graph,start,goal),
           'IDS':lambda:ids(graph,start,goal),
           'A*': lambda:astar(graph,start,goal,gender,group,tod,mode,rp),
           'W-A*':lambda:wastar(graph,start,goal,gender,group,tod,mode,rp),
           'Greedy':lambda:greedy(graph,start,goal,gender,group,tod,mode,rp)}
    for name,fn in algos.items():
        t0=time.perf_counter()
        p,ne,eo,td,tr=fn(); el=(time.perf_counter()-t0)*1000
        tc=sum(graph[p[i]][p[i+1]]['cost'] for i in range(len(p)-1)) if p else 0
        res[name]={'path':p,'nodes_explored':ne,'explored_order':eo,
                   'total_dist':round(td,2),'total_risk':round(tr,3),
                   'total_cost':round(tc,3),'path_len':len(p) if p else 0,
                   'time_ms':round(el,4),'found':p is not None}
    return res,graph,emap

# ─── INPUT BOX (unchanged) ──────────────────────────────────────────────────
class InputBox:
    def __init__(self,label,key,default,min_v,max_v,desc):
        self.label=label; self.key=key; self.text=str(default)
        self.default=default; self.min_v=min_v; self.max_v=max_v
        self.desc=desc; self.active=False; self.err=False
        self.rect=pygame.Rect(0,0,95,26)

    def get(self):
        try:
            v=float(self.text); self.err=not(self.min_v<=v<=self.max_v)
            return max(self.min_v,min(self.max_v,v))
        except: self.err=True; return self.default

    def event(self,ev):
        if ev.type==pygame.MOUSEBUTTONDOWN: self.active=self.rect.collidepoint(ev.pos)
        if ev.type==pygame.KEYDOWN and self.active:
            if ev.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif ev.key in(pygame.K_RETURN,pygame.K_ESCAPE,pygame.K_TAB): self.active=False
            elif ev.unicode in'0123456789.' and not(ev.unicode=='.' and '.' in self.text) and len(self.text)<7:
                self.text+=ev.unicode

    def draw(self,screen,x,y,fsm):
        self.rect.x,self.rect.y=x,y
        bc=DANGER if self.err else(ACCENT if self.active else PANEL_BORDER)
        bg=(35,42,62) if self.active else DGRAY
        pygame.draw.rect(screen,bg,self.rect,border_radius=5)
        pygame.draw.rect(screen,bc,self.rect,1,border_radius=5)
        t=fsm.render(self.text,True,WHITE if self.active else LGRAY)
        screen.blit(t,(x+5,y+4))

# ─── APP with scaled fonts and layout ───────────────────────────────────────
TABS=['⚙ Controls','⚡ Risk Tuning','📊 Comparison']
ALGO_COLS={'BFS':(55,132,198),'DFS':(175,72,72),'UCS':(55,175,112),
           'DLS':(175,135,45),'IDS':(95,155,198),'A*':(152,72,215),
           'W-A*':(198,55,175),'Greedy':(215,115,45)}
OPTIMAL={'UCS','A*','BFS','IDS'}

class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((ORIG_W, ORIG_H))
        pygame.display.set_caption('AI Lab — Safety-Aware Urban Route Planner')
        self.clock = pygame.time.Clock()
        # Scaled font sizes
        self.ft = pygame.font.SysFont('Segoe UI', 20, bold=True)
        self.flg = pygame.font.SysFont('Segoe UI', 14, bold=True)
        self.fmd = pygame.font.SysFont('Segoe UI', 11)
        self.fsm = pygame.font.SysFont('Segoe UI', 10)
        self.fxs = pygame.font.SysFont('Segoe UI', 9)
        self.fnd = pygame.font.SysFont('Segoe UI', 9, bold=True)
        self.ftb = pygame.font.SysFont('Segoe UI', 10, bold=True)

        self.start_node=None; self.end_node=None; self.hover_node=None
        self.gender='female'; self.group='solo'; self.tod='night'; self.mode='safe'
        self.algorithm='A*'; self.active_tab=0
        self.results=None; self.graph=None; self.emap=None; self.sel='A*'
        self.status='Click two nodes on the map to set Start → End'
        self.scol=LGRAY
        self.animating=False; self.astep=0; self.atimer=0
        self.cscroll=0

        self.boxes=[
            InputBox('Female coeff','female_coef',3.5,0.1,15.0,
                     'Scales female risk penalty. Higher = stronger avoidance on dangerous roads.'),
            InputBox('Female exp','female_exp',1.5,0.5,4.0,
                     'Exponent >1 makes female penalty grow faster than danger itself (quadratic).'),
            InputBox('Male coeff','male_coef',0.8,0.0,10.0,
                     'Linear risk coefficient for male traveler.'),
            InputBox('Night mult','night_mult',2.8,1.0,10.0,
                     'Multiplies ALL edge risks at night. 2.8 = nearly 3x more dangerous.'),
            InputBox('Evening mult','evening_mult',1.6,1.0,5.0,
                     'Evening risk multiplier (between day=1.0 and night value).'),
            InputBox('Group factor','group_factor',0.5,0.05,1.0,
                     'Group risk = solo risk × this. 0.5 = group is twice as safe.'),
        ]
        self._reset_btn=pygame.Rect(0,0,1,1)
        self.btns={}
        self._build_btns()

    def _build_btns(self):
        px = RP_X + 8
        b = self.btns
        tw = (RP_W - 12) // 3
        for i in range(3):
            b[f'tab_{i}'] = pygame.Rect(px + i*tw, 10, tw-4, 28)
        hw = (RP_W - 20) // 2 - 3
        b['gender_female'] = pygame.Rect(px, 106, hw, 30)
        b['gender_male']   = pygame.Rect(px + hw + 6, 106, hw, 30)
        b['group_solo']    = pygame.Rect(px, 172, hw, 30)
        b['group_group']   = pygame.Rect(px + hw + 6, 172, hw, 30)
        tw3 = (RP_W - 20) // 3 - 3
        b['time_day']      = pygame.Rect(px, 238, tw3, 30)
        b['time_evening']  = pygame.Rect(px + tw3 + 5, 238, tw3, 30)
        b['time_night']    = pygame.Rect(px + 2*tw3 + 10, 238, tw3, 30)
        b['mode_safe']     = pygame.Rect(px, 304, hw, 30)
        b['mode_risky']    = pygame.Rect(px + hw + 6, 304, hw, 30)
        aw = (RP_W - 20) // 4 - 3
        for i, alg in enumerate(['BFS','DFS','UCS','DLS','IDS','A*','W-A*','Greedy']):
            r, c = divmod(i, 4)
            b[f'algo_{alg}'] = pygame.Rect(px + c*(aw+4), 386 + r*38, aw, 30)
        b['run']    = pygame.Rect(px, 472, RP_W-16, 40)
        b['reset']  = pygame.Rect(px, 520, hw, 28)
        b['compare'] = pygame.Rect(px + hw + 6, 520, hw, 28)

    def _mp(self, n):
        x, y = NODES[n]['pos']
        return MAP_X + x, MAP_Y + y

    def _nat(self, mx, my):
        for n in NODES:
            nx, ny = self._mp(n)
            if math.hypot(mx - nx, my - ny) < 12:  # slightly smaller hit radius
                return n
        return None

    def _rc(self, br):
        return (int(48+br*185), int(178-br*155), 55)

    def _get_rp(self):
        return {ib.key: ib.get() for ib in self.boxes}

    # ── DRAW methods (identical logic, only rendering to self.screen) ────────
    def _hdr(self):
        pygame.draw.rect(self.screen, (14,17,28), (0,0,ORIG_W,108))
        pygame.draw.line(self.screen, PANEL_BORDER, (0,108), (ORIG_W,108), 1)
        self.screen.blit(self.ft.render('AI Lab — Safety-Aware Urban Route Planner', True, WHITE), (14,10))
        sub = ('Cost(A,B)=α·dist_norm+β·time_norm+γ·risk_norm  |  '
               'Risk=base×gender_mult×group_mult×time_mult  |  '
               'h(n)=α·SLD+γ·min_risk [Admissible Heuristic]')
        self.screen.blit(self.fxs.render(sub, True, GRAY), (14,44))
        pygame.draw.rect(self.screen, CARD, (14,62, MAP_W-4, 36), border_radius=6)
        self.screen.blit(self.fsm.render(self.status, True, self.scol), (22,73))

    def _map(self):
        pygame.draw.rect(self.screen, (16,20,32), (MAP_X, MAP_Y, MAP_W, MAP_H), border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, (MAP_X, MAP_Y, MAP_W, MAP_H), 1, border_radius=10)
        for gx in range(MAP_X, MAP_X+MAP_W, 60):
            pygame.draw.line(self.screen, (22,28,42), (gx, MAP_Y), (gx, MAP_Y+MAP_H))
        for gy in range(MAP_Y, MAP_Y+MAP_H, 60):
            pygame.draw.line(self.screen, (22,28,42), (MAP_X, gy), (MAP_X+MAP_W, gy))
        self._edges(); self._nodes()

    def _edges(self):
        ps = set(); es = set()
        if self.results and self.sel in self.results and self.results[self.sel]['found']:
            p = self.results[self.sel]['path']
            ps = set(zip(p,p[1:])) | set(zip(p[1:],p))
        if self.results and self.sel in self.results:
            eo = self.results[self.sel]['explored_order']
            if self.animating:
                eo = eo[:self.astep]
            es = set(eo)
        for n1,n2,dist,br in EDGES_RAW:
            p1, p2 = self._mp(n1), self._mp(n2)
            if (n1,n2) in ps:
                pygame.draw.line(self.screen, EDGE_PATH, p1, p2, 5)
                mx2, my2 = (p1[0]+p2[0])//2, (p1[1]+p2[1])//2
                self.screen.blit(self.fxs.render(f'{dist}km', True, (210,175,60)), (mx2-14, my2-7))
            elif n1 in es and n2 in es:
                pygame.draw.line(self.screen, (72,44,115), p1, p2, 2)
            else:
                pygame.draw.line(self.screen, self._rc(br), p1, p2, 2)

    def _nodes(self):
        ps = set(); es = set()
        if self.results and self.sel in self.results and self.results[self.sel]['found']:
            ps = set(self.results[self.sel]['path'])
        if self.results and self.sel in self.results:
            eo = self.results[self.sel]['explored_order']
            if self.animating:
                eo = eo[:self.astep]
            es = set(eo)
        for name, data in NODES.items():
            nx, ny = self._mp(name)
            if name == self.start_node:
                col, ring, r = NODE_START, (100,255,150), 13
            elif name == self.end_node:
                col, ring, r = NODE_END, (255,110,95), 13
            elif name in ps:
                col, ring, r = NODE_PATH, (255,220,70), 12
            elif name in es:
                col, ring, r = NODE_EXPLORED, (168,80,212), 11
            elif name == self.hover_node:
                col, ring, r = NODE_HOVER, ACCENT, 12
            else:
                col, ring, r = NODE_DEFAULT, None, 10
            if ring:
                pygame.draw.circle(self.screen, ring, (nx, ny), r+3, 2)
            if name in ps or name in (self.start_node, self.end_node):
                gs = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*col, 38), (r*2, r*2), r*2)
                self.screen.blit(gs, (nx - r*2, ny - r*2))
            pygame.draw.circle(self.screen, col, (nx, ny), r)
            pygame.draw.circle(self.screen, (195,215,250), (nx, ny), r, 1)
            lb = self.fnd.render(name, True, NODE_TEXT)
            self.screen.blit(lb, (nx - lb.get_width()//2, ny - lb.get_height()//2))
            nl = self.fxs.render(data['name'], True, (155,170,195))
            nlx = min(max(nx - nl.get_width()//2, MAP_X+2), MAP_X+MAP_W - nl.get_width() - 2)
            nly = ny + r + 3
            if nly + nl.get_height() < MAP_Y + MAP_H - 2:
                pygame.draw.rect(self.screen, (10,13,24), (nlx-2, nly-1, nl.get_width()+4, nl.get_height()+1), border_radius=2)
                self.screen.blit(nl, (nlx, nly))
            if name == self.hover_node:
                tip = self.fsm.render(data['name'], True, WHITE)
                tx = min(max(nx - tip.get_width()//2, MAP_X+5), MAP_X+MAP_W - tip.get_width() - 5)
                ty = ny - r - 18
                pygame.draw.rect(self.screen, (28,34,52), (tx-4, ty-2, tip.get_width()+8, tip.get_height()+4), border_radius=4)
                self.screen.blit(tip, (tx, ty))

    def _bottom(self):
        by = MAP_Y + MAP_H + 8
        bh = ORIG_H - by - 4
        pygame.draw.rect(self.screen, PANEL_BG, (MAP_X, by, MAP_W, bh), border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, (MAP_X, by, MAP_W, bh), 1, border_radius=8)
        x = MAP_X + 10
        y = by + 6
        if not self.results:
            self.screen.blit(self.fxs.render('LEGEND:', True, GRAY), (x, y)); y += 14
            items = [(NODE_START,'Start'), (NODE_END,'End'), (NODE_PATH,'On Path'),
                     (NODE_EXPLORED,'Explored'), ((55,155,55),'Low-risk edge'), ((195,55,55),'High-risk edge')]
            lx = x
            for col, lbl in items:
                pygame.draw.circle(self.screen, col, (lx+6, y+6), 6)
                self.screen.blit(self.fxs.render(lbl, True, LGRAY), (lx+16, y))
                lx += 145
            return
        r = self.results[self.sel]
        if not r['found']:
            self.screen.blit(self.fsm.render(f'{self.sel}: No path found.', True, DANGER), (x, y))
            return
        ac = ALGO_COLS.get(self.sel, ACCENT)
        self.screen.blit(self.fsm.render(f'[{self.sel}]', True, ac), (x, y))
        self.screen.blit(self.fsm.render('  ' + '→'.join(r['path']), True, NODE_PATH), (x+50, y)); y += 16
        DESCS = {
            'BFS':'BFS: explores level-by-level (FIFO queue). Finds minimum-hop path. Ignores edge cost/risk entirely.',
            'DFS':'DFS: dives deep via LIFO stack. Finds any path quickly. NOT cost-optimal.',
            'UCS':'UCS/Dijkstra: always expands lowest accumulated cost. OPTIMAL but slow—no heuristic guidance.',
            'DLS':'DLS: DFS with depth limit=8. Fast but incomplete if goal >8 hops away.',
            'IDS':'IDS: repeats DLS at increasing depths. Optimal like BFS, memory-efficient like DFS.',
            'A*': 'A*: f=g+h. g=actual cost so far, h=admissible heuristic. OPTIMAL + efficient (fewest nodes).',
            'W-A*':'W-A* (W=2.5): f=g+2.5h. More greedy than A*—faster, near-optimal (within 2.5× optimal).',
            'Greedy':'Greedy: only h(n), ignores g(n). Fastest but suboptimal—may miss safer detours.'
        }
        self.screen.blit(self.fxs.render(DESCS.get(self.sel,''), True, LGRAY), (x, y)); y += 13
        stats = [f'Explored:{r["nodes_explored"]}', f'Hops:{r["path_len"]}',
                 f'Dist:{r["total_dist"]}km', f'Risk:{r["total_risk"]:.3f}',
                 f'Cost:{r["total_cost"]:.3f}', f'Time:{r["time_ms"]:.4f}ms']
        sx = x
        for s in stats:
            self.screen.blit(self.fxs.render(s, True, LGRAY), (sx, y)); sx += 145

    def _rpanel(self):
        pygame.draw.rect(self.screen, PANEL_BG, (RP_X, 0, ORIG_W-RP_X, ORIG_H))
        pygame.draw.line(self.screen, PANEL_BORDER, (RP_X, 0), (RP_X, ORIG_H), 1)
        px = RP_X + 8
        tw = (RP_W - 12) // 3
        for i, lbl in enumerate(TABS):
            btn = self.btns[f'tab_{i}']; active = (self.active_tab == i)
            pygame.draw.rect(self.screen, (ACCENT if active else DGRAY), btn, border_radius=7)
            if active:
                pygame.draw.rect(self.screen, ACCENT, btn, 2, border_radius=7)
            t = self.ftb.render(lbl, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+7))
        pygame.draw.line(self.screen, PANEL_BORDER, (RP_X, 44), (ORIG_W, 44), 1)
        if self.active_tab == 0:
            self._tab0(px)
        elif self.active_tab == 1:
            self._tab1(px)
        else:
            self._tab2(px)

    def _tab0(self, px):
        y = 52
        pygame.draw.rect(self.screen, CARD, (px, y, RP_W-16, 44), border_radius=7)
        s = f'▶ {self.start_node} — {NODES[self.start_node]["name"]}' if self.start_node else '▶ Start: click a map node'
        e = f'◼ {self.end_node} — {NODES[self.end_node]["name"]}' if self.end_node else '◼ End:   click a map node'
        self.screen.blit(self.fsm.render(s, True, NODE_START if self.start_node else GRAY), (px+8, y+6))
        self.screen.blit(self.fsm.render(e, True, NODE_END if self.end_node else GRAY), (px+8, y+24))
        y += 52
        def sec(lbl, yy):
            self.screen.blit(self.fxs.render(lbl, True, GRAY), (px, yy))
        sec('TRAVELER GENDER', y)
        for key, lbl in [('female','♀ Female'), ('male','♂ Male')]:
            btn = self.btns[f'gender_{key}']; active = (self.gender == key)
            pygame.draw.rect(self.screen, (ACCENT if active else DGRAY), btn, border_radius=7)
            if active:
                pygame.draw.rect(self.screen, ACCENT, btn, 2, border_radius=7)
            t = self.fsm.render(lbl, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+8))
        y += 46
        sec('JOURNEY TYPE', y)
        for key, lbl in [('solo','👤 Solo'), ('group','👥 Group')]:
            btn = self.btns[f'group_{key}']; active = (self.group == key)
            pygame.draw.rect(self.screen, (ACCENT2 if active else DGRAY), btn, border_radius=7)
            if active:
                pygame.draw.rect(self.screen, ACCENT2, btn, 2, border_radius=7)
            t = self.fsm.render(lbl, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+8))
        y += 46
        sec('TIME OF DAY', y)
        for key, lbl, ac in [('day','☀ Day',WARNING), ('evening','🌆 Evening',ORANGE), ('night','🌙 Night',PURPLE)]:
            btn = self.btns[f'time_{key}']; active = (self.tod == key)
            pygame.draw.rect(self.screen, (ac if active else DGRAY), btn, border_radius=7)
            if active:
                pygame.draw.rect(self.screen, ac, btn, 2, border_radius=7)
            t = self.fsm.render(lbl, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+8))
        y += 46
        sec('ROUTE PRIORITY', y)
        for key, lbl, ac in [('safe','🛡 SAFE — avoid risk',SUCCESS), ('risky','⚡ RISKY — shortest',DANGER)]:
            btn = self.btns[f'mode_{key}']; active = (self.mode == key)
            pygame.draw.rect(self.screen, (ac if active else DGRAY), btn, border_radius=7)
            if active:
                pygame.draw.rect(self.screen, ac, btn, 2, border_radius=7)
            t = self.fxs.render(lbl, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+10))
        a,b_,g = WEIGHT_PROFILES[self.mode]
        self.screen.blit(self.fxs.render(f'  α={a}  β={b_}  γ={g}  (dist/time/risk weights)', True, ACCENT), (px, y+36))
        y += 52
        sec('SEARCH ALGORITHM', y); y += 15
        for alg in ['BFS','DFS','UCS','DLS','IDS','A*','W-A*','Greedy']:
            btn = self.btns[f'algo_{alg}']; active = (self.algorithm == alg)
            ac = ALGO_COLS.get(alg, ACCENT)
            pygame.draw.rect(self.screen, (ac if active else DGRAY), btn, border_radius=6)
            if active:
                pygame.draw.rect(self.screen, ac, btn, 2, border_radius=6)
            t = self.fsm.render(alg, True, WHITE if active else GRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+8))
        y += 80
        run = self.btns['run']
        pygame.draw.rect(self.screen, SUCCESS, run, border_radius=9)
        pygame.draw.rect(self.screen, (95,250,140), run, 2, border_radius=9)
        rt = self.fmd.render('▶  RUN SEARCH', True, (8,18,12))
        self.screen.blit(rt, (run.x + run.w//2 - rt.get_width()//2, run.y+11))
        for key, lbl in [('reset','↺ Reset'), ('compare','📊 Compare')]:
            btn = self.btns[key]
            pygame.draw.rect(self.screen, DGRAY, btn, border_radius=7)
            pygame.draw.rect(self.screen, PANEL_BORDER, btn, 1, border_radius=7)
            t = self.fsm.render(lbl, True, LGRAY)
            self.screen.blit(t, (btn.x + btn.w//2 - t.get_width()//2, btn.y+7))
        if self.results and self.sel in self.results:
            self._detail(px, 560)

    def _tab1(self, px):
        y = 52
        pygame.draw.rect(self.screen, CARD, (px, y, RP_W-16, 42), border_radius=7)
        self.screen.blit(self.flg.render('Dynamic Risk Parameter Tuning', True, WHITE), (px+10, y+5))
        self.screen.blit(self.fxs.render('Click a field → type value → Enter. All multipliers take effect on next RUN.', True, GRAY), (px+10, y+25))
        y += 50
        self._reset_btn = pygame.Rect(px, y, RP_W-16, 26)
        pygame.draw.rect(self.screen, DGRAY, self._reset_btn, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, self._reset_btn, 1, border_radius=6)
        rt = self.fxs.render('↺  Reset all to defaults', True, LGRAY)
        self.screen.blit(rt, (self._reset_btn.x + self._reset_btn.w//2 - rt.get_width()//2, self._reset_btn.y+6))
        y += 34
        cw = (RP_W - 24) // 2
        for i, ib in enumerate(self.boxes):
            row, col = divmod(i, 2)
            bx = px + col*(cw+8); by = y + row*100
            pygame.draw.rect(self.screen, CARD, (bx, by, cw, 94), border_radius=7)
            self.screen.blit(self.fsm.render(ib.label, True, WHITE), (bx+6, by+6))
            ib.draw(self.screen, bx+6, by+26, self.fsm)
            cv = ib.get()
            vcol = ACCENT2 if not ib.err else DANGER
            self.screen.blit(self.fxs.render(f'= {cv:.3f}', True, vcol), (bx+106, by+30))
            words = ib.desc.split(); line = ''; dy = by+54
            for w in words:
                test = line + (' ' if line else '') + w
                if self.fxs.size(test)[0] <= cw-12:
                    line = test
                else:
                    self.screen.blit(self.fxs.render(line, True, GRAY), (bx+6, dy)); dy += 13; line = w
            if line:
                self.screen.blit(self.fxs.render(line, True, GRAY), (bx+6, dy))
        y += 3*100 + 10
        pygame.draw.rect(self.screen, CARD, (px, y, RP_W-16, 130), border_radius=7)
        self.screen.blit(self.fsm.render('Live Risk Preview — Slum Area edge (base_risk = 0.55)', True, ACCENT), (px+8, y+6))
        rp = self._get_rp()
        combos = [('female','solo','night','F/solo/night'),
                  ('female','solo','day',  'F/solo/day'),
                  ('male',  'solo','night','M/solo/night'),
                  ('male',  'group','day', 'M/group/day')]
        for j, (g, gr, t, lbl) in enumerate(combos):
            rv = compute_risk(0.55, g, gr, t, rp)
            bw = min(int(rv/9.0 * (RP_W-80)), RP_W-80)
            by2 = y + 26 + j*24
            pygame.draw.rect(self.screen, DGRAY, (px+8, by2+4, RP_W-32, 14), border_radius=3)
            bc = (215,68,72) if rv>3 else ((252,165,42) if rv>1 else SUCCESS)
            if bw>0:
                pygame.draw.rect(self.screen, bc, (px+8, by2+4, bw, 14), border_radius=3)
            self.screen.blit(self.fxs.render(f'{lbl}: {rv:.3f}', True, WHITE), (px+8, by2+5))

    def _tab2(self, px):
        y = 52
        if not self.results:
            pygame.draw.rect(self.screen, CARD, (px, y, RP_W-16, 52), border_radius=7)
            self.screen.blit(self.fmd.render('Run a search first.', True, GRAY), (px+12, y+8))
            self.screen.blit(self.fxs.render('Results appear here after clicking RUN in the Controls tab.', True, GRAY), (px+12, y+28))
            return
        prof = f'{self.gender.upper()} | {self.group.upper()} | {self.tod.upper()} | {self.mode.upper()}'
        pygame.draw.rect(self.screen, CARD, (px, y, RP_W-16, 34), border_radius=7)
        self.screen.blit(self.fsm.render('Profile: '+prof, True, WHITE), (px+8, y+10)); y += 42
        COLS = [('Algorithm',90), ('Found',48), ('Nodes',52), ('Hops',42),
                ('Dist km',60), ('Risk',54), ('Cost',58), ('ms',62), ('Optimal',58)]
        total_cw = sum(c[1] for c in COLS)
        pygame.draw.rect(self.screen, DGRAY, (px, y, RP_W-16, 20), border_radius=4)
        hx = px+2
        for hdr, cw in COLS:
            self.screen.blit(self.fxs.render(hdr, True, ACCENT), (hx, y+4)); hx += cw
        y += 22
        panel_h = ORIG_H - y - 36
        clip = pygame.Rect(px, y, RP_W-16, panel_h)
        self.screen.set_clip(clip)
        ry = y - self.cscroll
        for algo, r in self.results.items():
            ac = ALGO_COLS.get(algo, WHITE)
            bg = CARD2 if algo == self.sel else CARD
            pygame.draw.rect(self.screen, bg, (px, ry, RP_W-16, 22), border_radius=3)
            if algo == self.sel:
                pygame.draw.rect(self.screen, ac, (px, ry, RP_W-16, 22), 1, border_radius=3)
            row = [(algo, ac),
                   ('✓' if r['found'] else '✗', SUCCESS if r['found'] else DANGER),
                   (str(r['nodes_explored']), LGRAY), (str(r['path_len']), LGRAY),
                   (str(r['total_dist']), ACCENT2),
                   (f"{r['total_risk']:.2f}", WARNING if r['total_risk']>2 else SUCCESS),
                   (f"{r['total_cost']:.3f}", LGRAY), (f"{r['time_ms']:.3f}", GRAY),
                   ('✓ Yes' if algo in OPTIMAL else '✗ No', SUCCESS if algo in OPTIMAL else WARNING)]
            hx = px+2
            for (txt, col), (_, cw) in zip(row, COLS):
                self.screen.blit(self.fxs.render(str(txt), True, col), (hx, ry+5)); hx += cw
            ry += 24
        ry += 4
        for note in ['* Optimal = guaranteed lowest cost  |  A* = optimal + fewest nodes explored',
                     '* W-A* (W=2.5) = near-optimal, fastest  |  BFS/IDS = fewest hops']:
            self.screen.blit(self.fxs.render(note, True, GRAY), (px, ry)); ry += 14
        self.screen.set_clip(None)
        if ry - y + self.cscroll > panel_h:
            self.screen.blit(self.fxs.render('↑↓ scroll with mousewheel', True, GRAY), (px, ORIG_H-18))

    def _detail(self, px, y):
        r = self.results[self.sel]
        if not r['found']:
            self.screen.blit(self.fsm.render('No path found.', True, DANGER), (px, y)); return
        clip = pygame.Rect(px, y, RP_W-16, ORIG_H-y-4)
        self.screen.set_clip(clip)
        ac = ALGO_COLS.get(self.sel, ACCENT)
        self.screen.blit(self.fsm.render(f'[{self.sel}] Path: '+'→'.join(r["path"]), True, NODE_PATH), (px, y)); y += 16
        stats = [(f'Nodes:{r["nodes_explored"]}', PURPLE), (f'Hops:{r["path_len"]}', ACCENT),
                 (f'Dist:{r["total_dist"]}km', ACCENT2),
                 (f'Risk:{r["total_risk"]:.3f}', WARNING if r['total_risk']>2 else SUCCESS),
                 (f'Cost:{r["total_cost"]:.3f}', WHITE), (f'Time:{r["time_ms"]:.4f}ms', GRAY)]
        sx = px
        for s, col in stats:
            self.screen.blit(self.fxs.render(s, True, col), (sx, y)); sx += 108
            if sx > px+RP_W-80:
                sx = px; y += 14
        y += 16
        if self.graph:
            self.screen.blit(self.fxs.render('── Per-edge risk breakdown ──', True, ACCENT), (px, y)); y += 13
            for i in range(len(r['path'])-1):
                n1, n2 = r['path'][i], r['path'][i+1]
                e = self.graph[n1][n2]
                lv = '⚠HIGH' if e['risk']>2 else ('△MED' if e['risk']>0.8 else '✓LOW')
                col = DANGER if e['risk']>2 else (WARNING if e['risk']>0.8 else SUCCESS)
                ln = (f"  {n1}→{n2}  dist={e['dist']}km  base={e['base_risk']:.2f}"
                      f"  risk={e['risk']:.3f} {lv}  cost={e['cost']:.4f}")
                self.screen.blit(self.fxs.render(ln, True, col), (px, y)); y += 13
                if y > ORIG_H-14: break
        self.screen.set_clip(None)

    # ── Events ──────────────────────────────────────────────────────────────
    def _click(self, mx, my):
        if MAP_X <= mx <= MAP_X+MAP_W and MAP_Y <= my <= MAP_Y+MAP_H:
            nd = self._nat(mx, my)
            if nd:
                if not self.start_node:
                    self.start_node = nd
                    self.status = f'Start: {nd} ({NODES[nd]["name"]}). Now click End.'
                    self.scol = NODE_START
                elif not self.end_node and nd != self.start_node:
                    self.end_node = nd
                    self.status = f'End: {nd} ({NODES[nd]["name"]}). Set options → RUN.'
                    self.scol = NODE_END
                else:
                    self.start_node = nd
                    self.end_node = None
                    self.results = None
                    self.status = f'Start reset to {nd}.'
                    self.scol = NODE_START
            return
        for i in range(3):
            if self.btns[f'tab_{i}'].collidepoint(mx, my):
                self.active_tab = i
                return
        if self.active_tab == 1 and self._reset_btn.collidepoint(mx, my):
            for ib in self.boxes:
                ib.text = str(DEFAULT_RP[ib.key])
                ib.err = False
            return
        for k, rect in self.btns.items():
            if rect.collidepoint(mx, my):
                self._btn(k)
                return

    def _btn(self, k):
        if k.startswith('gender_'):
            self.gender = k[7:]
        elif k.startswith('group_'):
            self.group = k[6:]
        elif k.startswith('time_'):
            self.tod = k[5:]
        elif k.startswith('mode_'):
            self.mode = k[5:]
        elif k.startswith('algo_'):
            self.algorithm = k[5:]
            self.sel = k[5:]
        elif k == 'run':
            self._run()
        elif k == 'reset':
            self._reset()
        elif k == 'compare':
            self.active_tab = 2

    def _run(self):
        if not self.start_node or not self.end_node:
            self.status = 'Select both Start and End nodes first!'
            self.scol = DANGER
            return
        self.sel = self.algorithm
        rp = self._get_rp()
        self.results, self.graph, self.emap = run_all(
            self.start_node, self.end_node, self.gender, self.group, self.tod, self.mode, rp)
        r = self.results[self.algorithm]
        if r['found']:
            self.status = (f'{self.algorithm}: {r["path_len"]} hops | {r["total_dist"]}km | '
                           f'Risk:{r["total_risk"]:.3f} | Nodes explored:{r["nodes_explored"]}')
            self.scol = SUCCESS
        else:
            self.status = f'{self.algorithm}: No path found!'
            self.scol = DANGER
        self.animating = True
        self.astep = 0
        self.atimer = 0

    def _reset(self):
        self.start_node = self.end_node = self.results = self.graph = self.emap = None
        self.animating = False
        self.astep = 0
        self.cscroll = 0
        self.status = 'Reset. Click two nodes on the map.'
        self.scol = LGRAY

    def _anim(self, dt):
        if not self.animating:
            return
        self.atimer += dt
        if self.atimer > 70:
            self.atimer = 0
            if self.results and self.sel in self.results:
                mx = len(self.results[self.sel]['explored_order'])
                if self.astep < mx:
                    self.astep += 1
                else:
                    self.animating = False

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            mx, my = pygame.mouse.get_pos()
            self.hover_node = self._nat(mx, my) if (MAP_X <= mx <= MAP_X+MAP_W and MAP_Y <= my <= MAP_Y+MAP_H) else None
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.active_tab == 1:
                    for ib in self.boxes:
                        ib.event(ev)
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self._click(mx, my)
                if ev.type == pygame.KEYDOWN:
                    if self.active_tab != 1:
                        if ev.key == pygame.K_r:
                            self._reset()
                        elif ev.key == pygame.K_RETURN:
                            self._run()
                if ev.type == pygame.MOUSEWHEEL:
                    if mx > RP_X and self.active_tab == 2:
                        self.cscroll = max(0, min(self.cscroll - ev.y*20, 500))
            self._anim(dt)
            self.screen.fill(BG)
            self._hdr()
            self._map()
            self._rpanel()
            self._bottom()
            pygame.display.flip()

if __name__ == '__main__':
    App().run()