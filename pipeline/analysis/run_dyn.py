import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *

eps = pickle.load(open('eps_v2.pkl', 'rb'))
E = pd.read_pickle('E_v2.pkl')
p = P()
LEVELS = [0.33, 0.38, 0.43]


def run_all(eps_sub, levels, tp, N, stop):
    out = []
    for e in eps_sub:
        g = e['_g']
        end, _, _ = horizon_end(g, e['k'], e['next_s0'], p)
        r = simulate_dynamic(g, e['k'], e['peak'], end, levels, tp, N, stop)
        if r is not None:
            r['name'] = e['name']; r['start'] = e['start_date']
            out.append(r)
    return pd.DataFrame(out)


def summ(df, n_total):
    if df.empty:
        return {}
    return dict(체결=len(df), 체결률=len(df) / n_total * 100, 승률=(df.ret > 0).mean() * 100,
                평균=df.ret.mean() * 100, 중앙=df.ret.median() * 100, P10=df.ret.quantile(.1) * 100,
                최악=df.ret.min() * 100,
                익절=(df.why == 'tp').mean() * 100, 시간청산=(df.why.isin(['time', 'horizon'])).mean() * 100,
                손절=(df.why == 'stop').mean() * 100)


pd.set_option('display.width', 220)
rows = []
for tp in (0.05, 0.10, 0.15, 0.20):
    for N in (20, 40):
        for stop in (None, 0.15, 0.25):
            df = run_all(eps, LEVELS, tp, N, stop)
            s = summ(df, len(eps))
            s.update(익절목표=f'+{int(tp*100)}%', 보유일=N, 손절=('없음' if stop is None else f'-{int(stop*100)}%'),
                     손절비율=s.pop('손절'))
            rows.append(s)
D = pd.DataFrame(rows)
D = D[['익절목표', '보유일', '손절', '체결', '승률', '평균', '중앙', 'P10', '최악', '익절', '시간청산', '손절비율']]
D.columns = ['익절', '최대보유일', '손절', '체결수', '승률%', '평균%', '중앙%', 'P10%', '최악%', '익절%', '시간청산%', '손절%']
print('=== 3분할 [-33,-38,-43] 동적 시뮬레이션 (n=%d 에피소드) ===' % len(eps))
print(D.round(1).to_string(index=False))
D.to_pickle('DYN.pkl')

# --- 단계별 결과 (+10%, 20일, 손절 없음 / -25%)
for stop in (None, 0.25):
    df = run_all(eps, LEVELS, 0.10, 20, stop)
    print(f'\n--- 최종 체결 단계별 (익절+10%, 20일, 손절 {"없음" if stop is None else int(stop*100)}) ---')
    t = df.groupby('stage').agg(n=('ret', 'size'), 승률=('ret', lambda s: (s > 0).mean() * 100), 평균=('ret', lambda s: s.mean() * 100),
                                 중앙=('ret', lambda s: s.median() * 100), 평단=('avg', 'median')).round(1)
    print(t.to_string())

# --- 전반/후반 교차검증: 전반(2020~2022 시작) 분포로 진입구간 산정 -> 후반(2023~) 적용
T = pd.read_pickle('T_v2.pkl')
Ef = E[['eid', 'start_date']]
first = T[T.order == 1].merge(Ef, on='eid')
tr_set = first[first.start_date < '2023-01-01']; te_set = first[first.start_date >= '2023-01-01']
print('\n=== 교차검증 ===')
for lab, s in (('전반 2020~2022', tr_set), ('후반 2023~2026', te_set)):
    v = s.dd_peak.values * 100
    print(f'{lab}: n={len(v)} 첫저점 중앙 {np.median(v):.1f}% / P25 {np.percentile(v,25):.1f}% / P75 {np.percentile(v,75):.1f}% / 평균 {v.mean():.1f}%')
tr_lv = [round(-np.percentile(tr_set.dd_peak.values * 100, q) / 100, 2) for q in (75, 50, 25)]
print('전반에서 도출한 레벨(고점대비):', tr_lv)
te_eps = [e for e in eps if e['start_date'] >= pd.Timestamp('2023-01-01')]
tr_eps = [e for e in eps if e['start_date'] < pd.Timestamp('2023-01-01')]
for lab, sub in (('전반(학습구간)', tr_eps), ('후반(검증구간)', te_eps)):
    for tp in (0.05, 0.10):
        df = run_all(sub, tr_lv, tp, 20, 0.25)
        s = summ(df, len(sub))
        print(f'  {lab} 레벨{tr_lv} 익절+{int(tp*100)}% 손절-25%: 체결 {s["체결"]}/{len(sub)}, 승률 {s["승률"]:.1f}%, 평균 {s["평균"]:.1f}%, 중앙 {s["중앙"]:.1f}%, P10 {s["P10"]:.1f}%')

