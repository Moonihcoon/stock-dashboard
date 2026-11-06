"""키움에서 받은 시세를 다른 분석용으로 내보냅니다.

결과 (설정 폴더 옆 export 폴더, 예: 바탕화면\\stock\\export):
  daily_2020_최종일.parquet   2020-01-01 이후 전 종목 일봉 (파이썬·R 용, 가장 빠름)
  csv\\daily_YYYY.csv         같은 내용을 연도별 CSV로 (엑셀/기타 도구용, UTF-8)
  minute\\종목코드.parquet     급등 종목 1분봉 (받아 둔 것만, 약 1년치)
  tickers.csv                 종목 목록 (코드, 이름, 시장, ETF/ETN 여부, 우선주 여부, 첫·마지막 날짜)
  README_데이터설명.txt
"""
from __future__ import annotations
import shutil, sys
import pandas as pd
from common import REPO, load_panel, etf_codes, work_dir, log
from classify import is_etf, is_pref


def main():
    out = REPO.parent / 'export'
    (out / 'csv').mkdir(parents=True, exist_ok=True)
    d = load_panel()
    d = d[d['date'] >= '2020-01-01'].copy()
    ec = etf_codes()
    nm = d.drop_duplicates('ticker', keep='last').set_index('ticker')
    etf = {t for t, n in zip(nm.index, nm['name']) if is_etf(t, n, ec)}
    d['is_etf'] = d['ticker'].isin(etf).astype(int)
    d = d.drop(columns=['industry_name'])
    last = d['date'].max().strftime('%Y%m%d')
    for f in out.glob('daily_2020_*.parquet'):
        f.unlink()
    d.to_parquet(out / f'daily_2020_{last}.parquet', index=False)
    for y, g in d.groupby(d['date'].dt.year):
        g.to_csv(out / 'csv' / f'daily_{y}.csv', index=False, encoding='utf-8-sig')
    t = d.groupby('ticker').agg(name=('name', 'last'), market=('market', 'last'), first=('date', 'min'),
                                last=('date', 'max'), rows=('date', 'size'), is_etf=('is_etf', 'max')).reset_index()
    t['is_pref'] = [int(is_pref(x)) for x in t['ticker']]
    t.to_csv(out / 'tickers.csv', index=False, encoding='utf-8-sig')
    md = work_dir() / 'minute'
    if md.exists():
        shutil.copytree(md, out / 'minute', dirs_exist_ok=True)
    (out / 'README_데이터설명.txt').write_text(f'''키움 REST API로 받은 코스피·코스닥 시세 (2020-01-01 ~ {d['date'].max():%Y-%m-%d})
행 수 {len(d):,} / 종목 {d['ticker'].nunique():,}

[daily 열 설명]
date                 거래일
open/high/low/close  시가/고가/저가/종가 (원, 키움 수정주가 기준)
volume               거래량 (주)
value                거래대금 (원)
ticker/name/market   종목코드/종목명/시장(KOSPI·KOSDAQ)
market_cap_won       시가총액 (원). 2026-10-23까지는 기존 수집 값,
                     그 뒤는 종가 x 받은 날 상장주식수(키움 종목정보)
market_cap_observed  1=시가총액 값 있음, 0=없음(ETF·ETN은 없음)
is_etf               1=ETF/ETN

[주의]
- 상장폐지 종목은 들어 있지 않습니다(생존 편향).
- 우선주·스팩·리츠는 수집 대상에서 빠져 있습니다.
- ETF·ETN은 2026-10-27까지만 있고 그 뒤로는 받지 않습니다.
- 분봉(minute 폴더)은 대시보드 급등 종목만, 키움이 주는 최근 약 1년치입니다.
  열: time(분), open, high, low, close, volume, ticker. 정규장 외 시간(NXT) 체결도 포함될 수 있습니다.
''', encoding='utf-8')
    log(f'내보내기 완료 -> {out} ({len(d):,}행, {d["ticker"].nunique():,}종목, 최종일 {last})')
    return out


if __name__ == '__main__':
    main()
