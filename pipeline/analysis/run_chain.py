import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *


def run_chain(eps, p: P):
    erows, trows = [], []
    for i, e in enumerate(eps):
        g = e['_g']
        k, peak = e['k'], e['peak']
        end, complete, trunc = horizon_end(g, k, e['next_s0'], p)
        ch = analyze_chain(g, k, peak, end, p)
        tr = ch['troughs']
        rec = {kk: vv for kk, vv in e.items() if kk not in ('_g',)}
        rec.update(eid=i, e_idx=end, e_date=g['date'].iloc[end], complete=complete, trunc=trunc,
                   follow_days=end - k, reached30=ch['reached30'], max_dd=ch.get('max_dd', np.nan),
                   n_rebounds=len(tr), end_reason=ch['end'], cens_depth=ch['cens_depth'],
                   cens_depth_ref=ch.get('cens_depth_ref', np.nan),
                   cond2=len(tr) >= 1, cond3=len(tr) >= 2, repeats=max(0, len(tr) - 1))
        erows.append(rec)
        for j, t in enumerate(tr):
            trows.append(dict(eid=i, ticker=e['ticker'], name=e['name'], order=j + 1, **{
                kk: vv for kk, vv in t.items()}))
    return pd.DataFrame(erows), pd.DataFrame(trows)


if __name__ == '__main__':
    p = P()
    eps = pickle.load(open('eps_v2.pkl', 'rb'))
    E, T = run_chain(eps, p)
    E.to_pickle('E_v2.pkl'); T.to_pickle('T_v2.pkl')
    pd.set_option('display.width', 220)
    print('에피소드', len(E), '| 종목', E.ticker.nunique())
    print('추적기간 6개월 완료:', int(E.complete.sum()), '| 다음 급등으로 단축:', int(E.trunc.sum()),
          '| 데이터 종료로 미완:', int((~E.complete & ~E.trunc).sum()))
    print('고점 후 -30% 도달(reached30):', int(E.reached30.sum()))
    print('조건2 (-30% 후 +10% 반등):', int(E.cond2.sum()), '| 조건3 (저점이탈 후 재반등 1회+):', int(E.cond3.sum()))
    print('종료 사유:'); print(E.end_reason.value_counts().to_string())
    print('\n반복 횟수(rebound 수) 분포:'); print(E.n_rebounds.value_counts().sort_index().to_string())
    print('\n조건2 만족 에피소드 첫 저점 고점대비(%):')
    f = T[T.order == 1]
    print((f.dd_peak * 100).describe([.1, .25, .5, .75, .9]).round(1).to_string())
    print('\n차수별 (이탈 확인된 레그만) 반등률%, 이탈 직전까지 최대:')
    b = T[T.broken == True]
    print(b.groupby('order').agg(n=('leg_ret', 'size'), 중앙=('leg_ret', lambda s: s.median() * 100), 평균=('leg_ret', lambda s: s.mean() * 100)).round(1).to_string())
    print('\n직전 저점 이탈 후 재반등 시 추가 하락폭(%):')
    r = T[T.order >= 2]
    print((r.depth_vs_ref * 100).describe([.1, .25, .5, .75, .9]).round(1).to_string())
