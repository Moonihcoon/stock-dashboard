import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *

E = pd.read_pickle('E_v2.pkl')
T = pd.read_pickle('T_v2.pkl')
eps = pickle.load(open('eps_v2.pkl', 'rb'))
p = P()
TPS = [0.05, 0.10, 0.15, 0.20, 0.30]


def hazard5(depths, events, start, n_buckets, step=0.05):
    """동일 폭(5%p) 구간 hazard. depths는 음수 비율."""
    depths = np.asarray(depths, float); events = np.asarray(events, bool)
    rows = []
    for i in range(n_buckets):
        hi_e = start - step * i; lo_e = hi_e - step
        at = (depths <= hi_e + 1e-12).sum()
        inb = (depths <= hi_e + 1e-12) & (depths > lo_e)
        if i == n_buckets - 1:
            inb = (depths <= hi_e + 1e-12)
        ev = (inb & events).sum(); ce = (inb & ~events).sum()
        eff = at - ce / 2
        h = ev / eff if eff > 0 else np.nan
        lo, hi = wilson(ev, eff) if eff > 0 else (np.nan, np.nan)
        lab = f'{hi_e*100:.0f}~{lo_e*100:.0f}%' if i < n_buckets - 1 else f'{hi_e*100:.0f}% 이하'
        rows.append(dict(구간=lab, 위험집단=int(at), 반등확정=int(ev), 중도절단=int(ce), hazard=h, CI하=lo, CI상=hi))
    return pd.DataFrame(rows)


first = T[T.order == 1]
H1 = hazard5(first.dd_peak, np.ones(len(first), bool), -0.30, 7)
r = T[T.order >= 2]
cens = E[E.end_reason == 'broke_no_rebound']
H2 = hazard5(np.r_[r.depth_vs_ref.values, cens.cens_depth_ref.values],
             np.r_[np.ones(len(r), bool), np.zeros(len(cens), bool)], 0.0, 7)
pd.set_option('display.width', 200)
print('=== 첫 반등 hazard (고점 대비 5%p 구간) ===\n', H1.round(3).to_string(index=False))
print('\n=== 저점 이탈 후 재반등 hazard (직전 저점 대비 5%p 구간) ===\n', H2.round(3).to_string(index=False))
H1.to_pickle('H1.pkl'); H2.to_pickle('H2.pkl')

# ------------------------------------------------------------------ 진입 구간
fd = first.dd_peak.values * 100
zone = dict(mean=fd.mean(), sd=fd.std(ddof=1), med=np.median(fd), p25=np.percentile(fd, 25), p75=np.percentile(fd, 75),
            p10=np.percentile(fd, 10), p90=np.percentile(fd, 90))
print('\n첫 반등저점 고점대비(%):', {k: round(v, 1) for k, v in zone.items()})
print('  mean 95% CI:', [round(x, 1) for x in boot_ci(fd, np.mean)], '| median 95% CI:', [round(x, 1) for x in boot_ci(fd, np.median)])
print(f'  -30~-40% 안에 있는 비율: {((fd <= -30) & (fd > -40)).mean() * 100:.1f}%')
print('  에피소드 6개월 최대낙폭(%) 중앙/평균/P25/P75:', E.max_dd.median().round(3) * 100, (E.max_dd.mean() * 100).round(1),
      (E.max_dd.quantile(.25) * 100).round(1), (E.max_dd.quantile(.75) * 100).round(1))

LEVELS = [0.33, 0.38, 0.43]   # 고점 대비 하락률 (P75 / P50 / P25 근방, 5%p 단위로 반올림)


def run_stage(eps_sub, levels, N=20):
    rows = []
    for e in eps_sub:
        g = e['_g']; k = e['k']; peak = e['peak']
        end, complete, trunc = horizon_end(g, k, e['next_s0'], p)
        res, fills = stage_paths(g, k, peak, end, levels, TPS, N)
        rows.append(dict(name=e['name'], start=e['start_date'], n_fill=len(fills), res=res, fills=fills, g=g, k=k, end=end))
    return rows


def summarize(rows, levels, label=''):
    n = len(rows)
    out = {'n': n}
    for s in (1, 2, 3):
        f = sum(1 for r in rows if r['n_fill'] >= s)
        st = [r['res'][s] for r in rows if s in r['res'] and r['res'][s]['wlen'] > 0]
        out[f'fill{s}'] = f
        out[f'st{s}'] = st
    return out


rows = run_stage(eps, LEVELS)
S = summarize(rows, LEVELS)
print(f'\n=== 3분할 {LEVELS} 체결 현황 (에피소드 {S["n"]}) ===')
for s in (1, 2, 3):
    print(f'  {s}차 체결: {S[f"fill{s}"]}건 ({S[f"fill{s}"]/S["n"]*100:.1f}%)')
stage_tab = []
for s in (1, 2, 3):
    st = S[f'st{s}']
    if not st:
        continue
    avgdd = np.median([x['avg_dd'] for x in st]) * 100
    row = dict(단계=s, n=len(st), 평단_고점대비=round(avgdd, 1), 다음분할로_이탈=round(np.mean([x['ended_by_next_fill'] for x in st]) * 100, 1),
               MFE중앙=round(np.nanmedian([x['mfe'] for x in st]) * 100, 1), MAE중앙=round(np.nanmedian([x['mae'] for x in st]) * 100, 1),
               종가수익중앙=round(np.nanmedian([x['close_ret'] for x in st]) * 100, 1))
    for tp in TPS:
        h = sum(1 for x in st if x['hit'].get(tp)); lo, hi = wilson(h, len(st))
        row[f'+{int(tp*100)}%'] = round(h / len(st) * 100, 1)
        row[f'+{int(tp*100)}%_CI'] = f'{lo*100:.0f}~{hi*100:.0f}'
    stage_tab.append(row)
ST = pd.DataFrame(stage_tab)
print(ST.to_string(index=False))
ST.to_pickle('ST.pkl')
pickle.dump(dict(zone=zone, levels=LEVELS), open('zone.pkl', 'wb'))
