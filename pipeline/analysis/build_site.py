"""대시보드용 시세 데이터 생성 (work/web 아래).

data/dates.json        거래일 목록 (인덱스 = di)
data/tick.json         [종목코드, 종목명, 시장] (인덱스 = ti)  ※ ETF·ETN·우선주 제외
data/top/YYYY-MM.json  {di: [[ti, 상승률%, 거래대금(억), 종가, 시가총액(억)|null], ... 상위 200]}
px/m/YYYY-MM.txt       월별 전 종목 일봉 (gzip+base64 JSON {ti: run})
월 단위로 나눠서, 매일 바뀌는 파일은 이번 달 것 두 개뿐입니다(저장소 용량 관리).
"""
import base64, gzip, json, os, shutil
import numpy as np, pandas as pd
from common import analysis_panel

W = 'web'
d = analysis_panel()[['date', 'ticker', 'name', 'market', 'open', 'high', 'low', 'close', 'value',
                      'market_cap_won', 'market_cap_observed']].copy()
dates = sorted(d.date.unique()); di = {x: i for i, x in enumerate(dates)}
d['di'] = d.date.map(di)
d = d.sort_values(['ticker', 'date']).reset_index(drop=True)
d['pc'] = d.groupby('ticker').close.shift()
d = d[d.date >= '2020-01-01']
for sub in ('data/top', 'px/m'):
    shutil.rmtree(f'{W}/{sub}', ignore_errors=True); os.makedirs(f'{W}/{sub}', exist_ok=True)
dump = lambda p, o: open(f'{W}/{p}', 'w', encoding='utf-8').write(json.dumps(o, ensure_ascii=False, separators=(',', ':')))
dump('data/dates.json', [str(pd.Timestamp(x).date()) for x in dates])
nm = d.drop_duplicates('ticker', keep='last').set_index('ticker')
tk = sorted(d.ticker.unique()); ti = {t: i for i, t in enumerate(tk)}
dump('data/tick.json', [[t, nm.loc[t, 'name'], nm.loc[t, 'market']] for t in tk])
d['t'] = d.ticker.map(ti)
d['ym'] = d.date.dt.strftime('%Y-%m')

# ---- 상위 200
x = d[d.pc.notna() & (d.pc > 0) & (d.close > 0)].copy()
x['rate'] = (x.close / x.pc - 1) * 100
x = x.sort_values(['di', 'rate'], ascending=[True, False])
x = x.groupby('di').head(200)
x['mc'] = np.where(x.market_cap_observed == 1, x.market_cap_won / 1e8, np.nan)
for ym, g in x.groupby('ym'):
    o = {}
    for dd, h in g.groupby('di'):
        o[int(dd)] = [[int(r.t), round(float(r.rate), 2), round(float(r.value) / 1e8, 1), int(r.close),
                       None if not np.isfinite(r.mc) else int(round(r.mc))] for r in h.itertuples()]
    dump(f'data/top/{ym}.json', o)

# ---- 월별 일봉
sz = 0
for ym, g in d.groupby('ym'):
    out = {}
    for t, h in g.groupby('t'):
        c = h.close.to_numpy(np.int64); o = h.open.to_numpy(np.int64)
        hi = h.high.to_numpy(np.int64); lo = h.low.to_numpy(np.int64); dd = h.di.to_numpy(np.int64)
        o = np.where(o > 0, o, c)
        hi = np.maximum(hi, c); lo = np.where(lo > 0, np.minimum(lo, c), c)
        out[int(t)] = dict(d0=int(dd[0]), d=np.diff(dd).tolist(), c=[int(c[0])] + np.diff(c).tolist(),
                           o=(o - np.r_[c[0], c[:-1]]).tolist(), h=(hi - c).tolist(), l=(c - lo).tolist(),
                           v=np.round(h.value.to_numpy() / 1e7).astype(int).tolist())
    b = gzip.compress(json.dumps(out, separators=(',', ':')).encode(), 9)
    open(f'{W}/px/m/{ym}.txt', 'w').write(base64.b64encode(b).decode()); sz += len(b)
print('dates', len(dates), 'tickers', len(tk), 'px', round(sz / 1e6, 1), 'MB gz')
