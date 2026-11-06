"""10. 고점 → 첫 반등까지 기간, 상승폭(20% 단위)별 비교, 하락기 거래대금 비율.

정의 (기준 조건 +80% / 3천억 3일 사례):
- 상승폭: 급등 시작 전일 종가(base_close) 대비 고점(peak, 장중 고가) 상승률. 20% 단위 구간.
- 첫 반등: 고점 대비 -30% 이상 하락한 뒤 저점 대비 +10% 반등이 나온 첫 번째 저점(T order 1).
  고점→저점 거래일, 고점→반등 확정일(+10% 도달일) 거래일, 저점의 고점 대비 하락률.
- 거래대금 비율: 하락기(고점 다음날~저점일) 일평균 거래대금 ÷ 상승기(급등 시작일~고점일) 일평균 거래대금.
"""
import pickle
import numpy as np, pandas as pd
try:
    from scipy import stats
except ImportError:          # 처음 한 번 자동 설치
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'scipy'], check=True)
    from scipy import stats

E = pd.read_pickle('E_v2.pkl'); T = pd.read_pickle('T_v2.pkl')
eps = pickle.load(open('eps_v2.pkl', 'rb'))
t1 = T[T['order'] == 1].set_index('eid')
rows = []
for i, e in enumerate(eps):
    r = E.iloc[i]
    g = e['_g']; s0, k = int(e['s0']), int(e['k'])
    v = g['value'].to_numpy(float) / 1e8
    rise_v = v[s0:k + 1].mean()
    d = dict(eid=int(r.eid), name=r['name'], ticker=r.ticker, start=r.start_date, peak_date=r.peak_date,
             rise=float(r.total_rise) * 100, rise_v=rise_v, reached30=bool(r.reached30))
    if r.eid in t1.index:
        x = t1.loc[r.eid]
        tr, cf = int(x['idx']), int(x['confirm'])
        d.update(days_trough=int(x['days_from_peak']), days_confirm=cf - k, dd=float(x['dd_peak']) * 100,
                 fall_v=v[k + 1:tr + 1].mean() if tr > k else np.nan,
                 fall_v_sum=v[k + 1:tr + 1].sum(), rise_v_sum=v[s0:k + 1].sum(),
                 rebound=float(x['leg_ret']) * 100)
        d['ratio'] = d['fall_v'] / rise_v if rise_v > 0 else np.nan
    rows.append(d)
D = pd.DataFrame(rows)
edges = [80, 100, 120, 140, 160, 180, 200, np.inf]
labels = ['80~100%', '100~120%', '120~140%', '140~160%', '160~180%', '180~200%', '200% 이상']
D['bin'] = pd.cut(D['rise'], edges, labels=labels, right=False)

def q(s, p):
    s = s.dropna()
    return float(np.percentile(s, p)) if len(s) else np.nan

G = []
for b in labels:
    x = D[D['bin'] == b]; y = x.dropna(subset=['days_trough'])
    G.append(dict(bin=b, n=len(x), n_reb=len(y),
                  days_med=q(y.days_trough, 50), days_q1=q(y.days_trough, 25), days_q3=q(y.days_trough, 75),
                  conf_med=q(y.days_confirm, 50),
                  dd_med=q(y.dd, 50), dd_q1=q(y.dd, 25), dd_q3=q(y.dd, 75),
                  reb_med=q(y.rebound, 50), ratio_med=q(y.ratio, 50), ratio_q1=q(y.ratio, 25), ratio_q3=q(y.ratio, 75)))
G = pd.DataFrame(G)
A = D.dropna(subset=['days_trough'])
# 통계 검정
lr = np.log(A['ratio'].dropna())
wil = stats.wilcoxon(lr) if len(lr) > 5 else None                          # 하락기 = 상승기 ?
sp_rise_days = stats.spearmanr(A.rise, A.days_trough)
sp_rise_dd = stats.spearmanr(A.rise, A.dd)
sp_ratio_dd = stats.spearmanr(A.ratio, A.dd, nan_policy='omit')
sp_ratio_days = stats.spearmanr(A.ratio, A.days_trough, nan_policy='omit')
sp_ratio_reb = stats.spearmanr(A.ratio, A.rebound, nan_policy='omit')
kw_days = stats.kruskal(*[A[A['bin'] == b].days_trough for b in labels if (A['bin'] == b).sum() >= 3])
kw_dd = stats.kruskal(*[A[A['bin'] == b].dd for b in labels if (A['bin'] == b).sum() >= 3])
# 거래대금 비율 3분위별 하락폭·반등
A = A.copy()
A['rq'] = pd.qcut(A['ratio'], 3, labels=['낮음', '중간', '높음'])
RQ = A.groupby('rq', observed=True).agg(n=('eid', 'size'), ratio=('ratio', 'median'), dd=('dd', 'median'),
                                        days=('days_trough', 'median'), reb=('rebound', 'median')).reset_index()
R4 = dict(D=D, G=G, RQ=RQ, n=len(D), n_reb=len(A),
          all=dict(days_med=q(A.days_trough, 50), days_q1=q(A.days_trough, 25), days_q3=q(A.days_trough, 75),
                   conf_med=q(A.days_confirm, 50), dd_med=q(A.dd, 50), ratio_med=q(A.ratio, 50),
                   ratio_q1=q(A.ratio, 25), ratio_q3=q(A.ratio, 75), share_lt1=float((A.ratio < 1).mean()),
                   share_lt05=float((A.ratio < 0.5).mean())),
          test=dict(wil_p=float(wil.pvalue) if wil else np.nan,
                    rise_days=(float(sp_rise_days.statistic), float(sp_rise_days.pvalue)),
                    rise_dd=(float(sp_rise_dd.statistic), float(sp_rise_dd.pvalue)),
                    ratio_dd=(float(sp_ratio_dd.statistic), float(sp_ratio_dd.pvalue)),
                    ratio_days=(float(sp_ratio_days.statistic), float(sp_ratio_days.pvalue)),
                    ratio_reb=(float(sp_ratio_reb.statistic), float(sp_ratio_reb.pvalue)),
                    kw_days=float(kw_days.pvalue), kw_dd=float(kw_dd.pvalue)))
pickle.dump(R4, open('R4.pkl', 'wb'))
if __name__ == '__main__':
    print(G.round(2).to_string()); print(RQ.round(2).to_string()); print(R4['all']); print(R4['test'])
