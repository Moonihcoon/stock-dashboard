import pickle, html
import pandas as pd, numpy as np
from build_html import *          # build_report 변수 + js(목록 정렬 스크립트)
d3 = pickle.load(open('R3.pkl', 'rb')); R3 = d3['R']
O = pd.read_pickle('G9.pkl')
res6 = R3['res6']; dur = R3['dur']; stg = R3['stage']; dyn = R3['dyn']
GN = {1: '1차 하락(고점 기준)', 2: '2차(1차 저점 이탈 후)', 3: '3차', 4: '4차 이상', 'all2': '2차 이상 전체'}
def rg(m, a, b, d=0): return f'{m:.{d}f}<span class="mut"> ({a:.{d}f}~{b:.{d}f})</span>'

# ---- 5번 표 (차수별 기간·반등률)
rows5 = []
for _, r in dur.iterrows():
    rows5.append([f'{int(r.o)}차' if r.o < 7 else '7차 이상', f'{int(r.n)}',
        pc(r.dep_med, 1) if r.dep_med == r.dep_med else '–',
        rg(r.decl_med, r.decl_p25, r.decl_p75) + '일', rg(r.up_med, r.up_p25, r.up_p75) + '일',
        rg(r.brk_med, r.brk_p25, r.brk_p75) + '일', rg(r.cyc_med, r.cyc_p25, r.cyc_p75) + '일',
        f'{pc(r.leg_med,1)} <span class="mut">({pc(r.leg_p25,0)}~{pc(r.leg_p75,0)})</span>'])
t5b = table(['차수', '저점 수', '직전 저점 이탈폭(중앙)', '하락 기간¹', '반등 최고점까지', '저점→이탈까지', '저점→다음 저점²', '반등 상승률(저점 대비)'], rows5)
# ---- 6번
v = res6
t6 = table(['기준 (고점 대비 하락 / 반등 기준)', '도달한 사례', '반등 없이 도달한 사례', '비율'], [
    ['<b>−50% 하락 / +20% 반등 (질문 기준)</b>', f'{v["reach_ep"]}건 ({v["reach_tk"]}종목)', f'<b>{v["norb_ep"]}건 ({v["norb_tk"]}종목)</b>', f'{v["norb_ep"]/v["reach_ep"]*100:.1f}%'],
    ['−50% 하락 / +15% 반등', f'{v["v_50_15"][0]}건', f'{v["v_50_15"][1]}건', f'{v["v_50_15"][1]/v["v_50_15"][0]*100:.1f}%'],
    ['−50% 하락 / +30% 반등', f'{v["v_50_30"][0]}건', f'{v["v_50_30"][1]}건', f'{v["v_50_30"][1]/v["v_50_30"][0]*100:.1f}%'],
    ['−40% 하락 / +20% 반등', f'{v["v_40_20"][0]}건', f'{v["v_40_20"][1]}건', f'{v["v_40_20"][1]/v["v_40_20"][0]*100:.1f}%'],
    ['−60% 하락 / +20% 반등', f'{v["v_60_20"][0]}건', f'{v["v_60_20"][1]}건', f'{v["v_60_20"][1]/v["v_60_20"][0]*100:.1f}%']])
names6 = ', '.join(html.escape(x) for x in R3['i6_names'])
# ---- 8번 표
def stage_tab(w):
    rr = []
    for g in (1, 2, 3, 4, 'all2'):
        for s in (1, 2, 3):
            x = stg[(stg.grp == g) & (stg.w == w) & (stg.stage == s)]
            if x.empty: continue
            x = x.iloc[0]
            rr.append([GN[g] if s == 1 else '', f'{s}차 매수', f'{int(x.fill)}/{int(x.n_legs)}', pc(x.avg_dd, 1),
                f'{x.h5:.0f}%', f'{x.h10:.0f}%', f'{x.h15:.0f}%', f'{x.h20:.0f}%', pc(x.mfe, 1), pc(x.mae, 1)])
    return table(['구분', '단계', '체결 건수', '평단(기준가 대비)', '+5% 도달', '+10% 도달', '+15% 도달', '+20% 도달', '최대상승(중앙)', '최대낙폭(중앙)'], rr)
t8 = stage_tab('균등')
rows_d = []
for g in (1, 2, 3, 4, 'all2'):
    for tp in (5, 10):
        for w in ('균등', '25/35/40'):
            x = dyn[(dyn.grp == g) & (dyn.tp == tp) & (dyn.w == w) & (dyn.stop == '없음')]
            if x.empty: continue
            x = x.iloc[0]
            rows_d.append([GN[g] if (tp == 5 and w == '균등') else '', f'+{tp}%', w, f'{int(x.n)}/{int(x.n_legs)}', f'{x.win:.1f}%', pc(x['mean'], 1, True), pc(x.cap, 1, True), pc(x.p10, 1), pc(x.worst, 1)])
t8d = table(['구분', '익절(평단 대비)', '비중', '체결/레그', '승률', '단순 평균', '자본가중 수익', '하위 10%', '최악'], rows_d)
# ---- 9번 표
def lv_txt(name, lv): return ' / '.join(f'−{x}%' for x in lv)
def cand(name, tp, stop, k=4):
    x = O[(O.name == name) & (O.tp == tp) & ((O.stop == stop) if stop == stop else O.stop.isna())].head(k)
    rr = []
    for _, r in x.iterrows():
        rr.append([lv_txt(name, r.levels), f'{r.fill:.0f}%', f'{r.win:.1f}%', f'{r.win_a:.0f}% / {r.win_b:.0f}%', pc(r['cap'], 1, True), f'{r.cap_a:+.1f}% / {r.cap_b:+.1f}%', f'{r.pl:.2f}', pc(r.worst, 0)])
    return rr
hd9 = ['1·2·3차 매수 위치', '체결률', '승률(전체)', '승률 전반/후반', '자본가중 수익', '수익 전반/후반', '평균이익÷평균손실', '최악']
t9a = table(hd9, cand('leg2p', 10, None) + cand('leg2p', 5, None, 3))
t9b = table(hd9, cand('leg1', 10, None) + cand('leg1', 5, None, 3))
# 대표값
a = O[(O.name == 'leg2p') & (O.tp == 10) & O.stop.isna()].iloc[0]; b = O[(O.name == 'leg1') & (O.tp == 10) & O.stop.isna()].iloc[0]

# ---- 10. 고점→첫 반등 기간, 상승폭별, 하락기 거래대금
R4 = pickle.load(open('R4.pkl', 'rb')); G4 = R4['G']; A4 = R4['all']; T4 = R4['test']
def _p(p): return '<0.001' if p < 0.001 else f'{p:.3f}'
def _sig(p): return '유의함' if p < 0.05 else '유의하지 않음'
ch_days4 = bar_chart(G4.bin.tolist(), [0 if pd.isna(v) else v for v in G4.days_med], '상승폭 구간별 고점→첫 반등 저점 거래일(중앙값)',
                     sub=[f'{n}건' for n in G4.n_reb], H=240, ylabel='거래일')
ch_ratio4 = bar_chart(G4.bin.tolist(), [0 if pd.isna(v) else v for v in G4.ratio_med], '상승폭 구간별 하락기/상승기 거래대금 비율(중앙값)',
                      vfmt=lambda v: f'{v:.1f}', sub=[f'{n}건' for n in G4.n_reb], H=240, ylabel='배')
t4 = table(['상승폭 (전일 종가→고점)', '사례', '첫 반등 있음', '고점→저점 거래일', '고점→반등 확정 거래일', '저점 하락률 (고점 대비)', '반등 상승률', '하락기/상승기 거래대금'],
           [[r.bin, r.n, r.n_reb, f'{r.days_med:.0f}일 ({r.days_q1:.0f}~{r.days_q3:.0f})', f'{r.conf_med:.0f}일',
             f'{r.dd_med:.1f}% ({r.dd_q1:.0f}~{r.dd_q3:.0f})', f'+{r.reb_med:.1f}%', f'{r.ratio_med:.2f}배 ({r.ratio_q1:.2f}~{r.ratio_q3:.2f})']
            for r in G4.itertuples() if r.n_reb])
t4q = table(['하락기 거래대금 비율 (3등분)', '사례', '비율 중앙값', '저점 하락률', '고점→저점 거래일', '반등 상승률'],
            [[r.rq, r.n, f'{r.ratio:.2f}배', f'{r.dd:.1f}%', f'{r.days:.0f}일', f'+{r.reb:.1f}%'] for r in R4['RQ'].itertuples()])
card10 = f"""<div class="card"><h2>10. 고점에서 첫 반등까지 걸린 기간 · 상승폭별 차이 · 하락기 거래대금</h2>
<p class="sub">고점(장중 고가)에서 −30% 이상 빠진 뒤 저점 대비 +10% 반등이 나온 <b>첫 반등 저점</b>까지, {R4['n_reb']}건(전체 {R4['n']}건) 기준
<b>고점→저점 중앙 {A4['days_med']:.0f}거래일</b>(25~75%: {A4['days_q1']:.0f}~{A4['days_q3']:.0f}일), +10% 반등 확정까지 중앙 {A4['conf_med']:.0f}거래일, 저점은 고점 대비 중앙 {A4['dd_med']:.1f}%입니다.</p>
<h3>상승폭(급등 시작 전일 종가 → 고점) 20% 구간별</h3>
{t4}
{ch_days4}
<p class="sub">상승폭이 클수록 저점까지 <b>더 빨리</b> 내려오는 경향이 있습니다(순위상관 ρ={T4['rise_days'][0]:.2f}, p={_p(T4['rise_days'][1])}; 구간 간 차이 Kruskal-Wallis p={_p(T4['kw_days'])}, {_sig(T4['kw_days'])}).
상승폭과 저점 깊이는 약한 관계만 있습니다(ρ={T4['rise_dd'][0]:.2f}, p={_p(T4['rise_dd'][1])}; 구간 간 차이 p={_p(T4['kw_dd'])}, {_sig(T4['kw_dd'])}). 다만 200% 이상 구간은 저점이 중앙 {G4.iloc[-1].dd_med:.1f}%로 더 깊었습니다.</p>
<h3>하락할 때 거래대금은 상승할 때보다 얼마나 적은가</h3>
<p class="sub">하락기(고점 다음 날~첫 반등 저점) 일평균 거래대금 ÷ 상승기(급등 시작일~고점) 일평균 거래대금은 <b>중앙 {A4['ratio_med']:.2f}배</b>(25~75%: {A4['ratio_q1']:.2f}~{A4['ratio_q3']:.2f})입니다.
{A4['share_lt1']*100:.0f}%의 사례에서 하락기 거래대금이 상승기보다 적었고, {A4['share_lt05']*100:.0f}%는 절반 미만이었습니다. 하락기가 상승기와 같다는 가정은 통계적으로 기각됩니다(Wilcoxon p={_p(T4['wil_p'])}) — <b>거래대금이 크게 줄면서 빠지는 것이 일반적</b>입니다.</p>
{ch_ratio4}
{t4q}
<p class="sub">거래대금 비율과 저점 깊이는 관계가 없었습니다(ρ={T4['ratio_dd'][0]:.2f}, p={_p(T4['ratio_dd'][1])}). 즉 "하락기 거래대금이 적으면 덜 빠진다"는 근거는 찾지 못했습니다.
비율이 높을수록 저점까지 기간이 짧았지만(ρ={T4['ratio_days'][0]:.2f}), 이는 상당 부분 <b>계산 구조 때문</b>입니다 — 하락 기간이 짧으면 고점 직후 거래가 많은 날만 평균에 들어가 비율이 커집니다. 반등 상승률과는 약한 양의 관계가 있었습니다(ρ={T4['ratio_reb'][0]:.2f}, p={_p(T4['ratio_reb'][1])}).</p>
<p class="mut" style="font-size:12px">일봉 기준(분봉상 고점·저점은 일봉 고가·저가로 대신). 같은 종목이 여러 번 들어간 사례가 있어 p값은 실제보다 작게(유의하게) 나올 수 있습니다. 구간별 사례가 8~11건인 곳은 중앙값이 크게 흔들릴 수 있습니다. 첫 반등이 없던 {R4['n']-R4['n_reb']}건은 기간·깊이 계산에서 빠졌습니다.</p></div>
"""

# ---- 종목 목록: 상승폭 구분 + 첫 반등 지표 추가
_D4 = R4['D'].copy(); _D4['key'] = _D4['ticker'].astype(str) + '|' + pd.to_datetime(_D4['start']).dt.strftime('%Y-%m-%d')
_D4 = _D4.set_index('key')
def _num(v, f):
    return ('', '–') if v is None or pd.isna(v) else (f'{v}', f(v))
_lo = {'80~100%': 80, '100~120%': 100, '120~140%': 120, '140~160%': 140, '160~180%': 160, '180~200%': 180, '200% 이상': 200}
L2 = []
for _, _r in lst.iterrows():
    _k = f"{str(_r['종목코드']).zfill(6)}|{_r['상승시작일']}"
    _x = _D4.loc[_k] if _k in _D4.index else None
    _g = lambda c: (None if _x is None or c not in _x.index else _x[c])
    _b = _g('bin'); _b = '' if _b is None or pd.isna(_b) else str(_b)
    cells = [f'<td data-v="{_lo.get(_b, 0)}">{_b or "–"}</td>',
             f'<td data-v="{html.escape(_r["종목명"])}">{html.escape(_r["종목명"])}</td>',
             f'<td data-v="{_r["시장"]}">{_r["시장"]}</td>',
             f'<td class="n" data-v="{_r["상승시작일"]}">{_r["상승시작일"]}</td>',
             f'<td class="n" data-v="{_r["상승률5일_장중고가"]}">{_r["상승률5일_장중고가"]:+.1f}%</td>',
             f'<td class="n" data-v="{_r["일평균거래대금_억"]}">{_r["일평균거래대금_억"]:,}</td>',
             f'<td class="n" data-v="{_r["시가총액_억"]}">{_r["시가총액_억"]:,.0f}</td>',
             f'<td class="n" data-v="{_r["고점일"]}">{_r["고점일"]}</td>',
             f'<td class="n" data-v="{_r["고점까지_총상승률"]}">{_r["고점까지_총상승률"]:+.0f}%</td>']
    for _c, _f in [('days_trough', lambda v: f'{v:.0f}'), ('days_confirm', lambda v: f'{v:.0f}'), ('dd', lambda v: f'{v:.1f}%'),
                 ('rebound', lambda v: f'+{v:.1f}%'), ('ratio', lambda v: f'{v:.2f}')]:
        _dv, _tx = _num(_g(_c), _f)
        cells.append(f'<td class="n" data-v="{_dv}">{_tx}</td>')
    cells += [f'<td class="n" data-v="{_r["최대낙폭_6개월"]}">{f1(_r["최대낙폭_6개월"],1)}%</td>',
              f'<td class="n" data-v="{_r["반등횟수"]}">{int(_r["반등횟수"])}</td>',
              f'<td class="n" data-v="{_r["저점이탈후_재반등횟수"]}">{int(_r["저점이탈후_재반등횟수"])}</td>']
    L2.append('<tr>' + ''.join(cells) + '</tr>')
_head2 = ['구분(상승폭)', '종목명', '시장', '상승 시작일', '5거래일 상승률', '일평균 거래대금(억)', '시가총액(억)', '고점일', '고점까지 상승',
          '고점→저점(거래일)', '고점→+10% 반등 확정(거래일)', '저점 하락률', '반등 상승률', '하락기/상승기 거래대금(배)',
          '6개월 최대낙폭', '반등 횟수', '이탈 후 재반등']
t_list = ('<div class="filter"><label for="flt">종목명 검색</label><input id="flt" type="search" placeholder="예: 신풍, 바이오"><span id="cnt" class="mut"></span></div>'
          '<div class="tw tall"><table id="lst"><thead><tr>' + ''.join(f'<th><button type="button" data-c="{i}">{h}</button></th>' for i, h in enumerate(_head2)) +
          '</tr></thead><tbody>' + ''.join(L2) + '</tbody></table></div>'
          '<p class="mut" style="font-size:12px">구분 = 급등 시작 전일 종가 → 고점 상승폭(20% 단위). 고점→저점·반등 확정·저점 하락률·반등 상승률은 고점 대비 −30% 이후 +10% 반등이 나온 <b>첫 반등</b> 기준(통계 10번과 같은 정의), 반등이 없던 사례는 –. 하락기/상승기 거래대금 = 하락기(고점 다음 날~첫 반등 저점) 일평균 ÷ 상승기(급등 시작일~고점) 일평균.</p>')

stats = f"""
<div class="card">
<h2>한눈에 보는 결과</h2>
<p class="sub">조건 1: 5거래일 내 장중 +80% 이상, 그 5일 중 3일 이상 거래대금 3천억원 이상 ({n_ep}건, {n_tk}종목). 일봉으로 근사했고 분봉 순서는 알 수 없습니다.</p>
<div class="ans">
<div><b>{pc(fm,1)}</b><span>② 첫 −30% 후 +10% 반등이 확정되는 고점 대비 낙폭 중앙값 (가운데 50%: {pc(fq3,0)}~{pc(fq1,0)})</span></div>
<div><b>{pc(bmed,1)}</b><span>③ 직전 저점을 깬 뒤 +10% 재반등이 나오는 추가 하락폭 중앙값 (가운데 50%: {pc(bq3,0)}~{pc(bq1,0)})</span></div>
<div><b>평균 {E.repeats.mean():.1f}회</b><span>④⑤ 6개월 안에 저점 이탈 후 재반등 반복. 차수가 오를수록 저점은 깊어지고 반등폭은 24%에서 약 19%로 줄어듭니다</span></div>
<div><b>{res6['norb_ep']}건 / {res6['reach_ep']}건</b><span>⑥ −50%까지 내려간 {res6['reach_ep']}건({res6['reach_tk']}종목) 중 20% 반등 없이 내려간 건 ({res6['norb_tk']}종목)</span></div>
<div><b>−33 / −38 / −43%</b><span>⑦ 고점 대비 3분할 매수 구간. 평단은 −33.0%, −35.6%, −38.3%</span></div>
<div><b>평단 +5%</b><span>⑧ 현실적인 목표. +10%는 레그별 도달률 약 50~60%이고 3차 매수 뒤에는 평균 −20%대까지 더 밀립니다</span></div>
</div>
<div class="note"><b>가장 중요한 제한:</b> 분봉이 없어서 "분봉상 고점·저점"은 일봉 고가·저가로 대신했습니다. 고점·저점 가격은 정확하지만 하루 안의 순서는 모릅니다. 상장폐지 종목이 빠져 있어 실제보다 낙관적일 수 있습니다. 맨 아래 "모르는 것"을 확인해 주세요.</div>
</div>

<div class="card"><h2>1. 종목 선정</h2>
<p class="sub">같은 급등이 이어지면 한 건으로 묶었습니다.</p>
{t5}
<h3>연도별 선정 건수</h3>{ch_year}
<p class="mut">2020년과 2026년에 몰려 있습니다. 과열 시기의 사례가 많다는 뜻이어서, 평상시에도 같은 결과일지는 모릅니다.</p></div>

<div class="card"><h2>2. 첫 반등 저점은 고점 대비 어디서 나오나</h2>
<p class="sub">고점에서 −30% 이상 하락한 뒤 저점 대비 +10% 반등이 확인된 시점의 저점 위치입니다. 평균 {pc(fmean,1)}, 중앙값 {pc(fm,1)} (95% 구간 {pc(fmed_ci[0],1)} ~ {pc(fmed_ci[1],1)}). 사례의 {share_30_40:.0f}%가 −30~−40% 안에 있습니다.</p>
{ch_first_hist}
<h3>그 깊이까지 내려온 사례 중 얼마나 거기서 반등했나</h3>{ch_first_haz}
<p class="mut">−50%까지 확률이 완만히 오르지만 신뢰구간(선)이 겹쳐서 특정 깊이가 유의하게 낫다고 말하기는 어렵습니다. −30% 근처가 많은 것은 정의상 −30%부터 세기 때문이기도 합니다.</p></div>

<div class="card"><h2>3·4. 저점을 깨고 내려가면 얼마나 더 빠져야 재반등하나</h2>
<p class="sub">직전 반등 저점의 저가를 하회한 뒤, 다음 +10% 반등이 확정된 저점이 직전 저점보다 얼마나 낮은지. 중앙값 {pc(bmed,1)} (95% 구간 {pc(bmed_ci[0],1)} ~ {pc(bmed_ci[1],1)}), 하위 10%는 {pc(bp10,1)}입니다. 이탈 뒤 6개월 안에 재반등이 없던 사례는 {int((E.end_reason=='broke_no_rebound').sum())}건입니다.</p>
{ch_brk_hist}{ch_brk_haz}</div>

<div class="card"><h2>5. 반복 횟수, 차수별 기간과 반등률</h2>
<p class="sub">6개월 안에 사례당 평균 {E.repeats.mean():.1f}회 반복했고(중앙 {E.repeats.median():.0f}회, 최대 {int(E.repeats.max())}회), 이탈 후 재반등은 모두 {rep_tot}회입니다.</p>
{ch_rep}
{t5b}
<p class="mut" style="font-size:12px">모든 기간은 거래일 기준, 괄호는 25~75% 구간입니다. ¹ 1차는 고점→첫 저점, 2차 이후는 직전 저점 이탈일→이번 저점. ² 저점에서 다음 차수 저점까지 한 사이클. 반등 상승률은 이탈이 확인된 레그만 집계했습니다(마지막 미이탈 레그는 진행 중이라 편향됩니다).</p>
<h3>차수별 반등 상승률 중앙값</h3>{ch_leg}</div>

<div class="card"><h2>6. 고점 대비 −50%까지 내려갈 때 20% 반등이 없던 종목</h2>
<p class="sub">고점에서 −50%까지 하락하는 동안 어느 저점에서도 +20% 반등(고가 기준)이 나오지 않은 사례입니다. 6개월 추적 구간 안에서 −50%에 닿은 사례만 셉니다.</p>
{t6}
<p>조건 1에 해당하는 {res6['total_ep']}건({res6['total_tk']}종목) 중 {res6['reach_ep']}건({res6['reach_tk']}종목)이 −50%에 닿았고, 그중 <b>{res6['norb_ep']}건({res6['norb_tk']}종목, {res6['norb_ep']/res6['reach_ep']*100:.0f}%)</b>이 20% 반등 없이 곧바로 내려갔습니다. 그런 사례에서 고점 후 −50%까지 걸린 기간 중앙값은 {res6['days_med']:.0f}거래일입니다.</p>
<details><summary>해당 {res6['norb_ep']}종목 보기</summary><p>{names6}</p></details>
<p class="mut" style="font-size:12px">반등은 저점 다음 날부터 인정했습니다(일봉으로는 같은 날 순서를 모르므로 보수적). −50% 도달일의 장중 반등은 제외했습니다. 조건검색 탭에서 상승률·거래대금을 바꾸면 조합별 건수도 볼 수 있습니다.</p></div>

<div class="card"><h2>7. 눌림 매수 진입 구간 (3분할)</h2>
<p class="sub">2번 분포의 가운데 50%({pc(fq3,1)} ~ {pc(fq1,1)})를 진입 구간으로 보고 5%p 단위로 −33% / −38% / −43%에 같은 금액을 나눴습니다. 체결 비율은 1차 97.6%, 2차 96.9%, 3차 89.8%입니다.</p>
{ch_ladder}
<p>단계별 평균 단가(고점 대비): 1차 후 {pc((A1-1)*100,1)}, 2차 후 {pc((A2-1)*100,1)}, 3차 후 {pc((A3-1)*100,1)}.</p></div>

<div class="card"><h2>8. 반등 구간마다 3분할 매수 시 평단 기준 수익률</h2>
<p class="sub">레그별로 같은 금액 3분할입니다. 1차 하락은 고점 기준 −33/−38/−43%, 2차 이후는 직전 저점 대비 −4/−9/−15%(3번 분포의 25·50·75% 지점)에 사 둡니다. 체결 후 다음 분할 체결 전 또는 20거래일 안에 평단 대비 몇 %까지 올랐는지 봅니다.</p>
{t8}
<h3>규칙을 넣은 시뮬레이션 (20거래일 보유, 손절 없음)</h3>{t8d}
<p class="mut" style="font-size:12px">자본가중 수익은 체결된 금액 비중으로 가중한 값입니다. 최악 값은 손절 없이 들고 간 경우입니다. 레그는 서로 겹칠 수 있고 독립이 아닙니다.</p>
<div class="note">같은 목표라도 1·2차 매수 뒤에는 도달률이 높지만, 3차까지 체결되면 평단 대비 최대낙폭 중앙값이 약 −20%로 깊습니다. 안정적으로 볼 수 있는 수익은 평단 +5% 안팎이고, +10% 이상은 레그의 절반 안팎만 도달합니다.</div></div>

<div class="card"><h2>9. 1차 25% · 2차 35% · 3차 40%로 나눌 때, 승률 80% 이상이 되는 매수 위치</h2>
<p class="sub">"손익비 80% 이상"을 <b>이익으로 끝난 비율(승률) 80% 이상</b>으로 읽었습니다. 다른 뜻이면 알려 주세요. 평균이익÷평균손실(손익비)도 같이 적었습니다. 후보는 체결률 75% 이상, 승률 80% 이상 중 수익이 큰 순서이며, 전반(2020~22)/후반(2023~26)으로 나눠 같은 레벨이 유지되는지 확인했습니다.</p>
<h3>2차 이상 레그: 직전 저점(전저점) 대비 하락률로 매수 (익절 +10% 위, +5% 아래, 손절 없음)</h3>{t9a}
<h3>1차 하락: 고점 대비 하락률로 매수</h3>{t9b}
<p><b>읽는 법:</b> 2차 이상 레그에서 승률 80% 이상이 되는 대표 위치는 전저점 대비 <b>−10% / −18% / −25%</b>(체결률 {a.fill:.0f}%, +10% 익절 시 승률 {a.win:.0f}%, 전반 {a.win_a:.0f}% · 후반 {a.win_b:.0f}%)입니다. 1차 하락은 고점 대비 <b>−43% / −48% / −55%</b>(체결률 {b.fill:.0f}%, 승률 {b.win:.0f}%)입니다. +5% 익절이면 대부분의 조합이 90% 안팎입니다.</p>
<div class="note">깊게 걸수록 승률은 오르지만 체결률이 떨어지고(위 표의 체결률), 손실이 나면 폭이 큽니다. 평균이익÷평균손실은 0.5~0.9로 1에 못 미쳐서, 승률은 높아도 몇 건의 큰 손실이 이익을 깎습니다. 최악 값이 −58% 안팎(손절 없을 때)인 점도 확인하세요. 같은 데이터에서 레벨을 고른 것이라 실전 성과는 이보다 낮을 수 있습니다.</div></div>

{card10}

<div class="card"><h2>정의를 바꾸면 결과가 얼마나 달라지나</h2>{t_sens}</div>

<div class="card"><h2>모르는 것과 한계</h2>
<ul>
<li><b>같은 날 안의 순서는 최근 약 1년만 반영됩니다.</b> 분봉이 있는 2025-11 이후는 정규장 1분봉으로 고점 이후의 하락, 저점 이후의 당일 반등까지 셉니다. 그 이전(일봉만 있는 기간)은 같은 날 안의 순서를 알 수 없어 반등을 저점 다음 날부터 인정했습니다. 저점일 하루 고저폭이 10% 이상인 비율은 첫 저점 {sd_first:.0f}%, 전체 {sd_all:.0f}%입니다.</li>
<li><b>키움 분봉(ka10080)이 과거 몇 년까지 제공되는지 모릅니다.</b> 확인되면 선정 종목만 분봉으로 다시 받아 재분석할 수 있습니다.</li>
<li><b>상장폐지 종목이 없습니다.</b> 급등 후 폐지된 종목이 빠져서 눌림 매수 성과가 실제보다 좋게 나옵니다.</li>
<li><b>고점은 사후에 압니다.</b> 실제 매매 중에는 지금이 고점인지 알 수 없습니다.</li>
<li><b>시기가 몰려 있습니다.</b> 2020년과 2026년(5~6월 대형주 급등)에 사례가 많아 독립 표본이 {n_ep}건보다 적습니다. 2026년 데이터는 제공받은 값의 내부 일관성만 확인했고 외부 시세와 대조하지 않았습니다.</li>
<li><b>체결 가능성.</b> 하한가 잠김·얇은 호가에서는 지정가가 체결되지 않을 수 있습니다. 수수료·세금·슬리피지는 넣지 않았습니다.</li>
<li><b>매수 위치는 같은 데이터에서 골랐습니다.</b> 전반/후반 확인은 했지만 진짜 표본 밖 검증은 아닙니다.</li>
<li><b>"손익비 80%"의 뜻</b>을 승률로 가정했습니다(9번).</li>
</ul>
<h3>더 필요한 데이터와 구하는 방법</h3>
<ul>
<li><b>선정 종목의 분봉(1·3·5분):</b> 키움 REST ka10080으로 받아 봅니다. 과거 몇 년까지 되는지 먼저 확인이 필요합니다.</li>
<li><b>상장폐지 종목 목록과 시세:</b> KRX 정보데이터시스템의 상장폐지종목 현황(CSV)을 내려받아 주시면 누락 규모부터 점검할 수 있습니다. 폐지 종목 시세는 키움으로는 받을 수 없어 별도 출처가 필요합니다.</li>
<li><b>상승 이유(뉴스·공시·테마):</b> DART 공시 목록이나 네이버 금융 뉴스에서 종목·날짜별로 모아야 합니다. 선정 {n_ep}건 정도면 수집이 가능합니다.</li>
<li><b>업종·시가총액 이력:</b> 업종은 비어 있고 2019년 이전 시가총액은 없습니다. KRX 일별 시가총액 자료로 채울 수 있습니다.</li>
</ul></div>
"""
tpl = open('web/tpl_head.html', encoding='utf-8').read() + open('web/tpl_body.html', encoding='utf-8').read()
tpl = tpl.replace('{{LAST}}', LASTD).replace('<!--STATS-->', stats).replace('<!--LIST-->', t_list)
extra = """
document.getElementById('n-list0').textContent=document.querySelectorAll('#lst tbody tr').length;
"""
page = tpl + '<script>' + open('web/tpl_js.js', encoding='utf-8').read() + '</script><script>' + js + extra + '</script>'
open('web/index.html', 'w', encoding='utf-8').write(page)
print(len(page))
