"""조건(급등) 종목의 1분봉을 키움 ka10080으로 받아 보관합니다.

- 대상: 분석에서 뽑힌 급등 종목(에피소드). 처음에는 급등 시작일부터 거슬러 받아 보고,
  이후에는 마지막 저장 시각 다음부터 이어 받습니다.
- 키움이 과거 몇 년치 분봉을 주는지는 확인되지 않았습니다. 실제로 받은 가장 이른 시각을
  work/minute_depth.json 에 적어 두니, 처음 실행 후 이 파일로 깊이를 확인하세요.
- 통계 분석은 아직 일봉 기준입니다(분봉이 2020년까지 다 받아지는지 확인된 뒤 바꿀 수 있음).
"""
from __future__ import annotations
import json
import pandas as pd
from common import opt, kiwoom_keys, log, work_dir


def _rw(path):
    try:
        return pd.read_parquet(path) if path.suffix == '.parquet' else pd.read_pickle(path)
    except Exception:
        return None


def main(api=None, max_tickers: int = 60):
    if opt('options', 'minute', 'yes').lower() not in ('yes', 'y', '1', 'true'):
        log('분봉 수집 꺼짐(config.ini options.minute)')
        return
    E = work_dir() / 'E_v2.pkl'
    if not E.exists():
        log('분봉: 분석 결과가 아직 없어 건너뜁니다.')
        return
    E = pd.read_pickle(E)
    if api is None:
        from kiwoom_api import Kiwoom
        api = Kiwoom(*kiwoom_keys())
    try:
        import pyarrow  # noqa
        ext = '.parquet'
    except ImportError:
        ext = '.pkl'
    md = work_dir() / 'minute'; md.mkdir(exist_ok=True)
    dp = work_dir() / 'minute_depth.json'
    depth = json.load(open(dp, encoding='utf-8')) if dp.exists() else {}
    # 최근 급등부터 우선
    tk = E.sort_values('start_date', ascending=False).drop_duplicates('ticker')
    done = 0
    for r in tk.itertuples():
        if done >= max_tickers:
            break
        f = md / f'{r.ticker}{ext}'
        old = _rw(f) if f.exists() else None
        if old is not None and len(old):
            start = (old.time.max() + pd.Timedelta(minutes=1)).strftime('%Y%m%d')
        else:
            start = (pd.Timestamp(r.start_date) - pd.Timedelta(days=10)).strftime('%Y%m%d')
        try:
            df = api.minute(r.ticker, start)
        except Exception as e:
            log(f'  분봉 {r.ticker} {r.name} 실패: {e}')
            continue
        done += 1
        if df is None or df.empty:
            depth.setdefault(r.ticker, {'name': r.name, 'first': None, 'want': start})
            continue
        if old is not None:
            df = pd.concat([old, df]).drop_duplicates('time', keep='last').sort_values('time')
        (df.to_parquet(f, index=False) if ext == '.parquet' else df.to_pickle(f))
        depth[r.ticker] = {'name': r.name, 'first': str(df.time.min()), 'last': str(df.time.max()),
                           'want_from': str(pd.Timestamp(r.start_date).date()), 'rows': int(len(df))}
    json.dump(depth, open(dp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    got = [v for v in depth.values() if v.get('first')]
    if got:
        log(f'분봉: {len(got)}종목 보관, 가장 이른 분봉 {min(v["first"] for v in got)}')


if __name__ == '__main__':
    main()
