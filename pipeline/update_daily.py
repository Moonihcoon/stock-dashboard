"""키움에서 일봉을 받아 시세 패널을 오늘까지 이어 붙입니다.

- 처음 실행: 기존 panel_kiwoom_marketcap.parquet 를 가져와서 그 다음 날부터 받습니다.
- 매일 실행: 종목마다 마지막 저장일 이후만 받습니다(대부분 1회 호출).
- 새로 상장된 종목은 2019-07-01부터 전부 받습니다.
- 수정주가(액면분할·무상증자 등)로 과거 가격이 바뀐 종목은 과거 전체를 다시 받습니다.
- 시가총액 = 종가 × 상장주식수(ka10099 listCount, 받는 날 기준 주식수). ETF·ETN·우선주는 받지 않습니다.
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
from common import opt, kiwoom_keys, log, load_panel, save_panel, work_dir, START
from classify import is_etf


def _check_shares(d, lst):
    """상장주식수 단위 점검: 기존 시가총액과 비교해 1000배 단위 차이를 바로잡고, 맞지 않으면 비웁니다."""
    sh = pd.to_numeric(lst['shares'], errors='coerce')
    if sh.notna().sum() == 0:
        log('주의: 종목 목록에 상장주식수(listCount)가 없어 새 날짜의 시가총액을 비워 둡니다.')
        return sh
    o = d[d.market_cap_observed == 1].sort_values('date').drop_duplicates('ticker', keep='last').set_index('ticker')
    m = pd.DataFrame({'sh': sh.values}, index=lst.ticker.values).join(o[['close', 'market_cap_won']], how='inner').dropna()
    if len(m) < 50:
        return sh
    r = float(np.median(m.close * m.sh / m.market_cap_won))
    for f in (1, 1000, 0.001):
        if 0.6 < r * f < 1.6:
            if f != 1:
                log(f'상장주식수 단위 보정 x{f}')
            return sh * f
    log(f'주의: 상장주식수로 계산한 시가총액이 기존 값과 맞지 않아(비율 {r:.3g}) 새 날짜 시가총액을 비워 둡니다.')
    return sh * np.nan


def main(api=None, today: str | None = None):
    if api is None:
        from kiwoom_api import Kiwoom
        key, sec = kiwoom_keys()
        if not key or not sec:
            raise SystemExit('설정 파일의 [kiwoom] app_key / app_secret(또는 _file 경로)이 비어 있습니다.')
        api = Kiwoom(key, sec)
    if today is None:
        now = pd.Timestamp.now(tz='Asia/Seoul').tz_localize(None)
        # 장 마감(15:30) 전이면 오늘 봉은 아직 확정이 아니므로 어제까지만 받습니다.
        today = (now if now.hour * 60 + now.minute >= 15 * 60 + 40 else now - pd.Timedelta(days=1)).strftime('%Y%m%d')
    d = load_panel()
    last = d.groupby('ticker')['date'].max()
    lastc = d.sort_values('date').groupby('ticker')['close'].last()

    etf = api.etf_codes()
    if etf:
        old = set()
        try:
            old = set(json.load(open(work_dir() / 'etf_codes.json', encoding='utf-8')))
        except (OSError, ValueError):
            pass
        json.dump(sorted(etf | old), open(work_dir() / 'etf_codes.json', 'w', encoding='utf-8'))
    lst = api.listing()
    lst = lst[[not is_etf(t, n, etf) for t, n in zip(lst.ticker, lst.name)]].reset_index(drop=True)
    log(f'종목 목록 {len(lst):,}개 (ETF·ETN·우선주·스팩·리츠 제외)')
    lst['shares'] = _check_shares(d, lst)

    new_parts, replace = [], set()
    n_new = n_full = n_err = 0
    for i, r in enumerate(lst.itertuples(index=False), 1):
        t = r.ticker
        try:
            if t in last.index:
                s = (last[t] + pd.Timedelta(days=1)).strftime('%Y%m%d')
                if s > today:
                    continue
                df = api.daily(t, last[t].strftime('%Y%m%d'), today, max_pages=2)
                if df is None or df.empty:
                    continue
                ov = df[df.date == last[t]]
                if len(ov) and abs(float(ov.close.iloc[0]) / float(lastc[t]) - 1) > 0.003:
                    # 수정주가 변경 → 전체 재수신
                    df = api.daily(t, START.strftime('%Y%m%d'), today)
                    replace.add(t); n_full += 1
                else:
                    df = df[df.date > last[t]]
            else:
                df = api.daily(t, START.strftime('%Y%m%d'), today)
                n_new += 1
            if df is None or df.empty:
                continue
            df = df.copy()
            df['value'] = df['value'] * 1e6            # 키움 거래대금 단위: 백만원 → 원
            df['name'], df['market'] = r.name, r.market
            sh = r.shares
            df['market_cap_won'] = df['close'] * sh if sh and np.isfinite(sh) else np.nan
            df['market_cap_observed'] = df['market_cap_won'].notna().astype(int)
            df['industry_name'] = ''
            new_parts.append(df)
        except Exception as e:  # 한 종목 실패로 전체를 멈추지 않음
            n_err += 1
            log(f'  {t} {r.name} 실패: {e}')
        if i % 300 == 0:
            log(f'  {i:,}/{len(lst):,} 종목 확인')
    if not new_parts:
        log('새로 받은 시세가 없습니다(휴장일이거나 이미 최신).')
        return 0
    new = pd.concat(new_parts, ignore_index=True)
    if replace:
        keep_mc = d[d.ticker.isin(replace)][['ticker', 'date', 'market_cap_won', 'market_cap_observed']]
        d = d[~d.ticker.isin(replace)]
        new = new.merge(keep_mc, on=['ticker', 'date'], how='left', suffixes=('', '_old'))
        m = new['market_cap_won_old'].notna()
        new.loc[m, 'market_cap_won'] = new.loc[m, 'market_cap_won_old']
        new.loc[m, 'market_cap_observed'] = new.loc[m, 'market_cap_observed_old']
        new = new.drop(columns=['market_cap_won_old', 'market_cap_observed_old'])
    # 종목명·시장 최신화
    nm = lst.set_index('ticker')
    d = pd.concat([d, new], ignore_index=True)
    has = d.ticker.isin(nm.index)
    d.loc[has, 'name'] = d.loc[has, 'ticker'].map(nm['name'])
    d.loc[has, 'market'] = d.loc[has, 'ticker'].map(nm['market'])
    save_panel(d)
    log(f'시세 저장: 새 행 {len(new):,} | 신규 상장 {n_new} | 수정주가 재수신 {n_full} | 실패 {n_err} | 최종일 {d.date.max():%Y-%m-%d}')
    return len(new)


if __name__ == '__main__':
    main()
