"""상승 이유 수집 (DART 공시 기반).

- 금융감독원 OpenDART '공시검색(list.json)'으로 전 거래일~당일에 나온 공시를 받고,
  그날 상승률 상위 200 종목의 공시만 골라 data/reasons.json 에 저장합니다.
- 공시 제목을 '공급계약 체결', '유상증자' 같은 짧은 이유로 바꾸고 중요도 순으로 정렬합니다.
- 테마·정책 수혜·루머처럼 공시 없이 오른 종목은 비어 있습니다.
설정: dashboard_config.ini 의 [dart] api_key
"""
from __future__ import annotations
import datetime, json, os, re, time, urllib.parse, urllib.request
from common import REPO, opt, log, work_dir

API = 'https://opendart.fss.or.kr/api/list.json'
RULES = [  # (정규식, 이유, 중요도: 작을수록 중요)
    (r'조회공시|풍문', '조회공시 답변(급등 사유)', 1),
    (r'단일판매|공급계약', '공급계약 체결', 2),
    (r'투자판단관련주요경영사항', '주요 경영사항(임상·기술 등)', 2),
    (r'기술이전|라이선스|기술도입', '기술이전 계약', 2),
    (r'최대주주변경|경영권', '최대주주·경영권 변경', 2),
    (r'합병|분할|영업양수|영업양도|자산양수|타법인주식및출자증권양수|공개매수', '합병·인수', 2),
    (r'무상증자', '무상증자', 3),
    (r'유상증자', '유상증자', 3),
    (r'전환사채|신주인수권부사채|교환사채', '전환사채 등 발행', 4),
    (r'자기주식취득|자사주|주식소각', '자사주 취득·소각', 3),
    (r'현금ㆍ현물배당|현금배당|배당', '배당 결정', 4),
    (r'영업\(잠정\)실적|매출액또는손익구조|실적', '실적 발표', 3),
    (r'신규시설투자|시설투자', '신규 시설투자', 3),
    (r'특허', '특허 취득', 3),
    (r'수주', '수주', 2),
    (r'기업설명회|IR', 'IR 개최', 5),
    (r'소송', '소송', 5),
    (r'주식등의대량보유', '대량보유 변동', 6),
]
SKIP = re.compile(r'임원ㆍ주요주주특정증권등소유상황보고서|증권발행실적보고서|투자설명서|일괄신고|기업지배구조|감사보고서|사업보고서|반기보고서|분기보고서')


def classify(title: str):
    t = re.sub(r'^\[[^\]]*\]\s*', '', title).replace(' ', '')
    if SKIP.search(t):
        return None
    for pat, lab, pr in RULES:
        if re.search(pat, t):
            return lab, pr
    return '기타 공시', 7


def fetch(key, bgn, end):
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode(dict(crtfc_key=key, bgn_de=bgn, end_de=end, page_no=page, page_count=100))
        for k in range(4):
            try:
                with urllib.request.urlopen(f'{API}?{q}', timeout=30) as r:
                    j = json.loads(r.read().decode('utf-8'))
                break
            except Exception:
                time.sleep(2 * (k + 1))
        else:
            raise RuntimeError('DART 응답 없음')
        st = j.get('status')
        if st == '013':
            return out
        if st != '000':
            raise RuntimeError(f"DART 오류 {st}: {j.get('message')}")
        out.extend(j.get('list') or [])
        if page >= int(j.get('total_page') or 1):
            return out
        page += 1
        time.sleep(0.1)


def main():
    key = opt('dart', 'api_key')
    if not key:
        log('DART 키가 없어 상승 이유 수집을 건너뜁니다(설정 파일 [dart] api_key).')
        return
    data = REPO / 'data'
    dates = json.load(open(data / 'dates.json', encoding='utf-8'))
    tick = json.load(open(data / 'tick.json', encoding='utf-8'))
    jp = data / 'reasons.json'
    old = []
    try:
        old = json.load(open(jp, encoding='utf-8'))
        old = [x for x in old if x.get('s') == 'DART']       # 예전 네이버 형식은 버림
    except (OSError, ValueError):
        pass
    days_keep = int(opt('dart', 'days_keep', '90') or 90)
    n_days = int(opt('dart', 'fetch_days', '5') or 5) if old else int(opt('dart', 'first_days', '40') or 40)
    targets = list(range(max(1, len(dates) - n_days), len(dates)))
    tops = {}
    new = []
    for di in targets:
        d, p = dates[di], dates[di - 1]
        ym = d[:7]
        if ym not in tops:
            try:
                tops[ym] = json.load(open(data / 'top' / f'{ym}.json', encoding='utf-8'))
            except OSError:
                tops[ym] = {}
        rows = tops[ym].get(str(di)) or []
        code2 = {tick[r[0]][0]: (tick[r[0]][1], r[1]) for r in rows}
        if not code2:
            continue
        lst = fetch(key, p.replace('-', ''), d.replace('-', ''))
        for it in lst:
            c = (it.get('stock_code') or '').strip()
            if c not in code2:
                continue
            cl = classify(it.get('report_nm', ''))
            if not cl:
                continue
            rd = it.get('rcept_dt', '')
            new.append(dict(d=d, t=f'{rd[4:6]}-{rd[6:8]}', n=code2[c][0], r=cl[0], p=cl[1],
                            h=re.sub(r'\s+', ' ', it.get('report_nm', '')).strip(),
                            u=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it.get('rcept_no')}",
                            s='DART', dir='up'))
        time.sleep(0.2)
    seen = {(x['u'], x['d'], x['n']) for x in old}
    add = [x for x in new if (x['u'], x['d'], x['n']) not in seen]
    allr = old + add
    cut = (datetime.date.today() - datetime.timedelta(days=days_keep)).isoformat()
    allr = [x for x in allr if x['d'] >= cut]
    allr.sort(key=lambda x: (x['d'], -x.get('p', 9), x['t']), reverse=True)
    tmp = str(jp) + '.tmp'
    json.dump(allr, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, jp)
    hit = len({(x['d'], x['n']) for x in allr if x['d'] in {dates[i] for i in targets}})
    log(f'상승 이유(DART): {len(targets)}거래일 확인, 새 공시 {len(add)}건, 공시가 있는 상위200 종목·일 {hit}건')
    try:
        import openpyxl  # noqa
        import pandas as pd
        pd.DataFrame(allr).rename(columns=dict(d='날짜', n='종목명', r='이유', h='공시 제목', u='링크', t='공시일')) \
            [['날짜', '종목명', '이유', '공시 제목', '공시일', '링크']].to_excel(work_dir() / '상승이유_DART.xlsx', index=False)
    except Exception:
        pass


if __name__ == '__main__':
    main()
