from common import analysis_panel
import pickle, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *
from run_chain import run_chain

d = analysis_panel()
LV = [0.33, 0.38, 0.43]
out = {}


def chain_summary(p, label):
    eps = find_episodes(d, p)
    E, T = run_chain(eps, p)
    if E.empty:
        return dict(label=label, n=0)
    first = T[T.order == 1]
    r = T[T.order >= 2]
    s = dict(label=label, n=len(E), tickers=int(E.ticker.nunique()), cond2=int(E.cond2.sum()), cond3=int(E.cond3.sum()),
             repeats_total=int(E.repeats.sum()), repeats_mean=float(E.repeats.mean()),
             first_med=float(first.dd_peak.median() * 100) if len(first) else np.nan,
             first_p25=float(first.dd_peak.quantile(.25) * 100) if len(first) else np.nan,
             first_p75=float(first.dd_peak.quantile(.75) * 100) if len(first) else np.nan,
             brk_med=float(r.depth_vs_ref.median() * 100) if len(r) else np.nan)
    return s


rows = []
base = P()
rows.append(chain_summary(base, '기준 (장중고가 +80%, 3천억×3일, 직전 저점 이탈)'))
rows.append(chain_summary(P(use_high=False), '종가 기준 +80%'))
rows.append(chain_summary(P(val_thresh=5000 * EOK), '거래대금 5천억×3일'))
rows.append(chain_summary(P(val_days=2), '3천억 × 2일 이상'))
rows.append(chain_summary(P(rise=0.70), '상승률 +70%'))
rows.append(chain_summary(P(ref='confirm_day'), '이탈 기준 = 반등확인일 저가'))
rows.append(chain_summary(P(rb=0.15), '반등 기준 +15%'))
rows.append(chain_summary(P(rb=0.20), '반등 기준 +20%'))
S = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(S.round(1).to_string(index=False))
S.to_pickle('SENS2.pkl')

# 일봉 한계 정량화: 첫 저점 확정일 이전 '저점일' 하루 안의 변동폭이 10% 이상인 비율
T = pd.read_pickle('T_v2.pkl')
print(f'\n저점일 하루 고저폭 >= 10% 비율: {(T.same_day_range >= 0.10).mean() * 100:.1f}% (전체 {len(T)}개 저점)')
print(f'  첫 저점만: {(T[T.order == 1].same_day_range >= 0.10).mean() * 100:.1f}%')
print(f'  저점일 고저폭 중앙값: {T.same_day_range.median() * 100:.1f}%')
out['same_day_ge10'] = float((T.same_day_range >= 0.10).mean() * 100)
out['same_day_med'] = float(T.same_day_range.median() * 100)

# 부분표본 (자본가중)
eps = pickle.load(open('eps_v2.pkl', 'rb'))
p = P()


def run_all(sub, lv, tp, N, stop):
    o = []
    for e in sub:
        g = e['_g']; end, _, _ = horizon_end(g, e['k'], e['next_s0'], p)
        r = simulate_dynamic(g, e['k'], e['peak'], end, lv, tp, N, stop)
        if r:
            o.append(r)
    return pd.DataFrame(o)


def cap(df):
    u = df.stage
    return dict(n=len(df), 승률=(df.ret > 0).mean() * 100, 단순=df.ret.mean() * 100, 자본가중=(df.ret * u).sum() / u.sum() * 100,
                P10=df.ret.quantile(.1) * 100)


subs = {
    '전체': eps,
    '2020년 제외': [e for e in eps if e['start_date'].year != 2020],
    '2026년 제외': [e for e in eps if e['start_date'].year != 2026],
    '2020·2026 제외': [e for e in eps if e['start_date'].year not in (2020, 2026)],
    '코스닥': [e for e in eps if e['market'] == 'KOSDAQ'],
    '코스피': [e for e in eps if e['market'] == 'KOSPI'],
    '전반 2020~2022': [e for e in eps if e['start_date'] < pd.Timestamp('2023-01-01')],
    '후반 2023~2026': [e for e in eps if e['start_date'] >= pd.Timestamp('2023-01-01')],
}
rows = []
for lab, sub in subs.items():
    for tp in (0.05, 0.10):
        df = run_all(sub, LV, tp, 20, 0.25)
        c = cap(df); c.update(구분=lab, 익절=f'+{int(tp*100)}%', 에피소드=len(sub))
        rows.append(c)
SUB = pd.DataFrame(rows)[['구분', '익절', '에피소드', 'n', '승률', '단순', '자본가중', 'P10']]
print('\n=== 부분표본 (고정 레벨 -33/-38/-43, 손절 -25%, 20일) ===')
print(SUB.round(1).to_string(index=False))
SUB.to_pickle('SUB.pkl')

# 전/후반 교차검증 (전반 분포로 레벨 도출 -> 후반에 적용)
E = pd.read_pickle('E_v2.pkl')
first = T[T.order == 1].merge(E[['eid', 'start_date']], on='eid')
tr = first[first.start_date < '2023-01-01'].dd_peak.values * 100
lv_tr = [round(-np.percentile(tr, q) / 100, 2) for q in (75, 50, 25)]
rows = []
for lab, sub in (('전반(학습)', subs['전반 2020~2022']), ('후반(검증)', subs['후반 2023~2026'])):
    for tp in (0.05, 0.10):
        df = run_all(sub, [float(x) for x in lv_tr], tp, 20, 0.25)
        c = cap(df); c.update(구분=lab, 익절=f'+{int(tp*100)}%', 레벨=str([int(x * 100) for x in lv_tr]))
        rows.append(c)
CV = pd.DataFrame(rows)[['구분', '레벨', '익절', 'n', '승률', '단순', '자본가중', 'P10']]
print('\n=== 교차검증 ===')
print(CV.round(1).to_string(index=False))
CV.to_pickle('CV.pkl')
