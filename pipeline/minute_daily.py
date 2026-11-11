"""1분봉 → 일별 요약 (정규장 09:00~15:30만).

통계 엔진이 분봉이 있는 기간(키움 제공 최근 약 1년)에 쓰는 값:
  mh, ml, mc   정규장 분봉으로 잡은 당일 고가·저가·종가(15:30 이전 마지막 체결)
  hpre         당일 저가가 나온 분 '이전' 분봉들의 최고가 (없으면 빈칸)
  hpost        당일 저가가 나온 분 '이후' 분봉들의 최고가
  lpost        당일 고가가 나온 분 '이후' 분봉들의 최저가
  nbars        정규장 분봉 개수
저가·고가가 나온 바로 그 1분 안의 선후는 알 수 없으므로 그 분은 앞뒤 어디에도 넣지 않습니다(보수적).

원본: 저장소 옆 minute_all 폴더(전 종목) + work\\minute(급등 종목). 결과: work\\minute_daily.parquet
바뀐 파일만 다시 계산합니다(파일 수정 시각 기준).
"""
from __future__ import annotations
import json, os, time
import numpy as np
import pandas as pd
from common import REPO, work_dir, log

OUT = work_dir() / 'minute_daily.parquet'
META = work_dir() / 'minute_daily_meta.json'
COLS = ['ticker', 'date', 'mh', 'ml', 'mc', 'hpre', 'hpost', 'lpost', 'nbars']


def sources():
    """종목코드 → 분봉 파일 (minute_all 우선)."""
    src = {}
    for d in (work_dir() / 'minute', REPO.parent / 'minute_all'):
        if d.exists():
            for f in d.glob('*.parquet'):
                if not f.name.startswith('_'):
                    src[f.stem] = f
    return src


def summarize(m: pd.DataFrame, ticker: str) -> pd.DataFrame:
    m = m[['time', 'high', 'low', 'close']].dropna()
    t = pd.to_datetime(m['time'])
    hm = t.dt.hour * 100 + t.dt.minute
    m = m[(hm >= 900) & (hm <= 1530)].copy()
    if m.empty:
        return pd.DataFrame(columns=COLS)
    m['time'] = pd.to_datetime(m['time'])
    m = m.sort_values('time').drop_duplicates('time', keep='last').reset_index(drop=True)
    m['date'] = m['time'].dt.normalize()
    m['pos'] = np.arange(len(m))
    g = m.groupby('date', sort=True)
    ilo = g['low'].transform('idxmin')          # 당일 최저가가 처음 나온 분
    ihi = g['high'].transform('idxmax')         # 당일 최고가가 처음 나온 분
    pre = m['high'].where(m['pos'] < ilo)
    post = m['high'].where(m['pos'] > ilo)
    lpost = m['low'].where(m['pos'] > ihi)
    s = pd.DataFrame({'date': m['date'], 'high': m['high'], 'low': m['low'], 'close': m['close'],
                      'pre': pre, 'post': post, 'lpost': lpost})
    out = s.groupby('date', sort=True).agg(mh=('high', 'max'), ml=('low', 'min'), mc=('close', 'last'),
                                           hpre=('pre', 'max'), hpost=('post', 'max'),
                                           lpost=('lpost', 'min'), nbars=('high', 'size')).reset_index()
    out.insert(0, 'ticker', ticker)
    return out[COLS]


def main():
    src = sources()
    if not src:
        log('분봉 일별 요약: 분봉 파일이 없어 건너뜁니다(통계는 일봉만 사용).')
        return 0
    meta = {}
    if META.exists() and OUT.exists():
        try:
            meta = json.load(open(META, encoding='utf-8'))
        except ValueError:
            meta = {}
    old = pd.read_parquet(OUT) if OUT.exists() and meta else pd.DataFrame(columns=COLS)
    todo = {t: f for t, f in src.items() if meta.get(t) != [str(f), f.stat().st_mtime_ns]}
    if not todo:
        log(f'분봉 일별 요약: 바뀐 분봉 파일 없음 ({len(src):,}종목)')
        return len(old)
    t0 = time.time()
    parts, done = [], {}
    for i, (t, f) in enumerate(sorted(todo.items()), 1):
        try:
            parts.append(summarize(pd.read_parquet(f, columns=['time', 'high', 'low', 'close']), t))
            done[t] = [str(f), f.stat().st_mtime_ns]
        except Exception as e:
            log(f'  분봉 요약 실패 {t}: {e}')
        if i % 500 == 0:
            log(f'  분봉 요약 {i:,}/{len(todo):,}')
    keep = old[~old['ticker'].isin(done)] if len(old) else old
    new = pd.concat([keep] + parts, ignore_index=True) if parts else keep
    new['date'] = pd.to_datetime(new['date'])
    tmp = str(OUT) + '.tmp'
    new.to_parquet(tmp, index=False)
    os.replace(tmp, OUT)
    meta = {t: v for t, v in meta.items() if t in src}
    meta.update(done)
    json.dump(meta, open(META, 'w', encoding='utf-8'))
    log(f'분봉 일별 요약: {len(done):,}종목 갱신, 전체 {new["ticker"].nunique():,}종목 · {len(new):,}일 '
        f'({new["date"].min():%Y-%m-%d} ~ {new["date"].max():%Y-%m-%d}), {time.time() - t0:.0f}초')
    return len(new)


if __name__ == '__main__':
    main()
