"""키움 REST API 클라이언트 (일봉 ka10081 · 분봉 ka10080 · 종목목록 ka10099 · 토큰 au10001).
App Key/Secret 은 config.ini 에서 읽습니다. 이 파일에는 키를 적지 않습니다."""
from __future__ import annotations
import random, time
import pandas as pd
import requests

HOST = "https://api.kiwoom.com"
MARKETS = {"0": "KOSPI", "10": "KOSDAQ"}
RATE_LIMIT_CODES = ("1687", "1700")
TOKEN_BAD_CODES = ("8005", "8010")
CHART_FIELDS = {
    "dt": "date", "open_pric": "open", "high_pric": "high",
    "low_pric": "low", "cur_prc": "close",
    "trde_qty": "volume", "trde_prica": "value",
}


def to_num(x) -> float:
    """키움 숫자 파서. 음수가 '--369770' 처럼 대시 두 개로 오는 함정 처리."""
    if x is None:
        return float("nan")
    s = str(x).strip().replace(",", "")
    if not s:
        return float("nan")
    neg = s.startswith("-")
    s = s.lstrip("+-")
    if not s:
        return float("nan")
    try:
        v = float(s)
    except ValueError:
        return float("nan")
    return -v if neg else v


class Kiwoom:
    def __init__(self, key: str, sec: str, interval: float = 0.25):
        self._key, self._sec = key, sec
        self.interval = interval
        self.s = requests.Session()
        self.token: str | None = None
        self._last = 0.0
        self.refresh_token()

    def refresh_token(self) -> None:
        r = self.s.post(
            f"{HOST}/oauth2/token",
            json={"grant_type": "client_credentials",
                  "appkey": self._key, "secretkey": self._sec},
            headers={"Content-Type": "application/json;charset=UTF-8"},
            timeout=30,
        )
        try:
            j = r.json()
        except ValueError:
            raise RuntimeError(
                "서버가 정상 응답하지 않았습니다. 키움 시스템 점검 시간일 수 있습니다.\n"
                "   (보통 새벽 시간대에 점검합니다. 잠시 후 다시 시도해 주세요)")
        tok = j.get("token") or j.get("access_token")
        if not tok:
            msg = str(j.get("return_msg") or j)
            hint = ""
            if "IP" in msg.upper():
                hint = ("\n   → App Key 관리 화면에서 '현재 이 컴퓨터의 공인 IP'가 "
                        "등록돼 있는지 확인하세요.")
            raise RuntimeError(f"인증 실패: {msg}{hint}")
        self.token = tok

    def call(self, api_id: str, path: str, body: dict,
             cont_yn: str | None = None, next_key: str | None = None,
             retries: int = 6):
        gap = self.interval - (time.time() - self._last)
        if gap > 0:
            time.sleep(gap)

        for attempt in range(retries):
            h = {"Content-Type": "application/json;charset=UTF-8",
                 "authorization": f"Bearer {self.token}", "api-id": api_id}
            if cont_yn:
                h["cont-yn"] = cont_yn
            if next_key:
                h["next-key"] = next_key
            try:
                r = self.s.post(f"{HOST}{path}", json=body, headers=h, timeout=30)
            except requests.RequestException:
                time.sleep(1.5 * (attempt + 1))
                continue
            finally:
                self._last = time.time()

            try:
                j = r.json()
            except ValueError:
                time.sleep(2.0 * (attempt + 1))
                continue

            code = str(j.get("return_code", "0"))
            msg = str(j.get("return_msg", ""))
            hay = code + " " + msg

            if any(c in hay for c in RATE_LIMIT_CODES):
                time.sleep((0.2, 0.5, 1.0, 2.0, 3.0, 5.0)[min(attempt, 5)]
                           + random.random() * 0.2)
                continue
            if any(c in hay for c in TOKEN_BAD_CODES):
                self.refresh_token()
                continue
            if code not in ("0", "None", ""):
                raise RuntimeError(f"{api_id} 오류 {code}: {msg}")
            return j, r.headers.get("cont-yn", ""), r.headers.get("next-key", "")
        raise RuntimeError(f"{api_id} 재시도 초과")

    def tickers(self) -> pd.DataFrame:
        rows = []
        for mt, mname in MARKETS.items():
            j, _, _ = self.call("ka10099", "/api/dostk/stkinfo", {"mrkt_tp": mt})
            n0 = len(rows)
            for it in j.get("list", []) or []:
                rows.append({"ticker": str(it.get("code", "")).strip(),
                             "name": str(it.get("name", "")).strip(),
                             "market": mname})
            print(f"   {mname}: {len(rows)-n0:,}개")
        df = pd.DataFrame(rows).drop_duplicates("ticker")
        df["ticker"] = df["ticker"].str.replace(r"_(NX|AL)$", "", regex=True)
        df = df[df["ticker"].str.fullmatch(r"\d{6}")]
        df = df[df["ticker"].str.endswith("0")]
        df = df[~df["name"].str.contains("스팩|SPAC|리츠", case=False, na=False)]
        return df.drop_duplicates("ticker").reset_index(drop=True)

    def daily(self, ticker: str, start: str, end: str, max_pages: int = 40):
        body = {"stk_cd": ticker, "base_dt": end, "upd_stkpc_tp": "1"}
        cont = nkey = None
        out = []
        for _ in range(max_pages):
            j, cont, nkey = self.call("ka10081", "/api/dostk/chart", body, cont, nkey)
            recs = j.get("stk_dt_pole_chart_qry") or []
            if not isinstance(recs, list) or not recs:
                break
            out.extend(recs)
            if min(str(r.get("dt", "9" * 8)) for r in recs) <= start or cont != "Y":
                break
        if not out:
            return None
        df = pd.DataFrame(out)
        keep = [c for c in CHART_FIELDS if c in df.columns]
        if "dt" not in keep:
            return None
        df = df[keep].rename(columns=CHART_FIELDS)
        for c in ("open", "high", "low", "close", "volume", "value"):
            if c in df.columns:
                df[c] = df[c].map(to_num).abs()
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
        df = df[df["close"] > 0]
        df["ticker"] = ticker
        return df.sort_values("date").reset_index(drop=True)



    # ---------- 파이프라인용 추가 기능 ----------
    def stock_list(self, mrkt_tp: str) -> list[dict]:
        """ka10099 원본 목록(연속조회 포함). mrkt_tp: 0 코스피, 10 코스닥, 8 ETF."""
        out, cont, nkey = [], None, None
        for _ in range(50):
            j, cont, nkey = self.call("ka10099", "/api/dostk/stkinfo", {"mrkt_tp": mrkt_tp}, cont, nkey)
            out.extend(j.get("list", []) or [])
            if cont != "Y":
                break
        return out

    def listing(self) -> pd.DataFrame:
        """코스피·코스닥 보통주 목록 + 상장주식수(listCount). 우선주·스팩·리츠 제외."""
        rows = []
        for mt, mname in MARKETS.items():
            for it in self.stock_list(mt):
                sh = None
                for k in ("listCount", "list_count", "lst_stkcnt", "flo_stk"):
                    if it.get(k) not in (None, ""):
                        sh = to_num(it.get(k)); break
                rows.append({"ticker": str(it.get("code", "")).strip(), "name": str(it.get("name", "")).strip(),
                             "market": mname, "shares": sh})
        df = pd.DataFrame(rows)
        df["ticker"] = df["ticker"].str.replace(r"_(NX|AL)$", "", regex=True)
        df = df[df["ticker"].str.fullmatch(r"\d{6}")]
        df = df[df["ticker"].str.endswith("0")]
        df = df[~df["name"].str.contains("스팩|SPAC|리츠", case=False, na=False)]
        return df.drop_duplicates("ticker").reset_index(drop=True)

    def etf_codes(self) -> set[str]:
        try:
            return {str(it.get("code", "")).strip()[:6] for it in self.stock_list("8")}
        except Exception:
            return set()

    def minute(self, ticker: str, start: str, scope: str = "1", max_pages: int = 300):
        """ka10080 분봉. start(YYYYMMDD) 이전까지 또는 데이터가 끝날 때까지 거슬러 받음.
        키움이 과거 몇 년치 분봉을 주는지는 확인되지 않았으므로 받은 최초 시각을 함께 돌려줍니다."""
        body = {"stk_cd": ticker, "tic_scope": scope, "upd_stkpc_tp": "1"}
        cont = nkey = None
        out = []
        for _ in range(max_pages):
            j, cont, nkey = self.call("ka10080", "/api/dostk/chart", body, cont, nkey)
            recs = j.get("stk_min_pole_chart_qry")
            if recs is None:
                recs = next((v for v in j.values() if isinstance(v, list)), [])
            if not recs:
                break
            out.extend(recs)
            if min(str(r.get("cntr_tm", "9" * 14))[:8] for r in recs) < start or cont != "Y":
                break
        if not out:
            return None
        df = pd.DataFrame(out)
        m = {"cntr_tm": "time", "open_pric": "open", "high_pric": "high", "low_pric": "low",
             "cur_prc": "close", "trde_qty": "volume"}
        df = df[[c for c in m if c in df.columns]].rename(columns=m)
        for c in ("open", "high", "low", "close", "volume"):
            if c in df.columns:
                df[c] = df[c].map(to_num).abs()
        df["time"] = pd.to_datetime(df["time"].astype(str).str[:12], format="%Y%m%d%H%M", errors="coerce")
        df = df.dropna(subset=["time"]).drop_duplicates("time").sort_values("time")
        df["ticker"] = ticker
        return df.reset_index(drop=True)
