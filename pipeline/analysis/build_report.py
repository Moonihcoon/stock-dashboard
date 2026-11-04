import pickle, sys, html, math, numpy as np, pandas as pd
sys.path.insert(0, '.')
from analyze_v2 import *
from build_data import hz, H1, H2, E, T, first, eps, ST, SUB, CV, SENS, byo, lst, cens
B = ''
p = P()
LV = [0.33, 0.38, 0.43]
M = '−'   # 진짜 마이너스 기호


def f1(v, d=1, sign=False):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return '–'
    s = f'{abs(v):,.{d}f}'
    if v < 0 and float(s.replace(',', '')) != 0:
        return M + s
    return ('+' + s) if sign and v > 0 else s


def pc(v, d=1, sign=False):
    return f1(v, d, sign) + '%'


# ------------------------------------------------------------------ 핵심 수치
n_ep, n_tk = len(E), E.ticker.nunique()
n_kq, n_ks = int((E.market == 'KOSDAQ').sum()), int((E.market == 'KOSPI').sum())
fd = first.dd_peak.values * 100
fm, fmean, fsd = np.median(fd), fd.mean(), fd.std(ddof=1)
fq1, fq3 = np.percentile(fd, 25), np.percentile(fd, 75)
fmed_ci = boot_ci(fd, np.median); fmean_ci = boot_ci(fd, np.mean)
share_30_40 = ((fd <= -30) & (fd > -40)).mean() * 100
rr = T[T.order >= 2]
bd = rr.depth_vs_ref.values * 100
bmed, bq1, bq3, bp10 = np.median(bd), np.percentile(bd, 25), np.percentile(bd, 75), np.percentile(bd, 10)
bmed_ci = boot_ci(bd, np.median)
cond2, cond3 = int(E.cond2.sum()), int(E.cond3.sum())
rep_tot = int(E.repeats.sum())
mdd_med = E.max_dd.median() * 100
n_complete = int(E.complete.sum()); n_trunc = int(E.trunc.sum()); n_incomp = int((~E.complete & ~E.trunc).sum())
sd_first = (first.same_day_range >= 0.10).mean() * 100
sd_all = (T.same_day_range >= 0.10).mean() * 100

# ------------------------------------------------------------------ SVG 도우미
W = 820


def nice_max(v):
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v)); m = v / e
    for s in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m <= s:
            return s * e
    return 10 * e


def bar_chart(labels, vals, aria, ymax=None, vfmt=lambda v: f'{v:,.0f}', sub=None, colors=None, H=230, ylabel=None, ticks=4):
    L, R, Tp, Bt = 52, 14, 26, 56 if sub else 44
    ymax = ymax or nice_max(max(vals) * 1.1)
    ph = H - Tp - Bt; pw = W - L - R
    slot = pw / len(vals); bw = min(64, slot * 0.62)
    o = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(aria)}">']
    for i in range(ticks + 1):
        y = Tp + ph - ph * i / ticks; tv = ymax * i / ticks
        o.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}"/>')
        o.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{vfmt(tv)}</text>')
    for i, (lb, v) in enumerate(zip(labels, vals)):
        cx = L + slot * (i + .5); h = ph * (v / ymax) if ymax else 0
        col = (colors[i] if colors else 'var(--blue)')
        o.append(f'<rect x="{cx-bw/2:.1f}" y="{Tp+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0):.1f}" rx="4" fill="{col}"/>')
        o.append(f'<text class="vl" x="{cx:.1f}" y="{Tp+ph-h-6:.1f}" text-anchor="middle">{vfmt(v)}</text>')
        o.append(f'<text class="ax" x="{cx:.1f}" y="{H-Bt+17}" text-anchor="middle">{html.escape(str(lb))}</text>')
        if sub:
            o.append(f'<text class="ax2" x="{cx:.1f}" y="{H-Bt+32}" text-anchor="middle">{html.escape(str(sub[i]))}</text>')
    o.append(f'<line class="base" x1="{L}" y1="{Tp+ph}" x2="{W-R}" y2="{Tp+ph}"/>')
    if ylabel:
        o.append(f'<text class="axl" x="{L}" y="14">{html.escape(ylabel)}</text>')
    o.append('</svg>')
    return ''.join(o)


def hazard_chart(rows, aria, ref=None, H=250, minn=10):
    L, R, Tp, Bt = 52, 14, 26, 58
    ph = H - Tp - Bt; pw = W - L - R
    slot = pw / len(rows)
    o = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(aria)}">']
    for i in range(5):
        y = Tp + ph - ph * i / 4
        o.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}"/>')
        o.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{i*25}%</text>')
    if ref is not None:
        y = Tp + ph - ph * ref
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="var(--ink-3)" stroke-width="1.2" stroke-dasharray="4 4"/>')
        o.append(f'<text class="axl" x="{W-R}" y="{y-6:.1f}" text-anchor="end">전체 평균 {ref*100:.0f}%</text>')
    for i, r in enumerate(rows):
        cx = L + slot * (i + .5)
        small = r['at_risk'] < minn
        if r['hazard'] is not None:
            yh = Tp + ph - ph * r['hazard']; ylo = Tp + ph - ph * r['lo']; yhi = Tp + ph - ph * r['hi']
            o.append(f'<line x1="{cx:.1f}" y1="{yhi:.1f}" x2="{cx:.1f}" y2="{ylo:.1f}" stroke="var(--ink-3)" stroke-width="1.5"/>')
            o.append(f'<line x1="{cx-6:.1f}" y1="{yhi:.1f}" x2="{cx+6:.1f}" y2="{yhi:.1f}" stroke="var(--ink-3)" stroke-width="1.5"/>')
            o.append(f'<line x1="{cx-6:.1f}" y1="{ylo:.1f}" x2="{cx+6:.1f}" y2="{ylo:.1f}" stroke="var(--ink-3)" stroke-width="1.5"/>')
            fill = 'var(--bg)' if small else 'var(--blue)'
            o.append(f'<circle cx="{cx:.1f}" cy="{yh:.1f}" r="6" fill="{fill}" stroke="var(--blue)" stroke-width="2.5"/>')
            o.append(f'<text class="vl" x="{cx+13:.1f}" y="{yh+4:.1f}">{r["hazard"]*100:.0f}%</text>')
        o.append(f'<text class="ax" x="{cx:.1f}" y="{H-Bt+17}" text-anchor="middle">{html.escape(r["label"])}%</text>')
        o.append(f'<text class="ax2" x="{cx:.1f}" y="{H-Bt+32}" text-anchor="middle">n={r["at_risk"]}{" (적음)" if small else ""}</text>')
    o.append(f'<line class="base" x1="{L}" y1="{Tp+ph}" x2="{W-R}" y2="{Tp+ph}"/>')
    o.append('</svg>')
    return ''.join(o)


def table(head, rows, cls='', align=None):
    o = [f'<div class="tw"><table class="{cls}"><thead><tr>' + ''.join(f'<th>{h}</th>' for h in head) + '</tr></thead><tbody>']
    for r in rows:
        trc = ''
        if isinstance(r, tuple) and len(r) == 2 and isinstance(r[1], str) and r[1].startswith('class:'):
            r, trc = r[0], r[1][6:]
        o.append(f'<tr class="{trc}">' + ''.join(f'<td class="n">{c}</td>' if i else f'<td>{c}</td>' for i, c in enumerate(r)) + '</tr>')
    o.append('</tbody></table></div>')
    return ''.join(o)


# ------------------------------------------------------------------ 차트들
# 연도별 에피소드
yr = E.groupby(E.start_date.dt.year).size()
ch_year = bar_chart([str(y) for y in yr.index], yr.values.tolist(), '연도별 선정 종목 수', ymax=nice_max(yr.max() * 1.15), ticks=4)

# 첫 반등저점 분포 + hazard
cnt1 = [r['events'] for r in H1]
ch_first_hist = bar_chart([r['label'] + '%' for r in H1], cnt1, '첫 반등저점의 고점 대비 하락률 분포',
                          sub=[f'{c/len(first)*100:.0f}%' for c in cnt1], H=240, ylabel='에피소드 수')
ref1 = len(first) / sum(r['at_risk'] for r in H1)
ch_first_haz = hazard_chart(H1, '깊이별 첫 반등 확정 확률', ref=ref1)
cnt2 = [r['events'] for r in H2]
ch_brk_hist = bar_chart([r['label'] + '%' for r in H2], cnt2, '직전 저점 이탈 후 재반등 지점의 추가 하락폭 분포',
                        sub=[f'{c/len(rr)*100:.0f}%' for c in cnt2], H=240, ylabel='재반등 횟수')
ref2 = len(rr) / sum(r['at_risk'] for r in H2)
ch_brk_haz = hazard_chart(H2, '이탈폭별 재반등 확정 확률', ref=ref2)

# 반복 횟수 분포
rc = E.repeats.value_counts().sort_index()
mx = int(rc.index.max())
rep_vals = [int(rc.get(i, 0)) for i in range(0, mx + 1)]
ch_rep = bar_chart([str(i) for i in range(0, mx + 1)], rep_vals, '에피소드별 저점 이탈 후 재반등 횟수 분포',
                   H=230, ylabel='에피소드 수')

# 차수별 반등률
ob = byo.copy()
lab_o = [(str(int(o)) + '차' if o < 7 else '7차+') for o in ob.o]
ch_leg = bar_chart(lab_o, ob.leg_med.round(1).tolist(), '차수별 반등 레그 상승률 중앙값',
                   vfmt=lambda v: f'{v:.1f}%', sub=[f'n={int(n)}' for n in ob.n_leg], H=250, ylabel='저점 → 이탈 전 최고가 (중앙값)')


# ------------------------------------------------------------------ 예시 경로
def example_chart(eid):
    e = eps[eid]; g = e['_g']; k = e['k']; peak = e['peak']
    end, _, _ = horizon_end(g, k, e['next_s0'], p)
    ch = analyze_chain(g, k, peak, end, p)
    fills = fill_plan(g, k, peak, end, LV)
    i0 = max(0, k - 6); i1 = end
    n = i1 - i0 + 1
    hi = g['high'].to_numpy(float) / peak; lo = g['low'].to_numpy(float) / peak; cl = g['close'].to_numpy(float) / peak
    ymin = math.floor((lo[i0:i1 + 1].min() - 0.03) * 10) / 10
    ymax = 1.05
    Wc, Hc = 820, 380; L, R, Tp, Bt = 54, 96, 18, 40
    pw, ph = Wc - L - R, Hc - Tp - Bt
    X = lambda i: L + pw * (i - i0 + .5) / n
    Y = lambda v: Tp + ph * (ymax - v) / (ymax - ymin)
    o = [f'<svg class="chart" viewBox="0 0 {Wc} {Hc}" role="img" aria-label="{html.escape(e["name"])} 고점 이후 가격 경로와 반등 저점, 분할 매수 위치">']
    t = ymin
    while t <= ymax + 1e-9:
        if t <= 1.0 + 1e-9:
            o.append(f'<line class="grid" x1="{L}" y1="{Y(t):.1f}" x2="{Wc-R}" y2="{Y(t):.1f}"/>')
            o.append(f'<text class="ax" x="{L-8}" y="{Y(t)+4:.1f}" text-anchor="end">{(t-1)*100:.0f}%</text>')
        t = round(t + 0.1, 6)
    # 구간 음영 (진입 구간 -33 ~ -43)
    o.append(f'<rect x="{L}" y="{Y(1-0.33):.1f}" width="{pw}" height="{Y(1-0.43)-Y(1-0.33):.1f}" fill="var(--orange)" opacity=".10"/>')
    for lv, lab in zip(LV, ('1차', '2차', '3차')):
        y = Y(1 - lv)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{Wc-R}" y2="{y:.1f}" stroke="var(--orange)" stroke-width="1.3"/>')
        o.append(f'<text class="axl" x="{Wc-R+6}" y="{y+4:.1f}" fill="var(--orange-ink)" style="fill:var(--orange-ink)">{lab} −{lv*100:.0f}%</text>')
    y30 = Y(0.70)
    o.append(f'<line x1="{L}" y1="{y30:.1f}" x2="{Wc-R}" y2="{y30:.1f}" stroke="var(--red)" stroke-width="1.2" stroke-dasharray="5 4"/>')
    o.append(f'<text class="axl" x="{Wc-R+6}" y="{y30-5:.1f}" style="fill:var(--red-ink)">−30% 기준</text>')
    # 일중 고저 막대 + 종가선
    for i in range(i0, i1 + 1):
        o.append(f'<line x1="{X(i):.1f}" y1="{Y(hi[i]):.1f}" x2="{X(i):.1f}" y2="{Y(lo[i]):.1f}" stroke="var(--ink-3)" stroke-width="2" opacity=".55"/>')
    pts = ' '.join(f'{X(i):.1f},{Y(cl[i]):.1f}' for i in range(i0, i1 + 1))
    o.append(f'<polyline points="{pts}" fill="none" stroke="var(--blue)" stroke-width="2"/>')
    # 고점 표시
    o.append(f'<circle cx="{X(k):.1f}" cy="{Y(1.0):.1f}" r="5" fill="var(--ink)"/>')
    o.append(f'<text class="vl" x="{X(k)+9:.1f}" y="{Y(1.0)+4:.1f}">고점 {g["date"].iloc[k]:%Y-%m-%d}</text>')
    # 반등 저점
    for j, tr in enumerate(ch['troughs'], 1):
        x, y = X(tr['idx']), Y(tr['low'] / peak)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="var(--red)" stroke="var(--bg)" stroke-width="2"/>')
        o.append(f'<text class="vl" x="{x:.1f}" y="{y+22:.1f}" text-anchor="middle" style="fill:var(--red-ink)">{j}</text>')
    # 매수 체결
    for j, (fi, fp) in enumerate(fills, 1):
        x, y = X(fi), Y(fp / peak)
        o.append(f'<path d="M{x:.1f},{y-7:.1f} L{x+7:.1f},{y:.1f} L{x:.1f},{y+7:.1f} L{x-7:.1f},{y:.1f} Z" fill="var(--orange)" stroke="var(--bg)" stroke-width="2"/>')
    # x 눈금
    step = 20
    for i in range(i0, i1 + 1, step):
        o.append(f'<text class="ax" x="{X(i):.1f}" y="{Hc-Bt+18}" text-anchor="middle">{g["date"].iloc[i]:%y-%m-%d}</text>')
    o.append(f'<line class="base" x1="{L}" y1="{Tp+ph}" x2="{Wc-R}" y2="{Tp+ph}"/>')
    o.append('</svg>')
    info = dict(name=e['name'], market=e['market'], start=e['start_date'], peak_date=g['date'].iloc[k], n_tr=len(ch['troughs']),
                dd1=ch['troughs'][0]['dd_peak'] * 100, nfill=len(fills), ntr=len(ch['troughs']))
    return ''.join(o), info


EX_EID = 46
ch_example, ex = example_chart(EX_EID)

# ------------------------------------------------------------------ 3분할 도식
avgs = [LV and 0]  # placeholder


def avg_of(levels):
    pr = [1 - l for l in levels]
    return len(pr) / sum(1 / x for x in pr)


A1, A2, A3 = (avg_of(LV[:i]) for i in (1, 2, 3))


def ladder():
    Hc = 360; L, R, Tp, Bt = 70, 220, 14, 24
    pw, ph = 820 - L - R, Hc - Tp - Bt
    Y = lambda v: Tp + ph * (-v) / 0.62   # v: 0 ~ -0.62
    o = [f'<svg class="chart" viewBox="0 0 820 {Hc}" role="img" aria-label="진입 구간과 3분할 매수 지정가, 단계별 평단">']
    for t in range(0, 61, 10):
        y = Y(-t / 100)
        o.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{820-R}" y2="{y:.1f}"/>')
        o.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{M if t else ""}{t}%</text>')
    # 진입 구간(P25~P75)
    yz1, yz2 = Y(fq3 / 100), Y(fq1 / 100)
    o.append(f'<rect x="{L}" y="{yz1:.1f}" width="{820-R-L}" height="{yz2-yz1:.1f}" fill="var(--blue)" opacity=".12"/>')
    o.append(f'<text class="axl" x="{820-R+10}" y="{(yz1+yz2)/2-8:.1f}">진입 구간</text>')
    o.append(f'<text class="ax" x="{820-R+10}" y="{(yz1+yz2)/2+8:.1f}">{pc(fq3,1)} ~ {pc(fq1,1)}</text>')
    o.append(f'<text class="ax2" x="{820-R+10}" y="{(yz1+yz2)/2+22:.1f}">첫 저점의 가운데 50%</text>')
    # 중앙값
    ym = Y(fm / 100)
    o.append(f'<line x1="{L}" y1="{ym:.1f}" x2="{820-R}" y2="{ym:.1f}" stroke="var(--blue)" stroke-width="1.2" stroke-dasharray="4 4"/>')
    # -30선
    y30 = Y(-0.30)
    o.append(f'<line x1="{L}" y1="{y30:.1f}" x2="{820-R}" y2="{y30:.1f}" stroke="var(--red)" stroke-width="1.2" stroke-dasharray="5 4"/>')
    o.append(f'<text class="axl" x="{820-R+10}" y="{y30-5:.1f}" style="fill:var(--red-ink)">−30% 하락 기준</text>')
    xs = [L + (820 - R - L) * f for f in (.22, .50, .78)]
    for x, lv, a, n in zip(xs, LV, (A1, A2, A3), (1, 2, 3)):
        y = Y(-lv)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{820-R}" y2="{y:.1f}" stroke="var(--orange)" stroke-width="1.6"/>')
        o.append(f'<path d="M{x:.1f},{y-9:.1f} L{x+9:.1f},{y:.1f} L{x:.1f},{y+9:.1f} L{x-9:.1f},{y:.1f} Z" fill="var(--orange)" stroke="var(--bg)" stroke-width="2"/>')
        o.append(f'<text class="vl" x="{x+16:.1f}" y="{y-8:.1f}">{n}차 매수 −{lv*100:.0f}%</text>')
        ya = Y(a - 1)
        o.append(f'<circle cx="{L+8}" cy="{ya:.1f}" r="5" fill="var(--ink)"/>')
        o.append(f'<text class="ax" x="{L+18}" y="{ya+4:.1f}">평단 {pc((a-1)*100,1)}</text>')
    o.append(f'<line class="base" x1="{L}" y1="{Tp}" x2="{L}" y2="{Tp+ph}"/>')
    o.append('</svg>')
    return ''.join(o)


ch_ladder = ladder()

# ------------------------------------------------------------------ 표들
# 요청5 집계
rep_dist = E.repeats.value_counts().sort_index()
t5 = table(['구분', '에피소드', '종목 수', '발생 횟수', '비고'], [
    ['조건 1 충족 (선정)', f'{n_ep}', f'{n_tk}', '–', f'코스닥 {n_kq} · 코스피 {n_ks}'],
    ['조건 2 (−30% 하락 후 +10% 반등)', f'{cond2} ({cond2/n_ep*100:.1f}%)', f'{E[E.cond2].ticker.nunique()}', f'{cond2}회', '에피소드당 첫 저점 1회'],
    ['조건 3 (저점 이탈 후 +10% 재반등) 1회 이상', f'{cond3} ({cond3/n_ep*100:.1f}%)', f'{E[E.cond3].ticker.nunique()}', f'{rep_tot}회', f'에피소드당 평균 {E.repeats.mean():.2f} · 중앙 {E.repeats.median():.0f} · 최대 {int(E.repeats.max())}'],
    ['  6개월 추적을 끝낸 에피소드만', f'{n_complete}', f'{E[E.complete].ticker.nunique()}', f'{int(E[E.complete].repeats.sum())}회', f'에피소드당 평균 {E[E.complete].repeats.mean():.2f} · 중앙 {E[E.complete].repeats.median():.0f}'],
])

# 차수 표
rows_o = []
for _, r in byo.iterrows():
    rows_o.append([f'{int(r.o)}차' if r.o < 7 else '7차 이상', f'{int(r.n)}', pc(r.dd_med, 1),
                   (pc(r.brk_med, 1) if pd.notna(r.brk_med) else '–'), f'{int(r.n_leg)}',
                   pc(r.leg_med, 1) + f' <span class="mut">({pc(r.leg_p25,0)}~{pc(r.leg_p75,0)})</span>', f'{r.days_med:.0f}일',
                   pc(r.f5_med, 1)])
t_order = table(['차수', '저점 수', '저점의 고점 대비', '직전 저점 이탈폭', '이탈 확인 레그', '반등 레그 상승률(중앙, 25~75%)', '저점→이탈까지', '저점 후 5일 최대'], rows_o)

# 단계 표
rows_s = []
for _, r in ST.iterrows():
    rows_s.append([f'{int(r["단계"])}차 체결 후', f'{int(r.n)}', pc(r['평단_고점대비'], 1),
                   f'{r["다음분할로_이탈"]:.0f}%'] + [f'{r[f"+{x}%"]:.0f}% <span class="mut">({r[f"+{x}%_CI"]})</span>' for x in (5, 10, 15, 20)] +
                  [pc(r['MFE중앙'], 1), pc(r['MAE중앙'], 1)])
t_stage = table(['단계', '표본', '평단(고점 대비)', '다음 분할 체결로 종료', '+5% 도달', '+10% 도달', '+15% 도달', '+20% 도달', '최대상승(중앙)', '최대낙폭(중앙)'], rows_s)

# 동적 시뮬 (자본가중) 재계산
def run_all(sub, lv, tp, N, stop):
    o = []
    for e in sub:
        g = e['_g']; end, _, _ = horizon_end(g, e['k'], e['next_s0'], p)
        r = simulate_dynamic(g, e['k'], e['peak'], end, lv, tp, N, stop)
        if r:
            o.append(r)
    return pd.DataFrame(o)


rows_d = []
dyn_cap = {}
for tp in (0.05, 0.10, 0.15):
    for stop in (None, 0.25):
        df = run_all(eps, LV, tp, 20, stop)
        u = df.stage; capw = (df.ret * u).sum() / u.sum() * 100
        dyn_cap[(tp, stop)] = capw
        rows_d.append([f'+{int(tp*100)}%', '없음' if stop is None else f'−{int(stop*100)}%', f'{len(df)}', f'{(df.ret>0).mean()*100:.1f}%',
                       pc(df.ret.mean() * 100, 1, True), pc(capw, 1, True), pc(df.ret.quantile(.1) * 100, 1), pc(df.ret.min() * 100, 1),
                       f'{u[df.ret<0].sum()/u.sum()*100:.0f}%'])
t_dyn = table(['익절(평단 대비)', '손절', '체결 에피소드', '승률', '단순 평균', '자본가중 수익', '하위 10%', '최악', '손실난 건의 자본 비중'], rows_d)
# 단계별 최종 결과 (익절+10%, 손절 25%)
dfx = run_all(eps, LV, 0.10, 20, 0.25)
stg = dfx.groupby('stage').agg(n=('ret', 'size'), win=('ret', lambda s: (s > 0).mean() * 100), mean=('ret', lambda s: s.mean() * 100), med=('ret', 'median')).reset_index()
t_final = table(['최종 체결 단계', '에피소드', '승률', '평균 수익', '중앙값'], [[f'{int(r.stage)}차까지', f'{int(r.n)}', f'{r.win:.0f}%', pc(r['mean'], 1, True), pc(r.med * 100, 1, True)] for _, r in stg.iterrows()])

# 교차검증 / 부분표본
t_cv = table(['구간', '진입 레벨', '익절', '표본', '승률', '단순 평균', '자본가중 수익', '하위 10%'],
             [[r['구분'], r['레벨'], r['익절'], f'{int(r.n)}', f'{r["승률"]:.1f}%', pc(r['단순'], 1, True), pc(r['자본가중'], 1, True), pc(r['P10'], 1)] for _, r in CV.iterrows()])
t_sub = table(['표본', '익절', '에피소드', '체결', '승률', '단순 평균', '자본가중 수익', '하위 10%'],
              [[r['구분'], r['익절'], f'{int(r["에피소드"])}', f'{int(r.n)}', f'{r["승률"]:.1f}%', pc(r['단순'], 1, True), pc(r['자본가중'], 1, True), pc(r['P10'], 1)] for _, r in SUB.iterrows()])
t_sens = table(['정의 변경', '에피소드', '종목', '조건3 발생', '이벤트당 재반등', '첫 저점(중앙)', '첫 저점(25~75%)', '이탈 후 추가 하락(중앙)'],
               [[r.label, f'{int(r.n)}', f'{int(r.tickers)}', f'{int(r.cond3)}', f'{r.repeats_mean:.1f}', pc(r.first_med, 1), f'{pc(r.first_p25,1)} ~ {pc(r.first_p75,1)}', pc(r.brk_med, 1)] for _, r in SENS.iterrows()],
               )

# 종목 리스트 표
L_rows = []
for i, r in lst.iterrows():
    L_rows.append(
        f'<tr><td data-v="{html.escape(r["종목명"])}">{html.escape(r["종목명"])}</td>'
        f'<td data-v="{r["시장"]}">{r["시장"]}</td>'
        f'<td class="n" data-v="{r["상승시작일"]}">{r["상승시작일"]}</td>'
        f'<td class="n" data-v="{r["상승률5일_장중고가"]}">{r["상승률5일_장중고가"]:+.1f}%</td>'
        f'<td class="n" data-v="{r["일평균거래대금_억"]}">{r["일평균거래대금_억"]:,}</td>'
        f'<td class="n" data-v="{r["시가총액_억"]}">{r["시가총액_억"]:,.0f}</td>'
        f'<td class="n" data-v="{r["고점일"]}">{r["고점일"]}</td>'
        f'<td class="n" data-v="{r["고점까지_총상승률"]}">{r["고점까지_총상승률"]:+.0f}%</td>'
        f'<td class="n" data-v="{r["최대낙폭_6개월"]}">{f1(r["최대낙폭_6개월"],1)}%</td>'
        f'<td class="n" data-v="{r["반등횟수"]}">{int(r["반등횟수"])}</td>'
        f'<td class="n" data-v="{r["저점이탈후_재반등횟수"]}">{int(r["저점이탈후_재반등횟수"])}</td></tr>')
list_head = ['종목명', '시장', '상승 시작일', '5거래일 상승률', '일평균 거래대금(억)', '시가총액(억)', '고점일', '고점까지 상승', '6개월 최대낙폭', '반등 횟수', '이탈 후 재반등']
t_list = ('<div class="filter"><label for="flt">종목명 검색</label><input id="flt" type="search" placeholder="예: 신풍, 바이오"><span id="cnt" class="mut"></span></div>'
          '<div class="tw tall"><table id="lst"><thead><tr>' + ''.join(f'<th><button type="button" data-c="{i}">{h}</button></th>' for i, h in enumerate(list_head)) +
          '</tr></thead><tbody>' + ''.join(L_rows) + '</tbody></table></div>')

# ------------------------------------------------------------------ 값 모음
Hs = {r['label']: r for r in H1}
S1, S2, S3 = (ST[ST['단계'] == i].iloc[0] for i in (1, 2, 3))
cvB = CV[(CV['구분'] == '후반(검증)')]
cvA = CV[(CV['구분'] == '전반(학습)')]
cv5_in, cv10_in = cvA[cvA.익절 == '+5%'].iloc[0]['자본가중'], cvA[cvA.익절 == '+10%'].iloc[0]['자본가중']
cv5_out, cv10_out = cvB[cvB.익절 == '+5%'].iloc[0]['자본가중'], cvB[cvB.익절 == '+10%'].iloc[0]['자본가중']
all5, all10 = dyn_cap[(0.05, 0.25)], dyn_cap[(0.10, 0.25)]
leg1 = byo[byo.o == 1].iloc[0]; leg7 = byo[byo.o == 7].iloc[0]
rep_tot_n = len(rr)

pickle.dump(dict(n_ep=n_ep, n_tk=n_tk), open(B + 'rep_meta.pkl', 'wb'))
print('OK', n_ep, n_tk, fm, bmed, all5, all10, cv5_out, cv10_out)
