"""공통 설정: 폴더 위치, config.ini 읽기, 시세 패널 읽기/쓰기."""
from __future__ import annotations
import configparser, os, sys, json, time
from pathlib import Path
import numpy as np
import pandas as pd

PIPE = Path(__file__).resolve().parent          # .../stock-dashboard/pipeline
REPO = PIPE.parent                               # GitHub 저장소 폴더(= 웹사이트 루트)
START = pd.Timestamp('2019-07-01')               # 2020년 분석에 필요한 직전 구간부터 보관


def cfg() -> configparser.ConfigParser:
    c = configparser.ConfigParser()
    for p in (config_path(), PIPE / 'config.ini'):
        if p.exists():
            c.read(p, encoding='utf-8-sig')
            break
    return c


def config_path() -> Path:
    """설정 파일은 저장소 바깥(예: C:\\stock\\dashboard_config.ini)에 둡니다. GitHub에 올라가지 않게."""
    return REPO.parent / 'dashboard_config.ini'


def opt(section, key, default=''):
    c = cfg()
    v = os.environ.get(f'{section}_{key}'.upper())
    if v:
        return v
    return c.get(section, key, fallback=default).strip()


def work_dir() -> Path:
    w = opt('paths', 'work', '') or '../../work'   # 기본: 저장소 바깥 폴더 (예: C:\\stock\\work)
    p = Path(w)
    if not p.is_absolute():
        p = (PIPE / p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def log(*a):
    s = time.strftime('%H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
    print(s, flush=True)
    try:
        with open(work_dir() / 'log.txt', 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d ') + s + '\n')
    except OSError:
        pass


def _has_parquet():
    try:
        import pyarrow  # noqa
        return True
    except ImportError:
        return False


def panel_path() -> Path:
    return work_dir() / ('panel.parquet' if _has_parquet() else 'panel.pkl')


COLS = ['date', 'open', 'high', 'low', 'close', 'volume', 'value', 'ticker', 'name', 'market',
        'market_cap_won', 'industry_name', 'market_cap_observed']
_PANEL = None


def _fix(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d['date'] = pd.to_datetime(d['date']).astype('datetime64[ns]')
    d['ticker'] = d['ticker'].astype(str).str.zfill(6)
    for c in COLS:
        if c not in d.columns:
            d[c] = 0 if c == 'market_cap_observed' else (pd.NA if c != 'industry_name' else '')
    d = d[COLS]
    d = d[d['date'] >= START]
    # 거래대금 단위 통일: 키움 원본(백만원)으로 남아 있는 행은 원으로 바꿉니다.
    cv = d['close'].astype(float) * d['volume'].astype(float)
    r = d['value'].astype(float) * 1e6 / cv.where(cv > 0)
    m = r.between(0.2, 5)
    if m.any():
        d.loc[m, 'value'] = d.loc[m, 'value'].astype(float) * 1e6
    return d.sort_values(['ticker', 'date']).drop_duplicates(['ticker', 'date'], keep='last').reset_index(drop=True)


def load_panel(refresh=False) -> pd.DataFrame:
    """분석 스크립트가 쓰는 전체 시세 패널. 한 번 읽으면 메모리에 보관합니다."""
    global _PANEL, _AP
    if refresh:
        _AP = None
    if _PANEL is not None and not refresh:
        return _PANEL
    p = panel_path()
    if not p.exists():
        base = opt('paths', 'base_file', 'panel_kiwoom_marketcap.parquet')
        cands = [Path(base), work_dir() / base, PIPE / base, REPO.parent / base]
        src = next((c for c in cands if c.exists()), None)
        if src is None:
            raise FileNotFoundError(
                f'시세 파일이 없습니다. {work_dir()} 폴더에 {Path(base).name} 를 넣어 주세요.')
        log('처음 실행: 기존 파일을 가져옵니다 ->', src)
        d = pd.read_parquet(src) if src.suffix == '.parquet' else pd.read_pickle(src)
        _PANEL = _fix(d)
        save_panel(_PANEL)
    else:
        _PANEL = _fix(pd.read_parquet(p) if p.suffix == '.parquet' else pd.read_pickle(p))
    return _PANEL


def save_panel(d: pd.DataFrame):
    global _PANEL
    d = _fix(d)
    p = panel_path()
    tmp = p.with_suffix(p.suffix + '.tmp')
    if p.suffix == '.parquet':
        d.to_parquet(tmp, index=False)
    else:
        d.to_pickle(tmp)
    os.replace(tmp, p)
    _PANEL = d


def etf_codes() -> set:
    p = work_dir() / 'etf_codes.json'
    try:
        return set(json.load(open(p, encoding='utf-8')))
    except (OSError, ValueError):
        return set()


_AP = None


def analysis_panel() -> pd.DataFrame:
    """분석용 패널: ETF·ETN·우선주 제외."""
    global _AP
    if _AP is None:
        from classify import excluded
        d = load_panel()
        ec = etf_codes()
        nm = d.drop_duplicates('ticker', keep='last')
        bad = {t for t, n in zip(nm.ticker, nm.name) if excluded(t, n, ec)}
        _AP = apply_minute(d[~d.ticker.isin(bad)].reset_index(drop=True))
    return _AP


def apply_minute(d: pd.DataFrame) -> pd.DataFrame:
    """분봉이 있는 날은 정규장(09:00~15:30) 분봉으로 고가·저가·종가를 잡고,
    같은 날 안의 순서 정보(hpre·hpost·lpost)를 붙입니다. 분봉이 없는 날은 일봉 그대로(빈칸).
    설정 [stats] minute = no 이면 쓰지 않습니다."""
    f = work_dir() / 'minute_daily.parquet'
    for c in ('hpre', 'hpost', 'lpost'):
        d[c] = np.nan
    if opt('stats', 'minute', 'yes').lower() in ('no', '0', 'false') or not f.exists():
        return d
    m = pd.read_parquet(f)
    m['date'] = pd.to_datetime(m['date'])
    x = d[['ticker', 'date', 'high', 'low', 'close']].merge(m, on=['ticker', 'date'], how='left')
    # 분봉은 받은 날 기준 수정주가라 그 뒤 액면분할 등이 있으면 일봉과 배율이 다름 → 종가 비율로 맞춤
    r = (x['close'] / x['mc']).where(x['mc'] > 0)
    sc = r.where((r - 1).abs() > 0.005, 1.0)
    for c in ('mh', 'ml', 'mc', 'hpre', 'hpost', 'lpost'):
        x[c] = x[c] * sc
    ok = (x['nbars'] >= 60) & ((x['mh'] / x['high'] - 1).abs() <= 0.03) & ((x['ml'] / x['low'] - 1).abs() <= 0.03)
    ok = ok.fillna(False).to_numpy()
    n_ok = int(ok.sum())
    if n_ok:
        for c in ('high', 'low', 'close'):
            d[c] = d[c].astype(float)
        ch = lambda a, b: int((ok & (np.abs(x[a].to_numpy(float) / d[b].to_numpy(float) - 1) > 1e-9)).sum())
        nh, nl, nc = ch('mh', 'high'), ch('ml', 'low'), ch('mc', 'close')
        d.loc[ok, 'high'] = x.loc[ok, 'mh'].to_numpy()
        d.loc[ok, 'low'] = x.loc[ok, 'ml'].to_numpy()
        d.loc[ok, 'close'] = x.loc[ok, 'mc'].to_numpy()
        for c in ('hpre', 'hpost', 'lpost'):
            d.loc[ok, c] = x.loc[ok, c].to_numpy()
        dd = d.loc[ok, 'date']
        log(f'통계에 분봉 반영: {n_ok:,}일({d.loc[ok, "ticker"].nunique():,}종목, {dd.min():%Y-%m-%d}~{dd.max():%Y-%m-%d}) · '
            f'일봉과 다른 값 고가 {nh:,} / 저가 {nl:,} / 종가 {nc:,}일 · 분봉 있으나 제외 {int(x["mh"].notna().sum()) - n_ok:,}일')
    return d


def last_date() -> str:
    return str(load_panel()['date'].max().date())


def kiwoom_keys():
    """config.ini 의 app_key/app_secret, 또는 키가 적힌 텍스트 파일 경로(app_key_file/app_secret_file)."""
    def one(k):
        v = opt('kiwoom', k)
        if v:
            return v
        f = opt('kiwoom', k + '_file')
        if f and Path(f).exists():
            return Path(f).read_text(encoding='utf-8-sig', errors='ignore').strip().split()[0]
        return ''
    return one('app_key'), one('app_secret')
