from build_report import *
from common import last_date
LASTD = last_date()
css = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#14202e;--ink-2:#3b4a5c;--ink-3:#8793a3;--line:#dfe4ea;--blue:#2a6fdb;--orange:#e08a1e;--orange-ink:#a4600a;--red:#d6453d;--red-ink:#b3322b;--good:#1f8a5b;--soft:#eaf1fc;--warn:#fff4e0}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f151d;--panel:#171f2a;--ink:#e8edf3;--ink-2:#b4c0cd;--ink-3:#7c8a9b;--line:#273241;--blue:#6aa3ff;--orange:#f0a63f;--orange-ink:#f3b765;--red:#ff7a70;--red-ink:#ff958c;--good:#4ccf95;--soft:#1b2a40;--warn:#33281a;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f151d;--panel:#171f2a;--ink:#e8edf3;--ink-2:#b4c0cd;--ink-3:#7c8a9b;--line:#273241;--blue:#6aa3ff;--orange:#f0a63f;--orange-ink:#f3b765;--red:#ff7a70;--red-ink:#ff958c;--good:#4ccf95;--soft:#1b2a40;--warn:#33281a;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.65 'Noto Sans KR',system-ui,sans-serif;padding-inline:max(16px,env(safe-area-inset-left,0px)) max(16px,env(safe-area-inset-right,0px));padding-block:24px 64px}
.wrap{max-width:880px;margin:0 auto;display:flex;flex-direction:column;gap:28px;min-width:0}
h1{font:600 28px/1.3 'Noto Serif KR',serif;margin:0;text-wrap:balance}
h2{font:600 20px/1.35 'Noto Serif KR',serif;margin:0 0 4px;text-wrap:balance}
h3{font-size:15px;margin:18px 0 4px}
p{margin:6px 0}.mut{color:var(--ink-3)}.sub{color:var(--ink-2);margin:0}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}
.hero{background:none;border:0;padding:0}
.ans{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:12px;margin-top:14px}
.ans div{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;min-width:0}
.ans b{display:block;font:600 22px/1.3 'Noto Serif KR',serif;font-variant-numeric:tabular-nums}
.ans span{font-size:13px;color:var(--ink-2)}
.note{background:var(--warn);border-radius:8px;padding:12px 14px;font-size:14px}
.tw{overflow-x:auto;margin-top:10px;border:1px solid var(--line);border-radius:8px}
.tw.tall{max-height:520px;overflow:auto}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap;text-align:left}
td.n{text-align:right}th{background:var(--soft);font-weight:600;position:sticky;top:0}
th button{all:unset;cursor:pointer;font-weight:600}th button:focus-visible{outline:2px solid var(--blue)}
tr:last-child td{border-bottom:0}
.chart{width:100%;height:auto;display:block;margin-top:8px}
.chart .grid{stroke:var(--line);stroke-width:1}.chart .base{stroke:var(--ink-3);stroke-width:1}
.chart .ax{fill:var(--ink-2);font-size:11.5px}.chart .ax2{fill:var(--ink-3);font-size:10.5px}
.chart .vl{fill:var(--ink);font-size:12px;font-weight:600}.chart .axl{fill:var(--ink-2);font-size:11.5px;font-weight:600}
.filter{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}
.filter input{padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;min-width:0}
ul{margin:6px 0;padding-left:20px}li{margin:3px 0}
.leg{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-2);margin-top:6px}
"""
js = """
(function(){var t=document.getElementById('lst');if(!t)return;var tb=t.tBodies[0],rows=[].slice.call(tb.rows),dir={};
t.querySelectorAll('th button').forEach(function(b){b.addEventListener('click',function(){var c=+b.dataset.c;dir[c]=!dir[c];
rows.sort(function(a,z){var x=a.cells[c].dataset.v,y=z.cells[c].dataset.v,nx=parseFloat(x),ny=parseFloat(y);
var r=(!isNaN(nx)&&!isNaN(ny)&&/^-?[\\d.]+$/.test(x))?nx-ny:x.localeCompare(y,'ko');return dir[c]?r:-r});
rows.forEach(function(r){tb.appendChild(r)})})});
var f=document.getElementById('flt'),cnt=document.getElementById('cnt');
function up(){var q=f.value.trim().toLowerCase(),n=0;rows.forEach(function(r){var s=(r.cells[0].textContent+' '+r.cells[1].textContent).toLowerCase().indexOf(q)>=0;r.hidden=!s;if(s)n++});cnt.textContent=n+'개'}
f.addEventListener('input',up);up()})();
"""
exn = ex
body = f"""
<div class="wrap">
<section class="hero">
<h1>급등주 눌림·반등 통계</h1>
<p class="sub">코스피·코스닥 2020-01 ~ {LASTD[:7]}, 5거래일 내 장중 +80% 이상 &amp; 거래대금 3천억 이상 3일 이상. 일봉 기준 분석 ({n_ep}개 사례, {n_tk}개 종목).</p>
<div class="ans">
<div><b>{pc(fm,1)}</b><span>② 첫 −30% 이후 +10% 반등이 확정되는 고점 대비 중앙값 (가운데 50%: {pc(fq3,0)} ~ {pc(fq1,0)})</span></div>
<div><b>{pc(bmed,1)}</b><span>③ 직전 반등 저점을 깬 뒤 다시 +10% 반등이 나오는 추가 하락폭 중앙값 (가운데 50%: {pc(bq3,0)} ~ {pc(bq1,0)})</span></div>
<div><b>{E.repeats.mean():.1f}회</b><span>④ 고점 후 6개월 내 저점 이탈 → 재반등 반복 (사례당 평균, 중앙 {E.repeats.median():.0f}회). 반등 레그는 약 +{leg7.leg_med:.0f}~{leg1.leg_med:.0f}%</span></div>
<div><b>평단 +5%까지</b><span>⑦ 3분할(−33/−38/−43%) 후 현실적인 목표. 다음 분할 전·20일 내 도달은 단계별 약 66~83%이나 검증구간 기대수익은 거의 0 (+{cv5_out:.1f}%)</span></div>
</div>
<p class="note" style="margin-top:14px"><b>가장 중요한 제한:</b> 분봉 데이터가 없어 일봉으로 근사했습니다. 고점·저점 가격은 일봉 고가·저가로 정확하지만, 하루 안의 선후 순서는 모릅니다. 상장폐지 종목이 빠져 있어 실제보다 낙관적일 가능성이 큽니다. 자세한 내용은 맨 아래 "모르는 것"에 있습니다.</p>
</section>

<section><h2>1·5. 종목 선정과 발생 횟수</h2>
<p class="sub">조건 1을 만족한 사례를 한 구간으로 묶어(같은 급등이 이어지면 병합) 센 결과입니다.</p>
{t5}
<h3>연도별 선정 건수</h3>{ch_year}
<p class="mut">2020년과 2026년에 몰려 있습니다. 시장 전체가 과열된 시기의 사례가 많다는 뜻이고, 결과가 평상시에도 같은지는 모릅니다.</p>
</section>

<section><h2>2. 첫 반등 저점은 고점 대비 어디서 나오나</h2>
<p class="sub">고점에서 −30% 이상 하락한 뒤, 저점 대비 +10% 반등이 확인된 시점의 저점 위치. 평균 {pc(fmean,1)} (95% 구간 {pc(fmean_ci[0],1)} ~ {pc(fmean_ci[1],1)}), 중앙값 {pc(fm,1)} (95% 구간 {pc(fmed_ci[0],1)} ~ {pc(fmed_ci[1],1)}). 사례의 {share_30_40:.0f}%가 −30~−40% 안에 있습니다.</p>
{ch_first_hist}
<h3>그 깊이에 도달했을 때 반등이 확정될 확률</h3>
<p class="sub">막대 높이는 많이 머문 구간이 높게 보이는 착시가 있어, "그 구간까지 내려온 사례 중 몇 %가 거기서 반등했나"로 다시 계산했습니다. 선은 95% 신뢰구간, 속이 빈 점은 표본 10 미만입니다.</p>
{ch_first_haz}
<p class="mut">−50%까지는 확률이 완만히 오르지만 신뢰구간이 겹쳐서, 특정 깊이가 유의하게 더 좋다고 말할 수 없습니다. −30% 근처에 몰리는 것은 정의상 −30%부터 세기 때문에 일부는 구조적입니다.</p>
</section>

<section><h2>3. 저점을 깨고 내려가면 얼마나 더 빠져야 재반등하나</h2>
<p class="sub">직전 반등 저점의 저가를 하회한 뒤, 다음 +10% 반등이 확정된 저점이 직전 저점보다 얼마나 낮은지. 중앙값 {pc(bmed,1)} (95% 구간 {pc(bmed_ci[0],1)} ~ {pc(bmed_ci[1],1)}), 하위 10% 지점 {pc(bp10,1)}. 이탈한 뒤 6개월 안에 재반등이 없던 사례도 {int((E.end_reason=='broke_no_rebound').sum())}건 있습니다.</p>
{ch_brk_hist}{ch_brk_haz}
<p class="mut">이탈폭이 −25%를 넘어가면 재반등 확률이 높아지지만 표본이 작습니다. 이탈 기준은 "직전 반등 저점의 저가"입니다. 반등 확인일 저가로 바꾸면 반복 횟수가 늘어납니다(아래 민감도).</p>
</section>

<section><h2>4. 6개월 안에 몇 번 반복되고, 차수마다 얼마나 반등하나</h2>
<p class="sub">반복 횟수는 사례당 저점 이탈 후 재반등의 횟수입니다.</p>
{ch_rep}
<h3>차수별 반등 레그 상승률</h3>
<p class="sub">반등한 저점 대비, 그 저점을 다시 깨기 전까지의 최고가 상승률. 이탈이 확인된 레그만 집계했습니다(마지막 미이탈 레그는 아직 진행 중이라 크게 편향됩니다: 중앙값 +68.5%).</p>
{ch_leg}
{t_order}
<p class="mut">차수가 올라갈수록 저점은 고점 대비 더 깊어지고, 반등 폭은 24%에서 약 19%로 조금씩 줄어듭니다.</p>
</section>

<section><h2>예시: {html.escape(exn['name'])} ({exn['market']}), 상승 시작 {exn['start']:%Y-%m-%d}</h2>
<p class="sub">고점 이후 일봉 고저(회색)와 종가(파랑). 빨간 점은 반등 저점(번호는 차수), 주황 마름모는 −33/−38/−43% 분할 매수 체결. 고점 대비 %로 표시했습니다.</p>
{ch_example}
</section>

<section><h2>6. 눌림 3분할 진입 구간</h2>
<p class="sub">2번의 분포에서 가운데 50%({pc(fq3,1)} ~ {pc(fq1,1)})를 진입 구간으로 보고, 5%p 단위로 −33% / −38% / −43%에 같은 금액을 나눴습니다. 체결 비율은 1차 97.6%, 2차 96.9%, 3차 89.8%입니다.</p>
{ch_ladder}
<p>단계별 평균 단가(고점 대비): 1차 후 {pc((A1-1)*100,1)}, 2차 후 {pc((A2-1)*100,1)}, 3차 후 {pc((A3-1)*100,1)}.</p>
</section>

<section><h2>7. 평단 기준으로 기대할 수 있는 수익률</h2>
<h3>체결 단계별: 다음 분할 체결 전 또는 20일 안에 평단 대비 몇 % 올랐나</h3>
{t_stage}
<p class="mut">3차까지 체결되면 최대낙폭 중앙값이 −24%이고 20일 뒤 종가 중앙값이 −13%라서, 평단 위로 팔 기회가 있어도 손실 구간이 깊습니다.</p>
<h3>규칙을 넣어 시뮬레이션 (20일 보유, 같은 금액 3분할)</h3>
{t_dyn}
<h3>최종 체결 단계별 결과 (익절 +10%, 손절 −25%)</h3>{t_final}
<h3>검증: 전반(2020~22)에서 레벨을 정해 후반(2023~26)에 적용</h3>{t_cv}
<p class="note">전반에서 +{cv5_in:.1f}%(+5% 익절)이던 자본가중 수익이 후반에서는 +{cv5_out:.1f}%, +10% 익절은 {pc(cv10_in,1,True)}에서 {pc(cv10_out,1,True)}로 떨어졌습니다. 이 결과로는 "안정적인 수익"을 말하기 어렵습니다. 기대수익이 있다면 평단 +5% 안팎이고, 그 대가로 손실 사례는 최대 −66%(손절 없을 때)까지 갑니다.</p>
<h3>표본을 바꿔 본 결과</h3>{t_sub}
</section>

<section><h2>정의를 바꾸면 결과가 얼마나 달라지나</h2>
{t_sens}
<p class="mut">반등 기준을 +15%, +20%로 올리면 첫 저점이 더 깊어지고(−38.7%, −42.2%), 거래대금·상승률 기준은 사례 수를 크게 바꾸지만 중앙값은 −37% 안팎으로 안정적입니다.</p>
</section>

<section><h2>종목 목록 ({n_ep}개)</h2>
<p class="sub">열 제목을 누르면 정렬되고, 검색창으로 종목명을 찾을 수 있습니다. 시가총액은 상승 시작 직전 거래일 기준(억원)입니다.</p>
{t_list}
</section>

<section><h2>모르는 것과 한계</h2>
<ul>
<li><b>분봉 순서를 모릅니다.</b> 저점일과 반등일이 같은 날이면 일봉으로는 순서를 알 수 없어, 반등은 저점 다음 날부터 인정했습니다. 저점일 하루 고저폭이 10% 이상인 비율이 첫 저점 {sd_first:.0f}%, 전체 {sd_all:.0f}%입니다. 분봉으로 보면 반등이 더 빨리, 더 얕은 하락에서 잡힐 수 있습니다.</li>
<li><b>키움 분봉(ka10080)이 과거 몇 년까지 제공되는지 모릅니다.</b> 확인되면 {n_ep}개 사례만 분봉으로 다시 받아 재분석할 수 있습니다.</li>
<li><b>상장폐지 종목이 없습니다.</b> 현재 상장 종목만 있어 급등 후 폐지된 종목이 빠졌고, 눌림 매수 성과는 실제보다 좋게 나옵니다. KRX 상장폐지 목록을 주시면 보정할 수 있습니다.</li>
<li><b>고점은 사후에 압니다.</b> 실제 매매 중에는 지금이 고점인지 알 수 없습니다. 이 분석은 "고점이 지나간 뒤" 기준입니다.</li>
<li><b>시기가 몰려 있습니다.</b> 2020년과 2026년(5~6월 대형주 급등)에 사례가 많아 독립 표본이 {n_ep}개보다 적을 수 있습니다. 2026년 이후 환경이 평상시와 같은지는 모릅니다.</li>
<li><b>체결 가능성.</b> 하한가 잠김이나 얇은 호가에서는 지정가가 체결되지 않을 수 있습니다. 시뮬레이션은 일봉 가격 도달을 체결로 봤고 수수료·세금·슬리피지를 넣지 않았습니다.</li>
<li><b>업종 정보는 비어 있고</b>, 2019년 이전과 일부 구간의 시가총액은 없습니다(선정 {n_ep}개는 모두 확인됨). 추적 6개월을 채운 사례는 {n_complete}개이며, 4개는 다음 급등으로 단축, {n_incomp}개는 데이터 종료로 미완입니다.</li>
<li><b>진입 레벨은 같은 데이터에서 골랐습니다</b> (in-sample). 위 검증처럼 표본 밖에서는 성과가 약해졌습니다.</li>
</ul>
</section>
</div>
<script>{js}</script>
"""
page = f"""<title>급등주 눌림·반등 통계</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600&amp;family=Noto+Serif+KR:wght@600&amp;display=swap">
<style>{css}</style>
{body}"""
open(B+'report_v2.html','w').write(page)
print(len(page))
