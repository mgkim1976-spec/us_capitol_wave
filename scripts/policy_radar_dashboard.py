#!/usr/bin/env python3
"""CAPITOL WAVE — 의회·정책자본 & ETF 모니터 (발행물급 UI: Economist/WSJ/FT풍).
주의: 매매 신호 아님 — 신고 stale·copy 알파 없음. 정책/테마 '맥락' 용도.
출력: dashboard/capitol_wave.html"""
import os, json, glob, datetime, numpy as np, pandas as pd, yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go, plotly.io as pio
from plotly.subplots import make_subplots

HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
OUT=os.path.join(HERE,"dashboard"); os.makedirs(OUT,exist_ok=True); SECF=os.path.join(DATA,"ticker_sectors.csv")
df=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv"),parse_dates=["transaction_date"])
df["amount"]=pd.to_numeric(df["amount"],errors="coerce"); df=df.dropna(subset=["amount","transaction_date"])
df["signed"]=np.where(df.type=="P",df.amount,np.where(df.type=="S",-df.amount,0))

# ---- 디자인 토큰 / 차트 테마 ----
NAVY,RED,GRAY,PURP="#2166AC","#B2182B","#5a5a5a","#762A83"
PAL=["#2166AC","#B2182B","#1b7837","#D68910","#762A83","#2a7e8c","#8c6d31","#c0504d","#4d7298","#999999","#5b2c6f"]
SANS="-apple-system,'Helvetica Neue',Arial,'Apple SD Gothic Neo',sans-serif"
def style(fig,h=380,legend=True):
    fig.update_layout(template="plotly_white",height=h,font=dict(family=SANS,size=12,color="#222"),
        margin=dict(l=8,r=14,t=10,b=8),colorway=PAL,title="",
        legend=dict(orientation="h",y=1.04,x=0,font=dict(size=11)) if legend else dict(),
        plot_bgcolor="white",paper_bgcolor="white")
    fig.update_xaxes(showgrid=False,linecolor="#ccc"); fig.update_yaxes(gridcolor="#eee",zerolinecolor="#ccc")
    return fig
# ---- FT풍 자동 직접라벨 + 이벤트 주석 ----
EVENTS={"2020-02-19":"코로나 고점","2022-01-03":"’22 약세장","2023-03-10":"SVB 파산",
        "2024-11-06":"트럼프 당선","2025-01-20":"트럼프 취임","2025-04-02":"해방의날 관세","2025-08-27":"인텔 정부지분"}
def end_labels(fig,series,mingap):
    """series=[(name,x_last,y_last,color)] → 선 끝에 라벨, 범례 제거(겹침 방지 y조정)."""
    series=sorted(series,key=lambda s:s[2]); ys=[float(s[2]) for s in series]
    for i in range(1,len(ys)):
        if ys[i]-ys[i-1]<mingap: ys[i]=ys[i-1]+mingap
    for (nm,xl,_,col),y in zip(series,ys):
        fig.add_annotation(x=xl,y=y,text="  "+nm,showarrow=False,xanchor="left",yanchor="middle",
            font=dict(color=col,size=11,family=SANS))
    fig.update_layout(showlegend=False,margin=dict(l=8,r=118,t=10,b=8))
def events_dates(fig,xmin,xmax,ytop):
    for d,lab in EVENTS.items():
        dt=pd.Timestamp(d)
        if xmin<=dt<=xmax:
            fig.add_vline(x=dt,line=dict(color="#e4e4e4",width=1))
            fig.add_annotation(x=dt,y=ytop,text=lab,showarrow=False,textangle=-90,xanchor="right",
                yanchor="top",xshift=-2,font=dict(size=8.5,color="#a8a8a8"))
def events_quarters(fig,qindex):
    qof=lambda d:f"{pd.Timestamp(d).year}Q{(pd.Timestamp(d).month-1)//3+1}"
    for d,lab in EVENTS.items():
        qc=qof(d)
        if qc in set(qindex):
            fig.add_annotation(x=qc,y=1,yref="paper",text=lab,showarrow=False,textangle=-90,
                xanchor="right",yanchor="top",font=dict(size=8,color="#a8a8a8"))

# ---- 섹터/테마 매핑 ----
CRYPTO={"IBIT","BITB","BITO","FBTC","GBTC","ARKB","BTCO","ETHA","BITW","MSTR","COIN","BITX"}
ETFS={"SPY","IWB","IWM","QQQ","VOO","IVV","PDBC","VTI","DIA","SCHD","ECOM","HIYS","BSTZ","PCLPX","FWONK"}
KOR={"Technology":"기술/반도체","Financial Services":"금융","Healthcare":"헬스케어","Energy":"에너지","Industrials":"산업재",
     "Consumer Cyclical":"경기소비재","Consumer Defensive":"필수소비재","Communication Services":"커뮤니케이션",
     "Basic Materials":"소재","Real Estate":"부동산","Utilities":"유틸리티"}
MANUAL={"FB":"커뮤니케이션","ATVI":"커뮤니케이션","ZAYO":"커뮤니케이션","QRTEA":"커뮤니케이션","LSXMK":"커뮤니케이션","LBRDK":"커뮤니케이션","RUM":"커뮤니케이션","CHTR":"커뮤니케이션","DISCA":"커뮤니케이션","WBD":"커뮤니케이션","SQ":"금융","DFS":"금융","BRK.B":"금융","FRC":"금융","SIVB":"금융","ICE":"금융","X":"소재","CLF":"소재","K":"필수소비재","MNST":"필수소비재","MDLZ":"필수소비재","HBI":"경기소비재","CMG":"경기소비재","ARNA":"헬스케어","BSX":"헬스케어","BMY":"헬스케어","FEYE":"기술/반도체","CTXS":"기술/반도체","WTT":"기술/반도체","CDLX":"기술/반도체","MDB":"기술/반도체","DDOG":"기술/반도체","CRWV":"기술/반도체","SMCI":"기술/반도체","AVGO":"기술/반도체"}
uni=df.groupby("ticker").amount.sum().sort_values(ascending=False).head(700).index.tolist()
cache=pd.read_csv(SECF).set_index("ticker")["sector"].to_dict() if os.path.exists(SECF) else {}
todo=[t for t in uni if t not in cache and t not in CRYPTO and t not in ETFS and t not in MANUAL]
if todo:
    print(f"섹터 조회 {len(todo)}개…")
    def gs(t):
        try: return t,yf.Ticker(t).info.get("sector")
        except Exception: return t,None
    with ThreadPoolExecutor(max_workers=12) as ex:
        for t,s in ex.map(gs,todo): cache[t]=s
    pd.Series(cache,name="sector").rename_axis("ticker").to_csv(SECF)
def theme(t):
    if t in CRYPTO: return "암호화폐"
    if t in ETFS: return "ETF/펀드"
    if t in MANUAL: return MANUAL[t]
    s=cache.get(t); return KOR[s] if isinstance(s,str) and s in KOR else "기타"
df["theme"]=df.ticker.map(theme); df["q"]=df.transaction_date.dt.to_period("Q").astype(str)
CUT=df.transaction_date.max()-pd.Timedelta(days=180); recent=df[df.transaction_date>=CUT]; buys=df[df.type=="P"]
def tbl(dfx,cols):
    h="".join(f"<th>{c}</th>" for c in cols)
    rows="".join("<tr>"+"".join(f"<td>{r[c]}</td>" for c in cols)+"</tr>" for _,r in dfx.iterrows())
    return f"<table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table>"

# ===== ETF 가격·정권매칭 =====
px=yf.download(["NANC","GOP","SPY"],start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
SWITCH="2025-01-17"; n=px/px.iloc[0]*100; si=px.index.searchsorted(pd.Timestamp(SWITCH))
regime=n["NANC"].copy(); regime.iloc[si:]=n["NANC"].iloc[si]*(px["GOP"].iloc[si:]/px["GOP"].iloc[si])
figE=go.Figure()
figE.add_scatter(x=n.index,y=regime,name="정권매칭(NANC→GOP)",line=dict(color=PURP,width=3))
figE.add_scatter(x=n.index,y=n["NANC"],name="NANC 매수보유",line=dict(color=NAVY,width=1.5))
figE.add_scatter(x=n.index,y=n["GOP"],name="GOP 매수보유",line=dict(color=RED,width=1.5))
figE.add_scatter(x=n.index,y=n["SPY"],name="S&P500",line=dict(color=GRAY,width=1.5,dash="dot"))
style(figE,440)
_ym=float(max(regime.max(),n.max().max()))
end_labels(figE,[("정권매칭",n.index[-1],regime.iloc[-1],PURP),("NANC",n.index[-1],n['NANC'].iloc[-1],NAVY),
                 ("GOP",n.index[-1],n['GOP'].iloc[-1],RED),("S&P500",n.index[-1],n['SPY'].iloc[-1],GRAY)],mingap=_ym*0.05)
events_dates(figE,n.index[0],n.index[-1],_ym*0.99)
def ret(s,a=None,b=None):
    s=s.copy()
    if a: s=s[s.index>=pd.Timestamp(a)]
    if b: s=s[s.index<=pd.Timestamp(b)]
    return (s.iloc[-1]/s.iloc[0]-1)*100
era=pd.DataFrame([{"구간":l,"NANC":f"{ret(px['NANC'],a,b):+.0f}%","GOP":f"{ret(px['GOP'],a,b):+.0f}%","S&P500":f"{ret(px['SPY'],a,b):+.0f}%"}
    for l,a,b in [("바이든기 (~25.01.17)",None,SWITCH),("트럼프기 (25.01.17~)",SWITCH,None),("상장후 누적",None,None)]])
era_tbl=tbl(era,["구간","NANC","GOP","S&P500"]); regime_tot=(regime.iloc[-1]/regime.iloc[0]-1)*100

# ===== 정권교체 검정 (regime mimic, 상원전용) — '여당 우위' 신화 반증 =====
figR=None; rgm_tbl=""; rgm_w=0
_rgf=os.path.join(DATA,"regime_mimic_senate.csv")
if os.path.exists(_rgf):
    rgm=pd.read_csv(_rgf).dropna(subset=["SPY","여당포트"]).copy()
    _rlab={"트럼프1기(R)":"트럼프1기<br><sub>·AI 이전</sub>","바이든(D)":"바이든<br><sub>·AI</sub>","트럼프2기(R)":"트럼프2기<br><sub>·AI</sub>"}
    rgm["lab"]=rgm.정권.map(lambda s:_rlab.get(s,s)); rgm_w=int((rgm.여당vsSPY>0).sum())
    figR=go.Figure()
    figR.add_bar(x=rgm.lab,y=rgm.여당vsSPY,name="여당 모방포트 − SPY",
        marker_color=["#1b7837" if v>=0 else RED for v in rgm.여당vsSPY],
        texttemplate="%{y:+.0f}%p",textposition="outside",textfont_size=10,cliponaxis=False)
    figR.add_bar(x=rgm.lab,y=rgm.상원vsSPY,name="상원전체(정당무관) − SPY",marker_color="#c2c2c2",
        texttemplate="%{y:+.0f}%p",textposition="outside",textfont_size=9,cliponaxis=False)
    figR.update_layout(barmode="group"); style(figR,360)
    figR.update_yaxes(ticksuffix="%p",title="모방포트 − SPY 초과(%p)"); figR.add_hline(y=0,line=dict(color="#999",width=1))
    def _pc(v): return f"{v:+.0f}%" if pd.notna(v) else "—"
    rgm_tbl=tbl(pd.DataFrame([{"정권":r.정권.replace("(R)"," ·공화").replace("(D)"," ·민주"),"여당":r.여당,
        "민주 모방포트":_pc(r.D포트),"공화 모방포트":_pc(r.R포트),"상원전체":_pc(r.상원전체),"SPY":_pc(r.SPY)} for _,r in rgm.iterrows()]),
        ["정권","여당","민주 모방포트","공화 모방포트","상원전체","SPY"])

# ===== ETF 섹터·종목 비교 =====
SK={"technology":"기술","communication_services":"커뮤니케이션","financial_services":"금융","healthcare":"헬스케어","energy":"에너지","industrials":"산업재","consumer_cyclical":"경기소비재","consumer_defensive":"필수소비재","basic_materials":"소재","real_estate":"부동산","realestate":"부동산","utilities":"유틸리티"}
def etf_data(t):
    fd=yf.Ticker(t).funds_data
    sec={SK.get(k,k):round(v*100,1) for k,v in fd.sector_weightings.items() if v and v>0}
    top={str(i).replace("-","."):round(float(p)*100,2) for i,p in fd.top_holdings["Holding Percent"].items()}
    return sec,top
nanc_sec,nanc_top=etf_data("NANC"); gop_sec,gop_top=etf_data("GOP")
secs=sorted(set(nanc_sec)|set(gop_sec),key=lambda s:-(nanc_sec.get(s,0)+gop_sec.get(s,0)))
figS=go.Figure()
figS.add_bar(y=secs,x=[nanc_sec.get(s,0) for s in secs],name="NANC(민주)",orientation="h",marker_color=NAVY)
figS.add_bar(y=secs,x=[gop_sec.get(s,0) for s in secs],name="GOP(공화)",orientation="h",marker_color=RED)
figS.update_layout(barmode="group"); style(figS,400); figS.update_xaxes(ticksuffix="%")
figS.update_traces(texttemplate="%{x:.0f}",textposition="outside",textfont_size=9,cliponaxis=False)
# 상위10 테이블: N-PORT 최신분기 비중 + 전분기Δ + 주가(3M·12M)
def _topnport(fund):
    pers=sorted(glob.glob(os.path.join(DATA,"nport_holdings",f"{fund}_2*.csv")))
    if not pers: return None,None,None
    cur=pd.read_csv(pers[-1]).set_index("ticker")
    prev=pd.read_csv(pers[-2]).set_index("ticker") if len(pers)>=2 else None
    return cur.sort_values("pct",ascending=False).head(10), prev, os.path.basename(pers[-1])[len(fund)+1:-4]
nanc_t,nanc_prev,nanc_pe=_topnport("NANC"); gop_t,gop_prev,gop_pe=_topnport("GOP")
_alltk=sorted(set(list(nanc_t.index)+list(gop_t.index))) if nanc_t is not None else []
_pp=yf.download([t.replace(".","-") for t in _alltk],start="2024-11-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"] if _alltk else pd.DataFrame()
def _ret(tk,days):
    col=tk.replace(".","-")
    if col not in _pp: return None
    s=_pp[col].dropna()
    return (s.iloc[-1]/s.iloc[-days-1]-1)*100 if len(s)>days else None
def _clr(v,suf="%"):
    if v is None: return "—"
    return f"<span style='color:{'#1b7837' if v>=0 else '#b2182b'}'>{v:+.0f}{suf}</span>"
def build_top(top,prev):
    if top is None: return "<p class=dek>N-PORT 데이터 없음</p>"
    rows=""
    for tk,r in top.iterrows():
        if prev is None: d="—"
        elif tk in prev.index: d=_clr(round(r.pct-float(prev.pct.get(tk,0)),2),"%p")
        else: d="<span style='color:#1b7837'>🆕신규</span>"
        rows+=f"<tr><td><b>{tk}</b></td><td>{r.pct:.1f}%</td><td>{d}</td><td>{_clr(_ret(tk,63))}</td><td>{_clr(_ret(tk,252))}</td></tr>"
    return f"<table><thead><tr><th>종목</th><th>비중</th><th>전분기Δ</th><th>주가3M</th><th>주가12M</th></tr></thead><tbody>{rows}</tbody></table>"
nanc_top_html=build_top(nanc_t,nanc_prev); gop_top_html=build_top(gop_t,gop_prev)

# ===== N-PORT 보유 변화 + 추이 =====
nport_html=""; figT=None
trends={}
for etf,col in [("NANC",NAVY),("GOP",RED)]:
    tsf=os.path.join(DATA,"nport_holdings",f"{etf}_timeseries.csv")
    if os.path.exists(tsf): trends[etf]=pd.read_csv(tsf)
    fp=os.path.join(DATA,"nport_holdings",f"{etf}_changes.json")
    if not os.path.exists(fp): continue
    d=json.load(open(fp))
    def L(items,f): return ", ".join(f(t,v) for t,v in items[:14]) or "—"
    nport_html+=f"<h4>{etf} <span class=q>({d['기간']})</span></h4><div class=chg>"
    nport_html+=f"<span class=new>🆕 신규 {len(d['신규'])}</span> {L(d['신규'],lambda t,v:f'{t} +{v}%')}<br>"
    nport_html+=f"<span class=liq>❌ 청산 {len(d['청산'])}</span> {L(d['청산'],lambda t,v:t)}<br>"
    nport_html+=f"<span class=up>▲ 확대</span> {L(d['확대'],lambda t,v:f'{t} {v:+}%p')}<br>"
    nport_html+=f"<span class=dn>▼ 축소</span> {L(d['축소'],lambda t,v:f'{t} {v:+}%p')}</div>"
if trends:
    figT=go.Figure()
    for etf,col in [("NANC",NAVY),("GOP",RED)]:
        if etf in trends: figT.add_scatter(x=trends[etf].period,y=trends[etf]["종목수"],name=etf,line=dict(color=col,width=2),mode="lines+markers")
    style(figT,300); figT.update_yaxes(title="보유 종목 수")
    end_labels(figT,[(etf,trends[etf].period.iloc[-1],float(trends[etf]["종목수"].iloc[-1]),col) for etf,col in [("NANC",NAVY),("GOP",RED)] if etf in trends],mingap=8)

# ===== 의회 순매수 섹터 틸트 =====
order=recent.groupby("theme").amount.sum().sort_values(ascending=False).index.tolist()
D=(recent[recent.party=="D"].groupby("theme").signed.sum()/1e6).reindex(order).fillna(0)
R=(recent[recent.party=="R"].groupby("theme").signed.sum()/1e6).reindex(order).fillna(0)
fig1=go.Figure()
fig1.add_bar(y=order,x=D.values,name="민주",orientation="h",marker_color=NAVY)
fig1.add_bar(y=order,x=R.values,name="공화",orientation="h",marker_color=RED)
fig1.update_layout(barmode="group"); style(fig1,400); fig1.update_xaxes(ticksuffix="M")
hot=recent[recent.type=="P"].groupby(["theme","ticker"]).agg(m=("member","nunique"),b=("amount",lambda x:round(x.sum()/1e6,2))).reset_index()
hot=hot.sort_values("b",ascending=False).groupby("theme").head(3)
hot=hot[hot.theme.isin([t for t in order if t not in("기타","ETF/펀드")][:5])].sort_values(["theme","b"],ascending=[True,False])
hot=hot.rename(columns={"theme":"섹터","ticker":"종목","m":"의원수","b":"매수$M"}); hot_tbl=tbl(hot,["섹터","종목","의원수","매수$M"])
fbd=buys.groupby("ticker").transaction_date.min(); newt=fbd[fbd>=df.transaction_date.max()-pd.Timedelta(days=270)].index
emg=buys[buys.ticker.isin(newt)].groupby("ticker").agg(m=("member","nunique"),b=("amount",lambda x:round(x.sum()/1e6,2))).reset_index()
emg["섹터"]=emg.ticker.map(theme); emg=emg[emg.m>=2].sort_values("b",ascending=False).head(10).rename(columns={"ticker":"종목","m":"의원수","b":"매수$M"})
emg_tbl=tbl(emg[["종목","섹터","의원수","매수$M"]],["종목","섹터","의원수","매수$M"]) if len(emg) else "<p class=dek>해당 없음</p>"

piv=buys.pivot_table(index="q",columns="theme",values="amount",aggfunc="sum").fillna(0)/1e6
piv=piv[[c for c in order if c in piv.columns]]
fig2=go.Figure()
for c in piv.columns: fig2.add_bar(x=piv.index,y=piv[c],name=c)
fig2.update_layout(barmode="stack"); style(fig2,360); fig2.update_yaxes(ticksuffix="M")
q=df.groupby("q").apply(lambda x:pd.Series({"순매수$M":x.signed.sum()/1e6,"매도비중%":100*(x.type=="S").sum()/max((x.type.isin(["P","S"])).sum(),1)}),include_groups=False)
_spyf=yf.download("SPY",start="2019-01-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].squeeze()  # 전 구간(2019~) — fig3 SPY 일부만 보이던 버그 수정
spq=_spyf.resample("QE").last(); spq.index=spq.index.to_period("Q").astype(str); q["SPY"]=q.index.map(spq.to_dict())
fig3=make_subplots(specs=[[{"secondary_y":True}]])
fig3.add_bar(x=q.index,y=q["순매수$M"],name="순매수$M",marker_color="#cfcfcf")
fig3.add_scatter(x=q.index,y=q["매도비중%"],name="매도비중%",line=dict(color=RED,width=1.5))
fig3.add_scatter(x=q.index,y=q["SPY"],name="SPY(우)",line=dict(color=GRAY,dash="dot"),secondary_y=True)
style(fig3,340); events_quarters(fig3,list(q.index))
oth=df[df.theme=="기타"].groupby("ticker").amount.sum().sort_values(ascending=False).head(10)
oth_tbl=tbl(pd.DataFrame({"종목":oth.index,"누적$M":(oth.values/1e6).round(2)}),["종목","누적$M"])

# ===== 다가오는 촉매 (독립: 보유종목 실적 + 연준 FOMC + 프로젝트 내 정책일정) =====
today=datetime.date.today(); cal_rows=[]
hold_map={}
for fund,top in [("NANC",nanc_t),("GOP",gop_t)]:
    if top is None: continue
    for tk,r in top.iterrows(): hold_map.setdefault(tk,[]).append(f"{fund} {r.pct:.0f}%")
for tk in hold_map:  # 1) 보유 상위종목 실적 (yfinance, 라이브)
    try:
        ed=yf.Ticker(tk.replace(".","-")).calendar.get("Earnings Date")
        if ed and ed[0]>=today and (ed[0]-today).days<=120:
            cal_rows.append((ed[0],f"{tk} 실적","실적","·".join(hold_map[tk])))
    except Exception: pass
try:  # 2) FOMC 금리결정 (연준 공식 페이지 자동 파싱)
    import urllib.request as _u, re as _re
    _h=_u.urlopen(_u.Request("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",headers={"User-Agent":"Mozilla/5.0 research"}),timeout=20).read().decode("utf-8","ignore")
    _p=_re.split(r'(20\d\d)\s*FOMC Meetings',_h)
    for _i in range(1,len(_p)-1,2):
        _yr=int(_p[_i]); _sec=_p[_i+1].split("FOMC Meetings")[0]
        for _m,(_d1,_d2) in zip(_re.findall(r'fomc-meeting__month[^>]*>(?:\s*<[^>]+>)*\s*([A-Z][a-z]+)',_sec),
                                _re.findall(r'fomc-meeting__date[^"]*"[^>]*>\s*(\d+)[-/](\d+)',_sec)):
            try:
                _dt=datetime.datetime.strptime(f"{_m} {_d2} {_yr}","%B %d %Y").date()
                if today<=_dt<=today+datetime.timedelta(days=120): cal_rows.append((_dt,"FOMC 금리결정","정책","전체 시장(금리)"))
            except Exception: pass
except Exception: pass
# 3) 프로젝트 내 편집형 정책일정 — CHIPS·관세·암호화폐 입법 등 직접 갱신 (형식 예시)
POLICY_DATES={
  # "2026-07-15":"상호관세 재검토 시한",
  # "2026-09-30":"CHIPS 차기 배분/예산 마감",
}
for _d,_nm in POLICY_DATES.items():
    try:
        _dt=datetime.date.fromisoformat(_d)
        if today<=_dt<=today+datetime.timedelta(days=120): cal_rows.append((_dt,_nm,"정책","전체 시장"))
    except Exception: pass
cal_rows=sorted(cal_rows)[:14]
if cal_rows:
    rws="".join(f"<tr><td>{d}</td><td><b>D-{(d-today).days}</b></td><td>{nm}</td><td>{cat}</td><td>{aff}</td></tr>" for d,nm,cat,aff in cal_rows)
    cal_html=f"<table><thead><tr><th>날짜</th><th>D-day</th><th>이벤트</th><th>구분</th><th>영향(보유비중)</th></tr></thead><tbody>{rws}</tbody></table>"
else:
    cal_html="<p class=dek>향후 120일 내 보유종목 실적·FOMC 일정 없음. (정책일정은 스크립트 내 POLICY_DATES에 직접 추가 가능)</p>"

# === 정책 플레이북(이벤트스터디 참조) + 최근 규제이벤트 자동피드 ===
AG2SEC={"Commerce":"기술/반도체","Energy Department":"에너지","Environmental":"에너지/소재","Health and Human":"헬스케어","Food and Drug":"헬스케어","Treasury":"금융","Securities":"금융","Defense":"산업재/방산","Federal Communications":"커뮤니케이션","Interior":"에너지/소재","Transportation":"산업재"}
import urllib.request as _ur
_since=(datetime.date.today()-datetime.timedelta(days=90)).isoformat(); reg_rows=[]
try:
    _u=f"https://www.federalregister.gov/api/v1/documents.json?conditions%5Btype%5D=RULE&conditions%5Bsignificant%5D=1&conditions%5Bpublication_date%5D%5Bgte%5D={_since}&per_page=25&order=newest&fields%5B%5D=title&fields%5B%5D=publication_date&fields%5B%5D=agencies"
    _j=json.loads(_ur.urlopen(_ur.Request(_u,headers={"User-Agent":"research"}),timeout=20).read())
    for r in _j.get("results",[]):
        ags=[a.get("name","") for a in r.get("agencies",[])]
        s=next((v for a in ags for k,v in AG2SEC.items() if k in a),"기타")
        reg_rows.append({"날짜":r.get("publication_date"),"섹터":s,"기관":(", ".join(ags))[:20],"중요규칙":r.get("title","")[:58]})
        if len(reg_rows)>=12: break
except Exception: pass
reg_html=tbl(pd.DataFrame(reg_rows),["날짜","섹터","기관","중요규칙"]) if reg_rows else "<p class=dek>최근 90일 중요규칙 조회 없음</p>"
PLAYBOOK=tbl(pd.DataFrame([
 {"정책 유형":"반도체보조금·CHIPS","대상섹터":"반도체(SMH)","다년 경향":"강한 +(예 +324%)","주의":"AI와 합작 — 정책단독 분리불가"},
 {"정책 유형":"관세(수입보호)","대상섹터":"철강(SLX)+ · 수입테크−","다년 경향":"철강 +41%(순수)","주의":"테크 단기− 후 회복"},
 {"정책 유형":"국방예산·지정학","대상섹터":"방산(ITA)","다년 경향":"+","주의":"NDAA·전쟁·지원예산"},
 {"정책 유형":"정부지분·구제","대상섹터":"해당기업","다년 경향":"사례적 大(인텔 +367%)","주의":"n=소수, 일화적"},
 {"정책 유형":"크립토 우호 EO","대상섹터":"암호화폐","다년 경향":"단기+·고변동","주의":"2025 IBIT는 오히려 축소"},
 {"정책 유형":"약가인하(IRA)","대상섹터":"제약(IBB)","다년 경향":"−(단 회복)","주의":"피해정책 다년엔 무력화"},
]),["정책 유형","대상섹터","다년 경향","주의"])

# ===== 이해상충 워치 (6층 nexus) =====
try:
    nx=pd.read_csv(os.path.join(DATA,"conflict_nexus.csv"))
    _n3=nx[nx.PAC후원=="예"]
    nexus_sum=f"감독 섹터를 거래한 충돌 <b>{len(nx)}건</b>·의원 {nx.의원.nunique()}명 중, 거래+관할위원회+그 기업 PAC 후원이 겹치는 <b>3중충돌 {len(_n3)}건</b>(의원 {_n3.의원.nunique()}명)"
    _by=_n3.groupby(["의원","정당"]).agg(종목수=("종목","nunique"),충돌종목=("종목",lambda x:"·".join(sorted(set(x))[:8]))).reset_index().sort_values("종목수",ascending=False)
    nexus_mem=tbl(_by.head(10),["의원","정당","종목수","충돌종목"])
    _top=nx.sort_values(["PAC후원","score"],ascending=[False,False]).head(14).copy(); _top["관할위원회"]=_top.관할위원회.astype(str).str.slice(0,30)
    nexus_top=tbl(_top[["의원","정당","섹터","종목","관할위원회","거래수","기업로비M","PAC후원"]],["의원","정당","섹터","종목","관할위원회","거래수","기업로비M","PAC후원"])
except Exception:
    nexus_sum="(conflict_nexus.csv 없음 — conflict_nexus.py 먼저 실행)"; nexus_mem=nexus_top=""

# ===== HTML (발행물 스타일) =====
H=lambda f,first=False:pio.to_html(f,full_html=False,include_plotlyjs="inline" if first else False,config={"displayModeBar":False})
asof=df.transaction_date.max().date(); cov=df[df.theme=="기타"].amount.sum()/df.amount.sum()
def sec(kicker,head,dek,body,src=""):
    s=f"<p class=src>{src}</p>" if src else ""
    return f"<section><div class=kicker>{kicker}</div><h2>{head}</h2><p class=dek>{dek}</p>{body}{s}</section>"
inpow_now="공화(GOP)"  # 현재 정권
body=f"""
{sec("ETF · 정권 전략","여당 ETF를 갈아탄 전략이 매수보유·S&P500을 앞섰다",
 f"상장(2023-02)부터 100. 바이든기 NANC→트럼프 취임 시 GOP로 전환한 가상전략은 <b>{regime_tot:+.0f}%</b>로 NANC({ret(px['NANC']):+.0f}%)·GOP({ret(px['GOP']):+.0f}%)·S&P500({ret(px['SPY']):+.0f}%)을 모두 상회. 단 정권교체 <b>1회</b>·사후관점·전환비용 무시한 <b>패턴 예시</b>이며, 본질은 정치가 아니라 'AI 강세섹터 적중'이다. <b>↓ 아래 '정권교체 검정'에서 4정권으로 늘리면 이 우위가 깨짐을 확인.</b>",
 H(figE,True)+era_tbl,"가격: yfinance 조정종가 · 전환일=트럼프 취임 직전 거래일(2025-01-17)")}
{sec("정권교체 검정 · 여당 우위 신화","정권을 늘리면 '여당이 이긴다'는 깨진다",
 f"위 +{regime_tot:.0f}%는 ETF 상장 후 <b>단 1회</b> 교체의 사후 패턴. ETF 이전(2014~)까지 거슬러 각 정당 의원의 거래로 정권별 모방포트를 복원하니 — 여당 모방포트가 SPY를 이긴 건 <b>3정권 중 {rgm_w}번(바이든)뿐.</b> AI 이전 트럼프1기엔 여당(공화)이 시장(+83%)·야당(민주 +149%)에 <b>대패</b>. 게다가 <b>정당 무관 '상원전체' 포트는 세 정권 모두 SPY 미달</b>(아래 회색) — 'STOCK Act(2012) 이후 의원 초과수익 소멸'이라는 학술 컨센서스(Huang-Xuan 2023)와 정합. 민주 모방포트만 전 정권 SPY 상회하나 §섹터분해상 <b>스킬 아닌 테크 베타</b>. 즉 '여당'이 아니라 <b>테크편향 민주포트가 테크 이기는 국면마다 이긴 것</b>이고, 정권매칭 우위는 그게 AI붐과 겹친 우연이다.",
 (H(figR)+rgm_tbl if figR is not None else "<p class=dek>regime_mimic_senate.csv 없음 — scripts/regime_mimic_senate.py 먼저 실행</p>"),
 "상원 eFD 모방포트(시가가중·직전3년 누적순매수 보유, 정권말까지). 생존편향(상폐 제외)·소수종목 집중 한계 — 정성적 방향만. 오바마2기는 2014 이전 데이터 부재로 미검정. data/regime_mimic_senate.csv")}
{sec("이 데이터의 진짜 산출물 · 이해상충 nexus","감독·거래·후원이 겹치는 의원 — 거버넌스 투명성",
 f"<b>거래 알파가 없다면(↑), 이 6층 데이터의 진짜 가치는 여기 있다 — 이해상충·거버넌스 투명성.</b> {nexus_sum}. 한 의원이 그 섹터를 감독(소속 위원회) + 그 종목 거래 + 그 기업 PAC 후원까지 받으면 <b>3중충돌</b>. <b>매매 신호 아님 · 정황이지 불법 증거 아님</b> — 행동주의·거버넌스 압박의 정량 근거로 쓴다.",
 f"<b>다중 3중충돌 의원 (감독섹터를 여러 종목 거래+후원)</b>{nexus_mem}<b>상위 nexus (PAC후원·로비 결합순)</b>{nexus_top}",
 "거래=PTR · 위원회=현직 명부 · 로비=LDA · 자금=FEC(.env 키). 현재 스냅샷·성/이름 매칭·정황")}
{sec("집중 후보","지금은 트럼프 집권 — 여당 ETF는 GOP",
 f"현재 정권={inpow_now} → 집중 후보는 GOP 기준으로 보되 NANC와 대비. 상위10에 <b>전분기 대비 비중 변화(Δ)</b>와 <b>주가 성과(3·12개월)</b>를 함께 표기 — 펀드가 늘리는 종목인지, 그게 실제로 오르는지 한눈에. GOP는 산업재·에너지·금융 비중이 높고 그 안의 AI인프라(FIX·INTC·ANET)가 성과를 견인.",
 H(figS)+f"<div class=two><div><b>NANC(민주) 상위10 <span class=q>(N-PORT {nanc_pe})</span></b>{nanc_top_html}</div><div><b>GOP(공화) 상위10 <span class=q>(N-PORT {gop_pe})</span></b>{gop_top_html}</div></div>",
 "섹터=yfinance, 상위10·비중=SEC N-PORT 최신분기, 전분기Δ=직전 N-PORT 대비, 주가=yfinance(3·12개월)")}
{sec("다가오는 촉매 · D-day","집중 보유 종목의 실적·FOMC가 언제 베팅을 시험하나",
 "보유 상위종목의 실적일과 FOMC 금리결정을 D-day로. <b>매매 신호가 아니라 타이밍·리스크용</b> — 이날들이 '정책→섹터 베타'가 재평가되는 시점이다. 예: GOP의 INTC·FIX 실적일 = AI인프라 베팅이 시험받는 날, FOMC = 전 포지션의 금리 재평가. 임박한 이벤트 전 신규진입은 사이징을 줄이거나 이후로 미루는 판단에 활용.",
 cal_html,"실적=yfinance(라이브) · FOMC=연준 공식일정 자동 · 정책일정=프로젝트 내 편집(POLICY_DATES). 외부 프로젝트 의존 없음.")}
{sec("ETF 보유 변화 · SEC N-PORT","두 펀드가 분기 동안 무엇을 사고 버렸나",
 f"전 종목(상위10 아님) 기준 신규·청산·확대·축소. NANC는 보유를 계속 압축(167→99종목), GOP는 친크립토 정책에도 <b>크립토(IBIT)를 줄이고</b> AI인프라(FIX)·에너지(COP)를 늘림 — 레토릭보다 성과를 따라감.",
 (H(figT) if figT is not None else "")+nport_html,
 "SEC EDGAR N-PORT 전체보유 (분기 공개·~60일 지연), CIK 1742912")}
{sec("정치 자본의 향방","최근 6개월, 의회는 어느 섹터를 순매수했나",
 f"상·하원 신고 거래의 순매수$(매수−매도)를 섹터별·정당별로. <b>매매 신호 아님</b> — 신고는 평균 49일 지연되고 집계 순매수는 다음분기 시장과 -0.30(약한 역행). 정책 테마 '맥락'으로만.",
 H(fig1),f"하원 Clerk PTR + 상원 eFD · {CUT.date()}~{asof}")}
{sec("종목 단서","핫섹터의 집중 매수 종목 · 새로 등장한 이름",
 "섹터 쏠림 안에서 실제로 많이·크게 산 개별 종목과, 최근 처음 등장한 신규 종목(테마 단서).",
 f"<div class=two><div><b>🔥 핫섹터 종목</b>{hot_tbl}</div><div><b>🌱 신규 부상</b>{emg_tbl}</div></div>","")}
{sec("테마 로테이션","정치 자본은 시간에 따라 테마를 바꾼다",
 "분기별 매수유입$를 테마별로 누적. 범례를 클릭해 특정 테마만 볼 수 있다.",H(fig2),"")}
{sec("리스크 맥락","의회는 금액기준 대체로 순매도 — 그러나 시장 예측력은 없다",
 "집계 순매수·매도비중을 SPY와 대조. <b>금액기준 순매도가 67% 분기(20/30)지만 건수로는 매수가 더 잦다</b>(매도비중 평균 44%) — '늘 순매도'는 아니다. 순매수와 다음분기 SPY는 −0.30의 약한 역상관이나 <b>통계적으로 유의하지 않아(t=−1.7·p=0.11) 신뢰할 신호가 아니다</b>. 코로나(2020) 폭락엔 선제 순매도가 없었고(반등 직전 대량 순매도), 2021Q4 순매도만 2022 약세를 일부 앞섰다.",
 H(fig3),"검증: 분기 30개·2019~2026, 순매도 20/30, r=−0.30(n=29, p=0.11 비유의)")}
{sec("정책 플레이북 · 검증된 경향","정책이벤트는 대상 섹터를 (다년) 움직인다 — 단 미확증·AI교란",
 "정책이벤트 스터디(29개)의 의사결정 참조표. 수혜 정책 → 대상섹터 +13%/1년(방향성)이나 통계 미확증(p≈0.37)·AI국면과 분리 안 됨. 신호가 아니라 대응 가이드.",
 PLAYBOOK,"이벤트스터디 n=29, 사인조정 CAR +1y +5.6%(p=0.37). 개별사례(CHIPS·관세·인텔)는 크나 통계 미확증")}
{sec("최근 규제 이벤트 · 자동","최근 90일 연방 중요규칙 — 보유섹터에 닿는 정책",
 "Federal Register 중요(significant) 최종규칙 자동피드. 보유 ETF 노출섹터에 규제가 닿는지 모니터(맥락용).",
 reg_html,"Federal Register API · 자동 · 최근 90일 significant rules")}{sec("부록","‘기타’ 미분류 항목",
 f"섹터 미분류는 금액기준 {cov*100:.0f}% — 대부분 상장폐지·개명된 과거 티커(FB→META, ATVI·SQ 등)와 소액 롱테일. 주요 종목은 수동매핑으로 편입.",oth_tbl,"")}
"""
html=f"""<!doctype html><html lang=ko><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Capitol Wave — 의회·정책자본 모니터</title><style>
:root{{--red:{RED};--ink:#1a1a1a;--mut:#6b6b6b}}
*{{box-sizing:border-box}} body{{margin:0;background:#f7f4ef;color:var(--ink);font-family:{SANS};line-height:1.55}}
.wrap{{max-width:880px;margin:0 auto;background:#fff;padding:0 36px 40px;box-shadow:0 0 30px rgba(0,0,0,.06)}}
.mast{{border-bottom:3px double var(--ink);padding:26px 0 12px;margin-bottom:6px}}
.mast .wm{{font-family:Georgia,'Times New Roman',serif;font-size:34px;font-weight:700;letter-spacing:-.5px}}
.mast .wm b{{color:var(--red)}} .mast .tag{{color:var(--mut);font-size:13px;margin-top:2px}}
.warn{{background:#fbeeee;border-left:3px solid var(--red);padding:10px 14px;font-size:12.5px;color:#7a2620;margin:16px 0 8px}}
section{{padding:22px 0;border-bottom:1px solid #ececec}}
.kicker{{color:var(--red);font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px}}
h2{{font-family:Georgia,serif;font-size:21px;font-weight:700;margin:0 0 4px;line-height:1.25}}
.dek{{color:var(--mut);font-size:13.5px;margin:0 0 14px;max-width:760px}}
.src{{color:#9a9a9a;font-size:10.5px;font-style:italic;margin-top:8px;border-top:1px solid #f0f0f0;padding-top:6px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;margin:6px 0}} th,td{{border-bottom:1px solid #eee;padding:5px 8px;text-align:left}}
th{{border-bottom:2px solid #ddd;font-weight:600;color:#555}} tr:hover td{{background:#fafafa}}
.two{{display:flex;gap:26px;flex-wrap:wrap}} .two>div{{flex:1;min-width:280px}}
h4{{font-size:13.5px;margin:14px 0 3px}} h4 .q{{color:#999;font-weight:400;font-size:12px}}
.chg{{font-size:12.5px;line-height:2;background:#fafafa;padding:8px 12px;border-radius:4px}}
.chg .new{{color:#1b7837;font-weight:700}} .chg .liq{{color:var(--red);font-weight:700}} .chg .up{{color:#1b7837;font-weight:700}} .chg .dn{{color:#b06000;font-weight:700}}
b{{font-weight:700}} .foot{{color:#9a9a9a;font-size:11px;padding-top:18px}}</style></head><body><div class=wrap>
<div class=mast><div class=wm>CAPITOL <b>WAVE</b></div><div class=tag>의회·정책자본 & ETF 모니터 — 미 상·하원 거래신고와 NANC/GOP ETF로 보는 정책 자본의 향방 · {asof} 기준</div></div>
<div class=warn>⚠️ <b>투자 신호가 아닙니다.</b> 의회 신고는 평균 49일 지연되고, 신고를 따라 사도 시장을 이기지 못하며(승률<50%), 집계 순매수는 다음 분기 시장과 약한 역(逆)상관(-0.30)입니다. 이 자료는 <b>정책·테마의 '맥락'</b>을 읽기 위한 것입니다. 금액은 신고 구간의 중간값 추정.</div>
{body}
<div class=foot>데이터: House Clerk PTR · Senate eFD(curl_cffi) · SEC N-PORT(CIK 1742912) · congress-legislators · yfinance. 거래 {len(df):,}건 ({df.transaction_date.min().date()}~{asof}). 섹터: yfinance+수동매핑. 재생성: <code>python3 scripts/policy_radar_dashboard.py</code> · 본 자료는 교육·분석 목적이며 투자권유가 아님.</div>
</div></body></html>"""
open(os.path.join(OUT,"capitol_wave.html"),"w").write(html)
print("저장:",os.path.join(OUT,"capitol_wave.html"),f"| 기타 {cov*100:.0f}% | 정권매칭 {regime_tot:+.0f}%")
