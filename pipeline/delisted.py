"""KRX 상장폐지종목 현황(참고용) 읽기·분류.  파일: data_ref/delisted_krx.csv
열: code(6자리), name, date(폐지일), reason(폐지사유), note(비고)
이 자료에는 시세가 없습니다. 통계에는 쓰지 않고, '생존 편향' 한계 문구의 숫자와 점검용으로만 씁니다.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

REF = Path(__file__).resolve().parent / 'data_ref' / 'delisted_krx.csv'

# 순서가 중요합니다(위에서부터 먼저 맞는 것으로 분류).
RULES = [
    ('시장 이전(폐지 아님)', ('코스닥시장 이전상장', '유가증권시장 상장', '유가증권시장 이전', '코스닥시장 상장', '코스닥시장 이전')),
    ('코넥스', ('지정자문인', '코넥스')),
    ('스팩', ('스팩', '기업인수목적', '상장예비심사신청서 미제출', '합병상장예비심사', '상장예비심사 청구서 미제출')),
    ('자진 폐지(신청)', ('상장폐지 신청', '신청에 의한 상장폐지', '상장폐지신청')),
    ('합병·주식교환', ('피흡수합병', '합병', '완전자회사', '포괄적 주식교환', '포괄적주식교환')),
    ('부실·감사의견·실질심사', ('감사의견', '감사범위', '기업의 계속성', '경영의 투명성', '자본잠식', '부도', '파산', '회생', '상장적격성', '실질심사', '불성실공시', '횡령', '배임', '해산', '사업보고서', '반기보고서', '분기보고서', '매매거래정지', '주식분산', '시가총액', '거래량', '매출액')),
]


def classify(reason: str, name: str = '') -> str:
    r = str(reason or '')
    n = str(name or '')
    if '스팩' in n or '기업인수목적' in n:
        return '스팩'
    for cat, keys in RULES:
        if any(k in r for k in keys):
            return cat
    return '기타'


def load() -> pd.DataFrame | None:
    if not REF.exists():
        return None
    d = pd.read_csv(REF, dtype={'code': str}, encoding='utf-8-sig')
    d['code'] = d['code'].astype(str).str.zfill(6)
    d['date'] = pd.to_datetime(d['date'])
    d['category'] = [classify(r, n) for r, n in zip(d['reason'], d['name'])]
    return d


def summary() -> dict | None:
    d = load()
    if d is None or d.empty:
        return None
    c = d['category'].value_counts().to_dict()
    bad = d[d['category'] == '부실·감사의견·실질심사']
    return dict(n=len(d), first=f"{d['date'].min():%Y-%m-%d}", last=f"{d['date'].max():%Y-%m-%d}",
                cats=c, bad=len(bad), other=c.get('기타', 0),
                bad_years={int(k): int(v) for k, v in bad['date'].dt.year.value_counts().sort_index().items()})
