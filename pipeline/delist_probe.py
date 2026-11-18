"""키움이 상장폐지 종목의 일봉을 주는지 점검합니다(읽기만 함, 데이터 변경 없음).
결과: work\\delist_probe.txt
"""
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import kiwoom_keys, work_dir
from kiwoom_api import Kiwoom
import delisted

d = delisted.load()
out = work_dir() / 'delist_probe.txt'
L = []
def log(s):
    print(s); L.append(s)
if d is None:
    log('폐지 목록 파일이 없습니다'); out.write_text('\n'.join(L), encoding='utf-8'); sys.exit()
d = d[d['category'].isin(['부실·감사의견·실질심사', '합병·주식교환', '자진 폐지(신청)'])].copy()
d['yr'] = d['date'].dt.year
pick = []
for y, g in d.groupby('yr'):
    pick += list(g.sort_values('date').head(2).itertuples())
api = Kiwoom(*kiwoom_keys())
today = dt.date.today().strftime('%Y%m%d')
ok = no = 0
log(f'점검 {len(pick)}종목 (연도별 2개, 부실/합병/자진 폐지)')
for r in pick:
    try:
        df = api.daily(r.code, '20190101', today)
    except Exception as e:
        df = None
        log(f'{r.code} {r.name} 폐지 {r.date:%Y-%m-%d} [{r.category}] -> 오류: {str(e)[:80]}')
        no += 1
        continue
    if df is None or len(df) == 0:
        log(f'{r.code} {r.name} 폐지 {r.date:%Y-%m-%d} [{r.category}] -> 시세 없음')
        no += 1
    else:
        log(f'{r.code} {r.name} 폐지 {r.date:%Y-%m-%d} [{r.category}] -> {len(df)}행 {df.date.min():%Y-%m-%d}~{df.date.max():%Y-%m-%d}')
        ok += 1
log(f'결과: 시세 있음 {ok} / 없음·오류 {no}')
out.write_text('\n'.join(L), encoding='utf-8')
