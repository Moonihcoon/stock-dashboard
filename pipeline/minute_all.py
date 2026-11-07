"""전 종목 1분봉 받기 (키움 ka10080, 받을 수 있는 가장 과거부터).

- 저장: 저장소 옆 minute_all 폴더 (예: 바탕화면\\stock\\minute_all\\종목코드.parquet)
- 진행 상황: minute_all\\_progress.json  → 끊겨도 다시 실행하면 이어서 받음
- 다 받은 뒤 다시 실행하면 각 종목의 마지막 시각 이후만 이어 붙임(업데이트)
- 매일 대시보드 업데이트(run_all)가 도는 동안에는 기다렸다가 이어서 받음
- 키움은 1분봉을 종목당 최근 약 1년치만 줍니다(2026-11 기준 확인).
"""
from __future__ import annotations
import datetime, json, os, sys, time
import pandas as pd
from common import REPO, analysis_panel, kiwoom_keys, log, work_dir

OUT = REPO.parent / 'minute_all'
PROG = OUT / '_progress.json'
LOCK = work_dir() / 'running.lock'


def save_prog(p):
    tmp = str(PROG) + '.tmp'
    json.dump(p, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    os.replace(tmp, PROG)


def wait_if_busy():
    """대시보드 업데이트 중이면 끝날 때까지 대기."""
    while LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3 * 3600:
        time.sleep(60)


def keep_awake(on=True):
    """받는 동안 Windows가 절전/잠자기로 들어가지 않게 합니다(끝나면 자동 해제)."""
    try:
        import ctypes
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED  (화면은 꺼져도 PC는 깨어 있음)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception:
        pass


def main():
    from kiwoom_api import Kiwoom
    OUT.mkdir(exist_ok=True)
    me = OUT / '_running.lock'
    if me.exists() and time.time() - me.stat().st_mtime < 15 * 60:
        log('전 종목 분봉: 이미 다른 창에서 받고 있어 종료합니다.')
        return
    me.write_text(str(os.getpid()))
    keep_awake(True)
    try:
        _run(Kiwoom, me)
    finally:
        keep_awake(False)
        try:
            me.unlink()
        except OSError:
            pass


def _run(Kiwoom, me):
    p = json.load(open(PROG, encoding='utf-8')) if PROG.exists() else {}
    d = analysis_panel()
    recent = d[d['date'] >= d['date'].max() - pd.Timedelta(days=40)]
    names = recent.drop_duplicates('ticker', keep='last').set_index('ticker')['name']
    tickers = sorted(names.index)
    today = datetime.date.today().strftime('%Y%m%d')
    todo = [t for t in tickers if p.get(t, {}).get('upd') != today]
    todo.sort(key=lambda t: (t in p, t))          # 아직 한 번도 안 받은 종목 먼저
    log(f'전 종목 분봉: 대상 {len(tickers):,}종목, 이번에 받을 종목 {len(todo):,}개 → {OUT}')
    api = Kiwoom(*kiwoom_keys())
    t0 = time.time()
    for i, t in enumerate(todo, 1):
        wait_if_busy()
        me.touch()
        f = OUT / f'{t}.parquet'
        old = None
        if f.exists():
            try:
                old = pd.read_parquet(f)
            except Exception:
                old = None
        start = (old['time'].max() + pd.Timedelta(minutes=1)).strftime('%Y%m%d') if old is not None and len(old) else '20000101'
        try:
            df = api.minute(t, start, max_pages=2000)
        except Exception as e:
            log(f'  {t} {names.get(t, "")} 실패: {e}')
            time.sleep(5)
            if 'token' in str(e).lower() or '인증' in str(e):
                api = Kiwoom(*kiwoom_keys())
            continue
        if df is not None and len(df):
            if old is not None:
                df = pd.concat([old, df]).drop_duplicates('time', keep='last').sort_values('time')
            df['name'] = names.get(t, '')
            df.to_parquet(f, index=False)
            p[t] = dict(name=str(names.get(t, '')), first=str(df['time'].min()), last=str(df['time'].max()),
                        rows=int(len(df)), upd=today)
        else:
            p[t] = dict(p.get(t, {}), name=str(names.get(t, '')), upd=today, rows=p.get(t, {}).get('rows', 0))
        if i % 10 == 0 or i == len(todo):
            save_prog(p)
            el = time.time() - t0
            log(f'  {i:,}/{len(todo):,} 완료 · 경과 {el/3600:.1f}시간 · 남은 예상 {el/i*(len(todo)-i)/3600:.1f}시간')
    save_prog(p)
    rows = sum(v.get('rows', 0) for v in p.values())
    firsts = [v['first'] for v in p.values() if v.get('first')]
    log(f'전 종목 분봉 끝: {len(p):,}종목, {rows:,}행, 가장 이른 분봉 {min(firsts) if firsts else "-"}')
    (OUT / 'README.txt').write_text(
        '키움 ka10080 1분봉 (종목별 parquet)\n열: time(분, 한국시각), open, high, low, close, volume, ticker, name\n'
        '키움이 주는 범위만큼(종목당 최근 약 1년) 받았습니다. NXT(정규장 외) 체결 시간대가 포함될 수 있습니다.\n'
        '_progress.json: 종목별 첫·마지막 시각과 행 수\n', encoding='utf-8')


if __name__ == '__main__':
    main()
