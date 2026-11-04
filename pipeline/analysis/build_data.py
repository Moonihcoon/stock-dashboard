import pickle, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *

B = ''
E = pd.read_pickle(B + 'E_v2.pkl'); T = pd.read_pickle(B + 'T_v2.pkl')
eps = pickle.load(open(B + 'eps_v2.pkl', 'rb'))
ST = pd.read_pickle(B + 'ST.pkl'); DYN = pd.read_pickle(B + 'DYN.pkl')
SUB = pd.read_pickle(B + 'SUB.pkl'); CV = pd.read_pickle(B + 'CV.pkl'); SENS = pd.read_pickle(B + 'SENS2.pkl')
p = P()


def hz(depths, events, edges, labels):
    """반개구간 (lo, hi] 동일 폭 hazard. 경계 부동소수 오차 방지를 위해 1e-9 단위로 반올림."""
    d = np.round(np.asarray(depths, float), 9); ev = np.asarray(events, bool)
    rows = []
    for i, (hi_e, lo_e) in enumerate(zip(edges[:-1], edges[1:])):
        hi_e = round(hi_e, 9); lo_e = round(lo_e, 9)
        at = (d <= hi_e).sum()
        inb = (d <= hi_e) & (d > lo_e) if i < len(labels) - 1 else (d <= hi_e)
        e_ = int((inb & ev).sum()); c_ = int((inb & ~ev).sum())
        eff = at - c_ / 2
        lo, hi = wilson(e_, eff) if eff > 0 else (np.nan, np.nan)
        rows.append(dict(label=labels[i], at_risk=int(at), events=e_, cens=c_,
                         hazard=(e_ / eff if eff > 0 else None), lo=lo, hi=hi))
    return rows


first = T[T.order == 1]
e1 = [-0.30, -0.35, -0.40, -0.45, -0.50, -0.55, -0.60, -9]
l1 = ['-30~-35', '-35~-40', '-40~-45', '-45~-50', '-50~-55', '-55~-60', '-60 이하']
H1 = hz(first.dd_peak, np.ones(len(first), bool), e1, l1)
r = T[T.order >= 2]
cens = E[E.end_reason == 'broke_no_rebound']
e2 = [0.0, -0.05, -0.10, -0.15, -0.20, -0.25, -0.30, -9]
l2 = ['0~-5', '-5~-10', '-10~-15', '-15~-20', '-20~-25', '-25~-30', '-30 이하']
H2 = hz(np.r_[r.depth_vs_ref.values, cens.cens_depth_ref.values], np.r_[np.ones(len(r), bool), np.zeros(len(cens), bool)], e2, l2)
print('H1 합계 이벤트', sum(x['events'] for x in H1), '(기대 %d)' % len(first))
print('H2 합계 이벤트', sum(x['events'] for x in H2), '(기대 %d)' % len(r))

# ---- 종목 리스트
E = E.sort_values('start_date').reset_index(drop=True)
E['mc_lag_days'] = [(pd.Timestamp(a) - pd.Timestamp(b)).days if pd.notna(b) else np.nan for a, b in zip(E.base_date, E.mcap_date)]
print('시총 관측일과 상승 직전일 간격(일): 최대', E.mc_lag_days.abs().max(), '| 0일(당일 관측)', int((E.mc_lag_days == 0).sum()), '/', len(E))
lst = pd.DataFrame(dict(
    종목명=E.name, 시장=E.market, 종목코드=E.ticker,
    상승시작일=E.start_date.dt.strftime('%Y-%m-%d'),
    상승률5일_장중고가=(E.rise5 * 100).round(1),
    상승률5일_종가=(E.rise5_close * 100).round(1),
    일평균거래대금_억=E.avg_value_eok.round(0).astype(int),
    조건충족일수=E.big_days,
    시가총액_억=E.mcap_eok.round(0),
    시총기준일=pd.to_datetime(E.mcap_date).dt.strftime('%Y-%m-%d'),
    고점일=E.peak_date.dt.strftime('%Y-%m-%d'),
    고점까지_총상승률=(E.total_rise * 100).round(0),
    최대낙폭_6개월=(E.max_dd * 100).round(1),
    반등횟수=E.n_rebounds, 저점이탈후_재반등횟수=E.repeats,
    추적=np.where(E.complete, '6개월 완료', np.where(E.trunc, '다음 급등으로 단축', '데이터 종료로 미완')),
))
lst.to_csv(B + '급등종목_리스트.csv', index=False, encoding='utf-8-sig')
try:
    lst.to_excel(B + '급등종목_리스트.xlsx', index=False)
    print('xlsx 저장')
except Exception as ex:
    print('xlsx 생략:', type(ex).__name__)
print('리스트', len(lst), '행')

# ---- 차수별
b = T[T.broken == True]
ordr = T.copy(); ordr['o'] = ordr.order.clip(upper=7)
byo = ordr.groupby('o').agg(n=('dd_peak', 'size'), dd_med=('dd_peak', lambda s: s.median() * 100),
                            brk_med=('depth_vs_ref', lambda s: s.median() * 100)).reset_index()
bb = b.copy(); bb['o'] = bb.order.clip(upper=7)
legs = bb.groupby('o').agg(n_leg=('leg_ret', 'size'), leg_med=('leg_ret', lambda s: s.median() * 100),
                           leg_p25=('leg_ret', lambda s: s.quantile(.25) * 100), leg_p75=('leg_ret', lambda s: s.quantile(.75) * 100),
                           days_med=('days_to_break', 'median')).reset_index()
f5 = ordr.groupby('o').agg(f5_med=('fwd5_max_trough', lambda s: s.median() * 100)).reset_index()
byo = byo.merge(legs, on='o').merge(f5, on='o')
print(byo.round(1).to_string(index=False))
# 마지막(미이탈) 레그 - 검열
cen_leg = T[T.broken == False]
print('이탈 미확인(검열) 레그', len(cen_leg), '| 레그수익 중앙 %.1f%%' % (cen_leg.leg_ret.median() * 100))

# ---- 예시 에피소드 선정: 6개월 완료, 첫 저점 중앙값 근처, 반등 4~6회
fm = first.dd_peak.median()
cand = E[(E.complete) & (E.n_rebounds.between(4, 6))].merge(first[['eid', 'dd_peak']], on='eid')
cand['sc'] = (cand.dd_peak - fm).abs() + 0.002 * (cand.n_rebounds - 5).abs()
cand = cand.sort_values('sc').head(5)
print(cand[['name', 'start_date', 'dd_peak', 'n_rebounds', 'eid']].to_string(index=False))
