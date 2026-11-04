"""ETF·ETN·우선주 판별 (상위 200 목록과 분석 대상에서 제외할 때 사용)."""
import re

ETF_BRANDS = {
    'KODEX', 'TIGER', 'RISE', 'KBSTAR', 'ACE', 'KINDEX', 'PLUS', 'ARIRANG', 'SOL', 'KIWOOM', 'KOSEF',
    'HANARO', 'TIME', 'TIMEFOLIO', 'WON', 'WOORI', 'KoAct', '에셋플러스', '1Q', '파워', 'UNICORN', 'BNK',
    'MIDAS', 'TREX', '마이티', 'FOCUS', 'DAISHIN', 'TRUSTON', 'N2', 'IBK', 'KCGI', 'VITA', '히어로즈',
    'HK', 'ITF', 'KTOP', 'SMART', 'QV', 'TRUE', '마이다스', '흥국', 'HANA', 'NH-Amundi', 'WISE',
}
_ETN = re.compile(r'ETN')


def is_etf(code: str, name: str, etf_codes=frozenset()) -> bool:
    if code in etf_codes:
        return True
    name = str(name or '')
    if _ETN.search(name):
        return True
    first = name.split(' ')[0]
    return first in ETF_BRANDS and ' ' in name


def is_pref(code: str, name: str = '') -> bool:
    """우선주: 종목코드 끝자리가 0이 아님(5·7·9·K·L 등)."""
    code = str(code)
    return len(code) == 6 and code[-1] != '0'


def excluded(code, name, etf_codes=frozenset()) -> bool:
    return is_pref(code, name) or is_etf(code, name, etf_codes)
