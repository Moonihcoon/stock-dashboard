"""공유용 별도 대시보드 '상승률 200' 생성 → work/web/rank.html
기존 대시보드의 '당일 상승 200'·'상승 이유' 두 탭만 같은 템플릿에서 떼어 냅니다.
업데이트 버튼·설명 문구는 넣지 않습니다. 같은 data/·px/ 를 쓰므로 매일 같이 갱신됩니다.
"""
import re

KEEP = ['calendar', 'reasons']
head = open('web/tpl_head.html', encoding='utf-8').read()
body = open('web/tpl_body.html', encoding='utf-8').read()
js = open('web/tpl_js.js', encoding='utf-8').read()

head = head.replace('<title>급등주 대시보드</title>', '<title>상승률 200</title>\n<meta name="robots" content="noindex,nofollow">')

i0 = body.index('<div class="wrap">')
i1 = body.index('<section id="p-stats">')
top = body[i0:i1]
top = re.sub(r'<h1>.*?</h1>', '<h1>상승률 200</h1>', top, flags=re.S)
top = re.sub(r'<p class="sub">.*?</p>\n?', '', top, count=1, flags=re.S)            # 설명 문구 없음
top = re.sub(r'<a class="btn up-btn" id="upd-btn".*?</a>', '', top, flags=re.S)       # 수동 업데이트 버튼 없음
top = re.sub(r'<p class="note" id="upd-note".*?</p>', '', top, flags=re.S)
top = re.sub(r'<nav role="tablist">.*?</nav>',
             '<nav role="tablist">\n<button role="tab" data-tab="calendar" aria-selected="true">당일 상승 200</button>\n'
             '<button role="tab" data-tab="reasons" aria-selected="false">상승 이유</button>\n</nav>', top, count=1, flags=re.S)

secs = ''
for k in KEEP:
    sec = re.search(r'<section id="p-%s".*?</section>' % k, body, flags=re.S).group(0)
    sec = re.sub(r'<div class="note">.*?</div>\n?', '', sec, flags=re.S)             # 하단 설명 없음
    if k == 'reasons':
        sec = re.sub(r'<h2>.*?</h2>\n?', '', sec, flags=re.S)
        sec = re.sub(r'<p class="sub">.*?</p>\n?', '', sec, count=1, flags=re.S)
    secs += sec + '\n\n'
secs = secs.replace('<section id="p-calendar" hidden>', '<section id="p-calendar">')
page_body = top + secs + '</div>\n'

old_list = "['stats','list','stocks','screen','cand','calendar','reasons']"
assert js.count(old_list) == 2, js.count(old_list)
js = js.replace(old_list, "['calendar','reasons']")
assert ":'stats')" in js
js = js.replace(":'stats')", ":'calendar')")
js = re.sub(r"\$\('#upd-btn'\)\.addEventListener\(.*?\);\n?", '', js, flags=re.S)

page = head + page_body + '<script>' + js + '</script>'
open('web/rank.html', 'w', encoding='utf-8').write(page)
print('rank.html', len(page))
