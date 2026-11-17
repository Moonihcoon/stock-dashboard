"""공유용 별도 페이지 '상승률 200' 생성 → work/web/rank.html
(시장 국면 칩 · 업종 시장 지도 · 상승 이유 패널 · 타임라인 바). 기존 대시보드와 같은 data/·px/ 를 씁니다.
차트 그리기·시세 풀기 코드는 기존 tpl_js.js 에서 그대로 가져옵니다.
"""
import re

tpl = open('web/tpl_rank.html', encoding='utf-8').read()
js = open('web/tpl_js.js', encoding='utf-8').read()
head = open('web/tpl_head.html', encoding='utf-8').read()

css = re.search(r'<style>(.*?)</style>', head, flags=re.S).group(1)
lines = js.split('\n')
i_dec = next(i for i, l in enumerate(lines) if l.startswith('function decodeRun'))
i_end_chart = next(i for i, l in enumerate(lines) if "document.addEventListener('keydown'" in l and 'Escape' in l)
shared = '\n'.join(lines[:i_end_chart + 1]) + '\n' + '\n'.join(lines[i_dec:i_dec + 3])
a = js.index('const loadXlsx')
b = js.index("document.addEventListener('click',async ev=>{const b=ev.target.closest('button[data-x]')")
xl = 'let XLSXP=null;\n' + js[a:b]
assert 'function mountChart' in shared and 'function decodeRun' in shared and 'async function saveXlsx' in xl

page = tpl.replace('/*@CHART_CSS@*/', css).replace('/*@SHARED_JS@*/', shared).replace('/*@XLSX_JS@*/', xl)
open('web/rank.html', 'w', encoding='utf-8').write(page)
print('rank.html', len(page))
