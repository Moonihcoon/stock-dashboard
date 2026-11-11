"""
급등주 고점 -> 하락 -> 반등 체인 분석 v2  (일봉 기반)
=====================================================
정의
 1) 종목선정: 5거래일 구간에서 [장중 최고가 / 구간 직전 종가 - 1] >= +80%,
              그 5일 중 거래대금 >= 3,000억원인 날이 3일 이상. 구간 시작일 2020-01-01 이후.
 2) 고점   : 조건 충족 구간 시작 ~ 종료+20거래일 사이 최고 장중고가(창 끝이면 60일까지 연장).
 3) 첫 반등저점: 고점 대비 -30% 이하까지 빠진 뒤, 러닝 최저가 대비 +10%가 '이후 거래일'에 확인되는 지점.
 4) 반복   : 반등 후 직전 저점을 이탈(저가 < 저점)한 뒤, 새 최저가 대비 +10% 재반등이 확인되면 1차수 증가.
 5) 기간   : 고점일로부터 달력 기준 6개월.

일봉 한계: 같은 날 안에서 저가/고가의 선후는 알 수 없어 '저점일 다음 거래일부터' 반등을 인정(보수적).
분봉 보완: 분봉이 있는 날(키움 제공 최근 약 1년)은 정규장 분봉으로 고가·저가·종가를 잡고 같은 날 안의 순서를 반영.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from dataclasses import dataclass

EOK = 1e8


@dataclass
class P:
    start: str = '2020-01-01'
    win: int = 5
    rise: float = 0.80
    val_thresh: float = 3000 * EOK
    val_days: int = 3
    use_high: bool = True          # True: 장중고가/직전종가, False: 종가/종가
    ext: int = 20
    hard: int = 60
    min_dd: float = 0.30
    rb: float = 0.10
    months: int = 6
    ref: str = 'trough'            # 'trough': 직전 반등저점 이탈 / 'confirm_day': 반등확인일 저가 이탈


def locate_peak(hi, s, t, p):
    n = len(hi)
    end = min(n - 1, t + p.ext)
    hard = min(n - 1, t + p.hard)
    while True:
        k = s + int(np.nanargmax(hi[s:end + 1]))
        if k < end or end >= hard:
            return k
        end = min(hard, end + p.ext)


def mc_lookup(g, idx, maxgap=10):
    """idx 날짜 기준 시가총액(원): 직전 관측 우선, 없으면 직후. 못 찾으면 (nan, None)."""
    mc = g['market_cap_won'].to_numpy(float)
    ob = g['market_cap_observed'].to_numpy()
    n = len(g)
    for off in range(0, maxgap + 1):
        j = idx - off
        if j >= 0 and ob[j] == 1 and np.isfinite(mc[j]):
            return mc[j], g['date'].iloc[j]
    for off in range(1, maxgap + 1):
        j = idx + off
        if j < n and ob[j] == 1 and np.isfinite(mc[j]):
            return mc[j], g['date'].iloc[j]
    return np.nan, None


def find_episodes(d, p: P):
    eps = []
    for tk, g in d.groupby('ticker', sort=False):
        g = g.reset_index(drop=True)
        n = len(g)
        if n < p.win + 10:
            continue
        dates = g['date'].to_numpy()
        hi = g['high'].to_numpy(float); lo = g['low'].to_numpy(float)
        cl = g['close'].to_numpy(float); va = g['value'].to_numpy(float)
        hmax = pd.Series(hi).rolling(p.win).max().to_numpy()
        base = pd.Series(cl).shift(p.win).to_numpy()
        with np.errstate(divide='ignore', invalid='ignore'):
            rise = (hmax / base - 1) if p.use_high else (cl / base - 1)
        cnt = pd.Series((va >= p.val_thresh).astype(float)).rolling(p.win).sum().to_numpy()
        ok = (np.nan_to_num(rise, nan=-1) >= p.rise) & (np.nan_to_num(cnt) >= p.val_days)
        trig = [t for t in np.flatnonzero(ok) if dates[t - p.win + 1] >= np.datetime64(p.start)]
        if not trig:
            continue
        groups = {}
        for t in trig:
            k = locate_peak(hi, t - p.win + 1, t, p)
            groups.setdefault(k, []).append(t)
        # ---- 같은 상승 국면 병합: (a) 다음 급등 시작이 현재 고점 이전이거나,
        #      (b) 다음 급등 시작 전까지 고점 대비 -30%에 도달하지 못했으면 한 국면으로 본다.
        items = sorted(((min(ts) - p.win + 1, k, ts) for k, ts in groups.items()))
        merged = []
        for s0_, k_, ts_ in items:
            if merged:
                m_s0, m_k, m_ts = merged[-1]
                same_run = s0_ <= m_k or (s0_ > m_k + 1 and lo[m_k + 1:s0_].min() > hi[m_k] * (1 - p.min_dd))
                if s0_ == m_k + 1:
                    same_run = True
                if same_run:
                    new_k = k_ if hi[k_] > hi[m_k] else m_k
                    merged[-1] = (m_s0, new_k, m_ts + ts_)
                    continue
            merged.append((s0_, k_, list(ts_)))
        groups = {k_: ts_ for _, k_, ts_ in merged}
        rows = []
        for k, ts in sorted(groups.items()):
            t0 = min(ts)
            s0 = t0 - p.win + 1
            b0 = t0 - p.win
            mc, mc_date = mc_lookup(g, b0)
            rows.append(dict(
                ticker=tk, name=g['name'].iloc[0], market=g['market'].iloc[0],
                s0=s0, b0=b0, t0=t0, k=k,
                start_date=g['date'].iloc[s0], base_date=g['date'].iloc[b0],
                base_close=cl[b0],
                rise5=float(rise[t0]), rise5_max=float(max(rise[t] for t in ts)),
                rise5_close=float(cl[t0] / cl[b0] - 1),
                avg_value_eok=float(va[s0:t0 + 1].mean() / EOK),
                big_days=int(cnt[t0]),
                peak_date=g['date'].iloc[k], peak=float(hi[k]),
                total_rise=float(hi[k] / cl[b0] - 1),
                mcap_eok=(mc / EOK if np.isfinite(mc) else np.nan), mcap_date=mc_date,
                n_trig=len(ts), n=n, peak_capped=bool(k - max(ts) >= p.hard - 1),
            ))
        # 다음 에피소드 시작일 (follow-up 오염 방지)
        for i, r in enumerate(rows):
            r['next_s0'] = rows[i + 1]['s0'] if i + 1 < len(rows) else None
        for r in rows:
            r['_g'] = g
        eps.extend(rows)
    return eps


def horizon_end(g, k, nxt, p):
    dates = g['date']
    lim = dates.iloc[k] + pd.DateOffset(months=p.months)
    n = len(g)
    e = int(np.searchsorted(dates.to_numpy(), np.datetime64(lim), side='right')) - 1
    e = min(e, n - 1)
    complete = dates.iloc[-1] >= lim
    trunc = False
    if nxt is not None and k < nxt <= e:
        e = nxt - 1
        trunc = True
        complete = False
    return e, complete, trunc


def _col(g, c):
    return g[c].to_numpy(float) if c in g.columns else np.full(len(g), np.nan)


def analyze_chain(g, k, peak, e, p: P):
    """분봉이 있는 날(hpre·hpost·lpost 값이 있는 날)은 같은 날 안의 순서를 반영:
    - 고점일: 고점이 나온 '이후'의 저가(lpost)를 하락에 포함 → 고점 당일 저점(0일)도 가능
    - 저가가 새로 나온 날: 그 저가 '이전'의 고가(hpre)로 직전 저점 대비 반등을 먼저 확인하고,
      그 저가 '이후'의 고가(hpost)로 당일 반등(+10%)을 인정
    분봉이 없는 날은 기존 일봉 방식(저점 다음 거래일부터 반등 인정) 그대로."""
    op = g['open'].to_numpy(float); hi = g['high'].to_numpy(float)
    lo = g['low'].to_numpy(float); cl = g['close'].to_numpy(float)
    n = len(g)
    ninf = -np.inf
    hpre = np.nan_to_num(_col(g, 'hpre'), nan=ninf)
    hpost = np.nan_to_num(_col(g, 'hpost'), nan=ninf)
    lpost = _col(g, 'lpost')
    lo_eff = lo.copy()
    lo_eff[k] = lpost[k] if np.isfinite(lpost[k]) else np.inf     # 고점일은 고점 이후 저가만
    hpre[k] = hpost[k] = ninf                                      # 고점일의 저가 시각은 고점 이후 저가와 다를 수 있어 쓰지 않음
    rbm = 1 + p.rb

    def scan(t0, run_min, run_i, thr):
        """t0~e 를 따라가며 러닝 최저가 대비 +rb 반등이 처음 확인되는 (저점 idx, 확인 idx)."""
        for t in range(t0, e + 1):
            l = lo_eff[t]
            if run_i >= 0 and t > run_i and (thr is None or run_min <= thr):
                hb = hi[t] if not l < run_min else hpre[t]
                if hb >= run_min * rbm:
                    return (run_i, t), run_min
            if l < run_min:
                run_min, run_i = l, t
                if (thr is None or run_min <= thr) and hpost[t] >= run_min * rbm:
                    return (t, t), run_min
        return None, run_min

    out = dict(troughs=[], end=None, reached30=False, first=None, cens_depth=np.nan)
    if e <= k:
        return out
    out['max_dd'] = float(np.min(lo_eff[k:e + 1]) / peak - 1)
    out['reached30'] = out['max_dd'] <= -p.min_dd
    # --- 1단계: 첫 반등저점
    first, _ = scan(k, np.inf, -1, peak * (1 - p.min_dd))
    if first is None:
        out['end'] = 'no_first_rebound' if out['reached30'] else 'never_30'
        out['cens_depth'] = out['max_dd']
        return out
    tr_i, cf_i = first
    L = lo_eff[tr_i]
    out['troughs'].append(dict(idx=tr_i, confirm=cf_i, low=L, dd_peak=L / peak - 1, depth_vs_ref=np.nan,
                               ref_prev=np.nan, days_from_peak=tr_i - k))
    # --- 2단계 이후: 이탈 -> 재반등 체인
    while True:
        ref = L if p.ref == 'trough' else lo[cf_i]
        u = None
        for x in range(cf_i + 1, e + 1):
            if lo[x] < ref:
                u = x; break
        seg_end = (u - 1) if u is not None else e
        cands = []
        if np.isfinite(hpost[tr_i]):
            cands.append((float(hpost[tr_i]), 0))                 # 저점 당일, 저점 이후 고가
        if seg_end >= tr_i + 1:
            j = int(np.argmax(hi[tr_i + 1:seg_end + 1]))
            cands.append((float(hi[tr_i + 1 + j]), j + 1))
        leg_high, leg_days = max(cands, key=lambda c: (c[0], -c[1])) if cands else (float(hi[tr_i]), 0)
        cur = out['troughs'][-1]
        cur.update(leg_high=leg_high, leg_ret=leg_high / L - 1, broken=u is not None,
                   break_idx=u, ref=ref, leg_days=leg_days,
                   days_to_break=(u - tr_i) if u is not None else np.nan)
        if u is None:
            out['end'] = 'no_break'; break
        nxt, run_min = scan(u, np.inf, -1, None)
        if nxt is None:
            out['end'] = 'broke_no_rebound'
            out['cens_depth_ref'] = float(lo[u:e + 1].min() / ref - 1)
            break
        tr_i, cf_i = nxt
        L = lo_eff[tr_i]
        out['troughs'].append(dict(idx=tr_i, confirm=cf_i, low=L, dd_peak=L / peak - 1,
                                   depth_vs_ref=L / ref - 1, ref_prev=ref, days_from_peak=tr_i - k))
    # 부가 지표
    for tr in out['troughs']:
        i, c = tr['idx'], tr['confirm']
        tr['same_day_range'] = float(hi[i] / tr['low'] - 1)
        a, b = i + 1, min(n - 1, i + 5)
        tr['fwd5_max_trough'] = float(hi[a:b + 1].max() / tr['low'] - 1) if b >= a else np.nan
        a2, b2 = c + 1, min(n - 1, c + 5)
        tr['fwd5_max_confirm'] = float(hi[a2:b2 + 1].max() / cl[c] - 1) if b2 >= a2 else np.nan
        tr['fwd5_close_confirm'] = float(cl[b2] / cl[c] - 1) if b2 >= a2 else np.nan
        tr['trough_date'] = g['date'].iloc[i]
        tr['confirm_date'] = g['date'].iloc[c]
    return out


# ---------------------------------------------------------------- 분할 매수 시뮬레이션
def fill_plan(g, k, peak, e, levels):
    """levels: 고점 대비 하락률(양수, 얕은->깊은). 체결일/가격 반환 (일봉 보수적)."""
    op = g['open'].to_numpy(float); lo = g['low'].to_numpy(float)
    fills = []   # (idx, price)
    j = 0
    for t in range(k + 1, e + 1):
        while j < len(levels) and lo[t] <= peak * (1 - levels[j]):
            lv = peak * (1 - levels[j])
            fills.append((t, op[t] if op[t] <= lv else lv))
            j += 1
        if j >= len(levels):
            break
    return fills


def avg_cost(prices):
    return len(prices) / sum(1.0 / x for x in prices)   # 동일 금액 분할 -> 조화평균


def stage_paths(g, k, peak, e, levels, tps, N=20):
    """단계 k(1~3) 체결 후, 다음 분할 체결 전/ N거래일 내 평단 대비 경로."""
    op = g['open'].to_numpy(float); hi = g['high'].to_numpy(float)
    lo = g['low'].to_numpy(float); cl = g['close'].to_numpy(float)
    fills = fill_plan(g, k, peak, e, levels)
    res = {}
    for s in range(1, len(levels) + 1):
        if len(fills) < s:
            continue
        f_idx = fills[s - 1][0]
        A = avg_cost([x[1] for x in fills[:s]])
        nxt_fill = fills[s][0] if len(fills) > s else None
        if nxt_fill is not None and nxt_fill == f_idx:
            continue                       # 같은 날 다음 단계도 체결 -> 이 단계는 독립 구간 없음
        w_end = min(f_idx + N, e if e > f_idx else f_idx)
        if nxt_fill is not None:
            w_end = min(w_end, nxt_fill - 1)
        # 체결일 당일은 고가/저가 선후를 알 수 없어 제외
        rng = range(f_idx + 1, w_end + 1)
        r = dict(stage=s, fill_idx=f_idx, avg=A, avg_dd=A / peak - 1, wlen=len(rng),
                 ended_by_next_fill=(nxt_fill is not None and nxt_fill - 1 <= f_idx + N),
                 hit={}, mfe=np.nan, mae=np.nan, close_ret=np.nan)
        if len(rng) == 0:
            res[s] = r; continue
        r['mfe'] = float(max(hi[t] for t in rng) / A - 1)
        r['mae'] = float(min(lo[t] for t in rng) / A - 1)
        r['close_ret'] = float(cl[w_end] / A - 1)
        for tp in tps:
            hit = False
            for t in rng:
                if hi[t] >= A * (1 + tp):
                    hit = True; break
            r['hit'][tp] = hit
        res[s] = r
    return res, fills


def simulate_dynamic(g, k, peak, e, levels, tp, N=20, stop=None):
    op = g['open'].to_numpy(float); hi = g['high'].to_numpy(float)
    lo = g['low'].to_numpy(float); cl = g['close'].to_numpy(float)
    fills = []; j = 0; last = -1
    for t in range(k + 1, e + 1):
        newfill = False
        while j < len(levels) and lo[t] <= peak * (1 - levels[j]):
            lv = peak * (1 - levels[j])
            fills.append(op[t] if op[t] <= lv else lv); j += 1; newfill = True; last = t
        if not fills:
            continue
        A = avg_cost(fills)
        if stop is not None:
            sp = A * (1 - stop)
            if lo[t] <= sp:
                px = op[t] if op[t] <= sp else sp
                return dict(stage=len(fills), ret=px / A - 1, why='stop', avg=A)
        if not newfill:
            tpp = A * (1 + tp)
            if hi[t] >= tpp:
                px = op[t] if op[t] >= tpp else tpp
                return dict(stage=len(fills), ret=px / A - 1, why='tp', avg=A)
        if t - last >= N:
            return dict(stage=len(fills), ret=cl[t] / A - 1, why='time', avg=A)
    if fills:
        A = avg_cost(fills)
        return dict(stage=len(fills), ret=cl[e] / A - 1, why='horizon', avg=A)
    return None


# ---------------------------------------------------------------- 통계 보조
def life_table(depths, events, edges):
    """depths<0 (얕->깊), events: 반등 확정 여부. edges: 내림차순 경계 [e0, e1, ...] (마지막 구간은 이하 전부)."""
    depths = np.asarray(depths, float); events = np.asarray(events, bool)
    rows = []
    for i in range(len(edges) - 1 if edges[-1] <= -1 else len(edges)):
        hi_e = edges[i]
        lo_e = edges[i + 1] if i + 1 < len(edges) else -9
        last = (i + 1 >= len(edges) - 1) and (edges[-1] <= -1)
        if i == len(edges) - 2 and edges[-1] <= -1:
            lo_e = -9
        in_b = (depths <= hi_e + 1e-12) & (depths > lo_e)
        at_risk = (depths <= hi_e + 1e-12).sum()
        ev = (in_b & events).sum(); ce = (in_b & ~events).sum()
        eff = at_risk - ce / 2
        h = ev / eff if eff > 0 else np.nan
        rows.append(dict(upper=hi_e, lower=(edges[i + 1] if i + 1 < len(edges) else None),
                         at_risk=int(at_risk), events=int(ev), censored=int(ce), hazard=h, eff=float(eff)))
    return rows


def wilson(k, n, z=1.96):
    if n <= 0:
        return (np.nan, np.nan)
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0, c - h), min(1, c + h))


def boot_ci(vals, stat=np.median, n_boot=5000, seed=7):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if len(v) < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    b = [stat(v[rng.integers(0, len(v), len(v))]) for _ in range(n_boot)]
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))
