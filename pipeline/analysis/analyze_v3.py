import pickle, sys, itertools, json, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *
eps = pickle.load(open('eps_v2.pkl', 'rb'))
E = pd.read_pickle('E_v2.pkl'); T = pd.read_pickle('T_v2.pkl')
p = P()
R = {}
# ---------------- 5번: 차수별 기간
T = T.sort_values(['eid', 'order']).reset_index(drop=True)
T['prev_break'] = T.groupby('eid').break_idx.shift()
T['decl_days'] = np.where(T.order == 1, T.days_from_peak, T.idx - T.prev_break)
T['next_idx'] = T.groupby('eid').idx.shift(-1)
T['to_next'] = T.next_idx - T.idx
T['o'] = T.order.clip(upper=7)
def q(s, a): return float(np.nanpercentile(s, a)) if len(s.dropna()) else np.nan
rows = []
for o, g in T.groupby('o'):
    b = g[g.broken == True]
    rows.append(dict(o=int(o), n=len(g), n_leg=len(b),
        decl_med=q(g.decl_days, 50), decl_p25=q(g.decl_days, 25), decl_p75=q(g.decl_days, 75),
        up_med=q(b.leg_days, 50), up_p25=q(b.leg_days, 25), up_p75=q(b.leg_days, 75),
        brk_med=q(b.days_to_break, 50), brk_p25=q(b.days_to_break, 25), brk_p75=q(b.days_to_break, 75),
        cyc_med=q(g.to_next, 50), cyc_p25=q(g.to_next, 25), cyc_p75=q(g.to_next, 75),
        leg_med=q(b.leg_ret * 100, 50), leg_p25=q(b.leg_ret * 100, 25), leg_p75=q(b.leg_ret * 100, 75),
        dep_med=q(g.depth_vs_ref * 100, 50)))
R['dur'] = pd.DataFrame(rows)
print(R['dur'].round(1).to_string(index=False))

# ---------------- 6번: -50% 하락 시 20% 반등 없음
def item6(eps, E, level=0.5, rb=0.2):
    out = []
    for i, e in enumerate(eps):
        g = e['_g']; k, peak = e['k'], e['peak']
        end, _, _ = horizon_end(g, k, e['next_s0'], p)
        lo = g['low'].to_numpy(float); hi = g['high'].to_numpy(float)
        t50 = next((t for t in range(k + 1, end + 1) if lo[t] <= peak * (1 - level)), None)
        if t50 is None:
            out.append(dict(i=i, reached=False, norb=False, when=None)); continue
        rm, ri, had, when = np.inf, -1, False, None
        for t in range(k + 1, t50):
            if lo[t] < rm: rm, ri = lo[t], t
            if ri >= 0 and t > ri and hi[t] >= rm * (1 + rb):
                had = True; when = t; break
        out.append(dict(i=i, reached=True, norb=not had, days=t50 - k, rb_depth=(rm / peak - 1) if had else np.nan))
    return pd.DataFrame(out)
X = item6(eps, E)
X['ticker'] = [e['ticker'] for e in eps]; X['name'] = [e['name'] for e in eps]
R['i6'] = X
reach = X[X.reached]; nor = reach[reach.norb]
res6 = dict(total_ep=len(eps), total_tk=E.ticker.nunique(), reach_ep=len(reach), reach_tk=reach.ticker.nunique(),
            norb_ep=len(nor), norb_tk=nor.ticker.nunique(), days_med=float(nor.days.median()) if len(nor) else np.nan)
for lv, rbv in ((0.5, 0.15), (0.5, 0.2), (0.5, 0.3), (0.4, 0.2), (0.6, 0.2)):
    Y = item6(eps, E, lv, rbv); r_ = Y[Y.reached]; n_ = r_[r_.norb]
    res6[f'v_{int(lv*100)}_{int(rbv*100)}'] = (len(r_), len(n_))
R['res6'] = res6; print(res6)
R['i6_names'] = nor.name.tolist()

# ---------------- 8·9번: 레그별 분할 매수 시뮬레이션 (가중치 지원)
def legs_list():
    """레그 = (그룹, 시리즈 g, 시작 idx, 기준가 ref, 종료 idx, 시작일)"""
    L = []
    Tg = T.groupby('eid')
    for i, e in enumerate(eps):
        g = e['_g']; k, peak = e['k'], e['peak']
        end, _, _ = horizon_end(g, k, e['next_s0'], p)
        L.append(dict(grp=1, g=g, k0=k, ref=peak, end=end, y=e['start_date'].year, eid=i))
        for _, t in Tg.get_group(i).iterrows() if i in Tg.groups else []:
            if t.broken:
                L.append(dict(grp=min(int(t.order) + 1, 4), g=g, k0=int(t.break_idx) - 1, ref=float(t.ref), end=end, y=e['start_date'].year, eid=i))
    return L
LEGS = legs_list()
for l in LEGS:
    l['op'] = l['g']['open'].to_numpy(float); l['hi'] = l['g']['high'].to_numpy(float)
    l['lo'] = l['g']['low'].to_numpy(float); l['cl'] = l['g']['close'].to_numpy(float)
print('레그 수', pd.Series([l['grp'] for l in LEGS]).value_counts().sort_index().to_dict())

def wavg(prices, w):
    w = np.asarray(w[:len(prices)], float); return w.sum() / (w / np.asarray(prices)).sum()

def sim(l, levels, w, tp, N=20, stop=None, stages=False):
    op, hi, lo, cl = l['op'], l['hi'], l['lo'], l['cl']; ref = l['ref']
    fills = []; j = 0; last = -1
    for t in range(l['k0'] + 1, l['end'] + 1):
        newfill = False
        while j < len(levels) and lo[t] <= ref * (1 - levels[j]):
            lv = ref * (1 - levels[j]); fills.append(op[t] if op[t] <= lv else lv); j += 1; newfill = True; last = t
        if not fills: continue
        A = wavg(fills, w)
        if stop is not None and lo[t] <= A * (1 - stop):
            sp = A * (1 - stop); px = op[t] if op[t] <= sp else sp
            return dict(n=len(fills), ret=px / A - 1, why='stop', cap=float(np.sum(w[:len(fills)])))
        if not newfill and hi[t] >= A * (1 + tp):
            tpp = A * (1 + tp); px = op[t] if op[t] >= tpp else tpp
            return dict(n=len(fills), ret=px / A - 1, why='tp', cap=float(np.sum(w[:len(fills)])))
        if t - last >= N:
            return dict(n=len(fills), ret=cl[t] / A - 1, why='time', cap=float(np.sum(w[:len(fills)])))
    if fills:
        A = wavg(fills, w); return dict(n=len(fills), ret=cl[l['end']] / A - 1, why='horizon', cap=float(np.sum(w[:len(fills)])))
    return None

def stage_stats(l, levels, w, tps, N=20):
    op, hi, lo, cl = l['op'], l['hi'], l['lo'], l['cl']; ref = l['ref']
    fills = []; j = 0
    for t in range(l['k0'] + 1, l['end'] + 1):
        while j < len(levels) and lo[t] <= ref * (1 - levels[j]):
            lv = ref * (1 - levels[j]); fills.append((t, op[t] if op[t] <= lv else lv)); j += 1
        if j >= len(levels): break
    out = {}
    for s in range(1, len(levels) + 1):
        if len(fills) < s: continue
        f = fills[s - 1][0]; A = wavg([x[1] for x in fills[:s]], w)
        nx = fills[s][0] if len(fills) > s else None
        if nx == f: continue
        we = min(f + N, l['end'] if l['end'] > f else f)
        if nx is not None: we = min(we, nx - 1)
        rng = range(f + 1, we + 1)
        if len(rng) == 0: continue
        r = dict(avg_dd=A / ref - 1, by_next=(nx is not None and nx - 1 <= f + N),
                 mfe=max(hi[t] for t in rng) / A - 1, mae=min(lo[t] for t in rng) / A - 1,
                 hit={tp: any(hi[t] >= A * (1 + tp) for t in rng) for tp in tps})
        out[s] = r
    return out

TPS = [0.05, 0.10, 0.15, 0.20]
EQ = [1, 1, 1]; W2 = [25, 35, 40]
LV1 = [0.33, 0.38, 0.43]; LV2 = [0.04, 0.09, 0.15]
GR = {1: '1차 하락(고점 기준)', 2: '2차(1차 저점 이탈)', 3: '3차', 4: '4차 이상'}
stage_rows = []; dyn_rows = []
for grp in (1, 2, 3, 4, 'all2'):
    legs = [l for l in LEGS if (l['grp'] == grp if grp != 'all2' else l['grp'] >= 2)]
    lv = LV1 if grp == 1 else LV2
    for wname, w in (('균등', EQ), ('25/35/40', W2)):
        n = len(legs); fills = {s: 0 for s in (1, 2, 3)}; st = {1: [], 2: [], 3: []}
        for l in legs:
            S = stage_stats(l, lv, w, TPS)
            for s, r in S.items(): st[s].append(r)
            res = sim(l, lv, w, 0.1)
            if res:
                for s in range(1, res['n'] + 1): fills[s] += 1
        for s in (1, 2, 3):
            a = st[s]
            if not a: continue
            stage_rows.append(dict(grp=grp, w=wname, stage=s, n_legs=n, fill=fills[s], n=len(a), avg_dd=float(np.median([x['avg_dd'] for x in a])) * 100,
                by_next=float(np.mean([x['by_next'] for x in a])) * 100, mfe=float(np.median([x['mfe'] for x in a])) * 100, mae=float(np.median([x['mae'] for x in a])) * 100,
                **{f'h{int(tp*100)}': float(np.mean([x['hit'][tp] for x in a])) * 100 for tp in TPS}))
        for tp in (0.05, 0.10):
            for stop in (None, 0.25):
                rr = [sim(l, lv, w, tp, 20, stop) for l in legs]; rr = [x for x in rr if x]
                if not rr: continue
                df = pd.DataFrame(rr); cap = (df.ret * df.cap).sum() / df.cap.sum() * 100
                dyn_rows.append(dict(grp=grp, w=wname, tp=int(tp * 100), stop=('없음' if stop is None else int(stop * 100)), n_legs=len(legs), n=len(df),
                    win=float((df.ret > 0).mean() * 100), mean=float(df.ret.mean() * 100), cap=float(cap), p10=float(df.ret.quantile(.1) * 100), worst=float(df.ret.min() * 100)))
R['stage'] = pd.DataFrame(stage_rows); R['dyn'] = pd.DataFrame(dyn_rows)
pd.set_option('display.width', 250)
print(R['stage'].round(1).to_string(index=False)); print(R['dyn'].round(1).to_string(index=False))

# ---------------- 9번: 25/35/40 가중, 승률 80%+ 레벨 탐색
def grid(legs, S, w, tp, stop=None, N=20):
    out = []
    for tri in itertools.combinations(S, 3):
        lv = [x / 100 for x in tri]
        rr = [sim(l, lv, w, tp, N, stop) for l in legs]; rr = [x for x in rr if x]
        if len(rr) < 20: continue
        df = pd.DataFrame(rr); win = df.ret > 0
        wins = df.ret[win].mean() if win.any() else np.nan; loss = -df.ret[~win].mean() if (~win).any() else np.nan
        out.append(dict(levels=tri, n_fill=len(df), fill_rate=len(df) / len(legs) * 100, win=float(win.mean() * 100),
                        mean=float(df.ret.mean() * 100), cap=float((df.ret * df.cap).sum() / df.cap.sum() * 100),
                        pl=float(wins / loss) if loss == loss and loss else np.nan, worst=float(df.ret.min() * 100), p10=float(df.ret.quantile(.1) * 100)))
    return pd.DataFrame(out)
S2 = [2, 4, 6, 8, 10, 12, 15, 18, 20, 25]
S1 = [30, 33, 35, 38, 40, 43, 45, 48, 50, 55]
if __name__=='__main__':
    G = {}
    legs2 = [l for l in LEGS if l['grp'] >= 2]; legs1 = [l for l in LEGS if l['grp'] == 1]
    for name, legs, S in (('leg2p', legs2, S2), ('leg1', legs1, S1)):
        for tp in (0.05, 0.10):
            for stop in (None, 0.25):
                G[(name, int(tp * 100), stop)] = grid(legs, S, W2, tp, stop)
    # 전/후반 검증용
    def split(legs): return [l for l in legs if l['y'] <= 2022], [l for l in legs if l['y'] >= 2023]
    R['grid'] = G
    R['gridS'] = (S1, S2)
    pickle.dump(dict(R=R, X=X), open('R3.pkl', 'wb'))
    for k, v in G.items():
        ok = v[v.win >= 80].sort_values('cap', ascending=False).head(5)
        print(k, len(v), 'win>=80:', (v.win >= 80).sum()); print(ok.round(1).to_string(index=False))
