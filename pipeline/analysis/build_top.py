"""별도 대시보드 'top.html' 생성: '당일 상승 200' + '상승 이유' 두 탭만.
기존 대시보드와 같은 템플릿·같은 data/·px/ 파일을 쓰므로 매일 자동으로 같이 갱신됩니다.
결과: work/web/top.html (publish 단계에서 저장소 루트로 복사 → .../stock-dashboard/top.html)
"""
import re

KEEP = ['calendar', 'reasons']
head = open('web/tpl_head.html', encoding='utf-8').read()
body = open('web/tpl_body.html', encoding='utf-8').read()
js = open('web/tpl_js.js', encoding='utf-8').read()

head = head.replace('<title>급등주 대시보드</title>', '<title>당일 상승 200 · 상승 이유</title>')

# 머리말(제목·탭·업데이트 줄)
i0 = body.index('<div class="wrap">')
i1 = body.index('<section id="p-stats">')
top = body[i0:i1]
top = re.sub(r'<h1>.*?</h1>', '<h1>당일 상승 200 · 상승 이유</h1>', top, flags=re.S)
top = re.sub(r'<p class="sub">.*?</p>', '<p class="sub">코스피·코스닥 일봉 (~ {{LAST}}). 매일 장 마감 후 자동으로 갱신됩니다. 상승 빨강, 하락 파랑. '
             '<a href="index.html">급등주 대시보드(통계 분석 등) 보기</a></p>', top, count=1, flags=re.S)
top = re.sub(r'<nav role="tablist">.*?</nav>',
             '<nav role="tablist">\n<button role="tab" data-tab="calendar" aria-selected="true">당일 상승 200</button>\n'
             '<button role="tab" data-tab="reasons" aria-selected="false">상승 이유</button>\n</nav>', top, count=1, flags=re.S)

secs = ''.join(re.search(r'<section id="p-%s".*?</section>' % k, body, flags=re.S).group(0) + '\n\n' for k in KEEP)
secs = secs.replace('<section id="p-calendar" hidden>', '<section id="p-calendar">')
page_body = top + secs + '</div>\n'

old_list = "['stats','list','stocks','screen','cand','calendar','reasons']"
assert js.count(old_list) == 2, js.count(old_list)
js = js.replace(old_list, str(KEEP).replace('"', "'").replace(' ', ''))
assert ":'stats')" in js
js = js.replace(":'stats')", ":'calendar')")

last = open('web/data/dates.json', encoding='utf-8').read().strip('[]').split(',')[-1].strip('"')
page = head + page_body.replace('{{LAST}}', last) + '<script>' + js + '</script>'
open('web/top.html', 'w', encoding='utf-8').write(page)
print('top.html', len(page))
