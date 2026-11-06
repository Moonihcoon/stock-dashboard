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
        log('DART 키가 없어 공시는 건너뛰고 뉴스만 모읍니다(설정 파일 [dart] api_key).')
    data = REPO / 'data'
    dates = json.load(open(data / 'dates.json', encoding='utf-8'))
    tick = json.load(open(data / 'tick.json', encoding='utf-8'))
    jp = data / 'reasons.json'
    old = []
    try:
        old = json.load(open(jp, encoding='utf-8'))
        old = [x for x in old if x.get('s') == 'DART' or 'p' in x]   # 예전 네이버 형식은 버림
    except (OSError, ValueError):
        pass
    days_keep = int(opt('dart', 'days_keep', '90') or 90)
    n_days = int(opt('dart', 'fetch_days', '5') or 5) if old else int(opt('dart', 'first_days', '40') or 40)
    targets = list(range(max(1, len(dates) - n_days), len(dates)))
    tops = {}
    for di in range(max(1, len(dates) - max(n_days, 10)), len(dates)):
        ym = dates[di][:7]
        if ym not in tops:
            try:
                tops[ym] = json.load(open(data / 'top' / f'{ym}.json', encoding='utf-8'))
            except OSError:
                tops[ym] = {}
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
        if not key:
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
    # 뉴스(구글 뉴스 RSS) — 키 필요 없음. 이미 뉴스가 있는 종목·일은 건너뜀
    if opt('news', 'enabled', 'yes').lower() in ('yes', 'y', '1', 'true'):
        nd = int(opt('news', 'days', '3') or 3)
        have = {(x['d'], x['n']) for x in old if x.get('s') != 'DART'}
        ntg = list(range(max(1, len(dates) - nd), len(dates)))
        nrows, _ = collect_news(dates, tick, tops, ntg, have)
        new += nrows
        log(f'뉴스: 새 기사 {len(nrows)}건')
    seen = {(x['u'], x['d'], x['n']) for x in old}
    add = [x for x in new if (x['u'], x['d'], x['n']) not in seen]
    allr = old + add
    cut = (datetime.date.today() - datetime.timedelta(days=days_keep)).isoformat()
    allr = [x for x in allr if x['d'] >= cut]
    allr.sort(key=lambda x: (x['d'], -x.get('p', 9), x['t']), reverse=True)
    tmp = str(jp) + '.tmp'
    json.dump(allr, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, jp)
    tdays = sorted({x['d'] for x in allr if x.get('s') != 'DART'})
    th = build_themes(allr, tdays)
    json.dump(th, open(data / 'themes.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    if tdays:
        log(f"테마({tdays[-1]}): " + ', '.join(f'{k}({v})' for k, v in th[tdays[-1]]['top'][:6]))
    hit = len({(x['d'], x['n']) for x in allr if x['d'] in {dates[i] for i in targets}})
    log(f'상승 이유(DART): {len(targets)}거래일 확인, 새 공시 {len(add)}건, 공시가 있는 상위200 종목·일 {hit}건')
    try:
        import openpyxl  # noqa
        import pandas as pd
        pd.DataFrame(allr).rename(columns=dict(d='날짜', n='종목명', r='이유', h='공시 제목', u='링크', t='공시일')) \
            [['날짜', '종목명', '이유', '공시 제목', '공시일', '링크']].to_excel(work_dir() / '상승이유_DART.xlsx', index=False)
    except Exception:
        pass


# ------------------------------------------------------------------ 구글 뉴스 RSS
import email.utils, html as _html, xml.etree.ElementTree as ET
UPW = ('특징주', '급등', '상한가', '강세', '상승', '신고가', '껑충', '급반등', '돌파', '수혜')
DNW = ('하락', '급락', '약세', '하한가', '신저가', '폭락')
STOP = set('특징주 상승 급등 강세 상한가 주가 기대감 소식 관련 투자 시장 코스피 코스닥 증시 오늘 마감 장중 거래 신고가 외국인 기관 개인 매수 매도 실적 발표 전망 이유 영향 효과 종목 기업 국내 글로벌 한국 미국 중국 회사 대표 개장 오전 오후 대비 약세 하락 급락 반등 돌파 지속 연속 최고 사상 주식 증권 리포트 목표가 상향 하향 우려 계약 체결 공시 확대 추진 예정 가능성 공급 소폭 대거 일제히 동반 주목 관심 기록 이틀째 사흘째 나흘째 연일 장초반 장마감 시간외 거래량 거래대금 관련주 테마주 테마 수혜주 수혜 껑충 훨훨 들썩 질주 쑥 뚝'.split())


def _kst(dt):
    return dt.astimezone(datetime.timezone(datetime.timedelta(hours=9))).replace(tzinfo=None)


def gnews(name, day_from, day_to):
    """day_from~day_to(YYYY-MM-DD) 사이 '종목명' 뉴스 제목 목록."""
    to1 = (datetime.date.fromisoformat(day_to) + datetime.timedelta(days=1)).isoformat()
    q = urllib.parse.quote(f'"{name}" after:{day_from} before:{to1}')
    url = f'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (stock-dashboard)'})
    for k in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                root = ET.fromstring(r.read())
            break
        except Exception:
            time.sleep(3 * (k + 1))
    else:
        return None
    out = []
    for it in root.iter('item'):
        t = _html.unescape(it.findtext('title') or '').strip()
        src = (it.findtext('source') or '').strip()
        if src and t.endswith(' - ' + src):
            t = t[:-len(src) - 3].strip()
        try:
            pub = _kst(email.utils.parsedate_to_datetime(it.findtext('pubDate')))
        except Exception:
            continue
        out.append(dict(t=t, u=(it.findtext('link') or '').strip(), s=src or '뉴스', pub=pub))
    return out


def news_reason(t, name):
    r = re.sub(r'^\s*[\[【(][^\]】)]{1,12}[\]】)]\s*', '', t)
    r = r.replace(name, '', 1)
    r = re.sub(r'^[\s,·…\-–—:\'\"“”‘’]+', '', r).strip()
    return r[:100] or t[:100]


THEMES = {  # 테마 이름: 제목에서 찾을 단어들
    'AI': ['AI', '인공지능', '생성형', 'LLM', '챗GPT', 'GPT'], '반도체': ['반도체', 'HBM', '파운드리', '웨이퍼', '유리기판', 'D램', '낸드'],
    '2차전지': ['2차전지', '이차전지', '배터리', '양극재', '음극재', '전고체', '리튬'], '원전': ['원전', '원자력', 'SMR', '소형모듈원자로'],
    '로봇': ['로봇', '휴머노이드'], '방산': ['방산', 'K-방산', '미사일', '전투기', '방위산업'], '조선': ['조선', 'LNG선', '선박', 'MASGA'],
    '우주항공': ['우주', '위성', '발사체', '항공우주', 'UAM', '드론'], '양자': ['양자'], '수소': ['수소', '연료전지'],
    '바이오': ['바이오', '신약', '임상', '기술이전', '항암', 'ADC', '비만', 'GLP'], '의료기기': ['의료기기', '진단', '미용', '보톡스'],
    '게임': ['게임', '신작'], '엔터': ['엔터', 'K팝', '아이돌', '콘서트', '드라마', '웹툰'], '화장품': ['화장품', 'K뷰티', '뷰티'],
    '정보보안': ['보안', '해킹', '정보보안', '사이버'], '전력·전선': ['전력', '전선', '변압기', '전력기기', '송전', 'ESS'],
    '데이터센터': ['데이터센터', '클라우드', '냉각'], '통신': ['5G', '6G', '통신장비'], '자율주행·전기차': ['자율주행', '전기차', '자동차부품'],
    '가상자산': ['비트코인', '가상자산', '코인', '스테이블코인', '블록체인', 'STO'], '대북·남북경협': ['대북', '남북', '북한', '경협'],
    '건설·인프라': ['건설', '재건', '인프라', 'SOC'], '태양광·풍력': ['태양광', '풍력', '신재생'], '철강·소재': ['철강', '희토류', '구리', '니켈', '알루미늄'],
    '초전도체': ['초전도'], '정치테마': ['대선', '테마주', '정치'], '음식료': ['음식료', '라면', '식품', '불닭'], '여행·항공': ['여행', '항공', '면세'],
    '해운': ['해운', '운임'], '디스플레이': ['디스플레이', 'OLED', '마이크로LED'], '스마트폰': ['스마트폰', '폴더블', '아이폰'],
    '중국 소비': ['중국 소비', '한한령', '중국 관광'], '저PBR·밸류업': ['밸류업', '저PBR', '자사주 소각', '주주환원'],
}
_TK = [(th, k) for th, ks in THEMES.items() for k in ks]


def words(t, name):
    """제목에서 테마 이름 집합: 사전에 있는 단어 + '○○ 관련주/테마/수혜' 형태."""
    t = t.replace(name, ' ')
    found = {th for th, k in _TK if (k in t if not re.fullmatch(r'[A-Za-z0-9]+', k) else re.search(r'(?<![A-Za-z])' + re.escape(k) + r'(?![A-Za-z])', t))}
    cue = {w for w in re.findall(r'([가-힣A-Za-z0-9]{2,8})\s*(?:관련주|테마주|테마|수혜주)', t) if w not in STOP}
    return cue, found


def collect_news(dates, tick, tops, targets, have):
    """targets(거래일 인덱스)마다 상위 200 종목 뉴스 → (reason rows, themes)."""
    rows, themes = [], {}
    names_all = {n for _, n, _ in tick}
    for di in targets:
        d, p = dates[di], dates[di - 1]
        top = tops.get(d[:7], {}).get(str(di)) or []
        if not top:
            continue
        lo = datetime.datetime.fromisoformat(p + 'T15:30:00')
        hi = datetime.datetime.fromisoformat(d + 'T23:59:59')
        for r in top:
            nm = tick[r[0]][1]
            if (d, nm) in have:
                continue
            got = gnews(nm, p, d)
            time.sleep(0.6)
            if got is None:
                log(f'  뉴스 조회 실패({nm}), 이 날은 여기까지만 받습니다.')
                break
            got = [g for g in got if lo <= g['pub'] <= hi and nm in g['t']]
            if not got:
                continue
            def score(g):
                up = any(w in g['t'] for w in UPW); dn = any(w in g['t'] for w in DNW)
                return (('특징주' in g['t']), up and not dn, g['pub'])
            got.sort(key=score, reverse=True)
            for g in got[:3]:
                up = any(w in g['t'] for w in UPW); dn = any(w in g['t'] for w in DNW)
                rows.append(dict(d=d, t=g['pub'].strftime('%m-%d %H:%M'), n=nm, r=news_reason(g['t'], nm),
                                 p=2 if ('특징주' in g['t'] or (up and not dn)) else 5,
                                 h=g['t'], u=g['u'], s=g['s'], dir='down' if dn and not up else 'up'))
    return rows, {}



def build_themes(rows, days):
    """저장된 뉴스 제목으로 날짜별 테마를 다시 계산."""
    out = {}
    for d in days:
        per = {}
        for x in rows:
            if x['d'] == d and x.get('s') != 'DART':
                per.setdefault(x['n'], []).append(x.get('h', ''))
        cnt, cue_cnt, own = {}, {}, {}
        for nm, ts in per.items():
            cs, ws = set(), set()
            for t in ts:
                c, w = words(t, nm)
                cs |= c; ws |= w
            own[nm] = (cs, ws)
            for w in ws: cnt[w] = cnt.get(w, 0) + 1
            for w in cs: cue_cnt[w] = cue_cnt.get(w, 0) + 1
        score = {w: c for w, c in cnt.items() if c >= 2}
        score.update({w: c for w, c in cue_cnt.items() if c >= 3 and w not in score})
        tmap = {}
        for nm, (cs, ws) in own.items():
            cand = [w for w in (ws | cs) if w in score]
            if cand:
                tmap[nm] = max(cand, key=lambda w: (w in ws, score[w]))
        tops = {}
        for v in tmap.values():
            tops[v] = tops.get(v, 0) + 1
        out[d] = dict(top=[[k, v] for k, v in sorted(tops.items(), key=lambda x: -x[1]) if v >= 2][:10], map=tmap)
    return out


if __name__ == '__main__':
    main()
