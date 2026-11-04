from common import analysis_panel
import pickle,json,sys,gzip,base64,itertools,numpy as np,pandas as pd
sys.path.insert(0,'.')
from analyze_v2 import *
from run_chain import run_chain
d=analysis_panel()
dates=sorted(d.date.unique());di={x:i for i,x in enumerate(dates)}
d2=d.sort_values(['ticker','date']);d2['di']=d2.date.map(di)
fr={t:g.reset_index(drop=True) for t,g in d2.groupby('ticker')}
def pos(t,date): return int(np.searchsorted(fr[t].date.values,np.datetime64(pd.Timestamp(date))))
def item6(e,p,level=0.5,rb=0.2):
    g=e['_g'];k,peak=e['k'],e['peak'];end,_,_=horizon_end(g,k,e['next_s0'],p)
    lo=g['low'].to_numpy(float);hi=g['high'].to_numpy(float)
    t50=next((t for t in range(k+1,end+1) if lo[t]<=peak*(1-level)),None)
    if t50 is None: return -1
    rm,ri=np.inf,-1
    for t in range(k+1,t50):
        if lo[t]<rm: rm,ri=lo[t],t
        if ri>=0 and t>ri and hi[t]>=rm*(1+rb): return 0
    return 1
EP={};COMBO={}
for rise,val in itertools.product([70,80,90,100],[2000,3000,4000,5000]):
    p=P(rise=rise/100,val_thresh=val*EOK,val_days=3)
    eps=find_episodes(d,p);E,T=run_chain(eps,p)
    first=T[T.order==1].set_index('eid');brk=T[T.order>=2]
    rows=[]
    for i,e in enumerate(eps):
        r=E.iloc[i];key=f"{e['ticker']}_{pd.Timestamp(e['start_date']):%Y%m%d}"
        f6=item6(e,p)
        if key not in EP:
            t=e['ticker'];pk=pos(t,e['peak_date']);st=pos(t,e['start_date'])
            g=fr[t].iloc[max(0,st-20):pk+131]
            c=g.close.to_numpy(np.int64);o=g.open.to_numpy(np.int64);h=g.high.to_numpy(np.int64);l=g.low.to_numpy(np.int64);dd=g.di.to_numpy(np.int64)
            EP[key]=dict(id=key,code=t,name=e['name'],mkt=e['market'],start=di[np.datetime64(pd.Timestamp(e['start_date']))],
              rise=round(e['rise5']*100,1),avgv=round(e['avg_value_eok']),mcap=None if pd.isna(e['mcap_eok']) else round(e['mcap_eok']),
              peakDate=di[np.datetime64(pd.Timestamp(e['peak_date']))],peak=int(e['peak']),tot=round(e['total_rise']*100),
              run=dict(d0=int(dd[0]),d=np.diff(dd).tolist(),c=[int(c[0])]+np.diff(c).tolist(),o=(o-np.r_[c[0],c[:-1]]).tolist(),h=(h-c).tolist(),l=(c-l).tolist(),v=np.round(g.value.to_numpy()/1e7).astype(int).tolist()))
        fd=round(float(first.loc[i,'dd_peak'])*100,1) if i in first.index else None
        rows.append([key,fd,int(r.n_rebounds),int(r.repeats),f6,None if pd.isna(r.max_dd) else round(float(r.max_dd)*100,1)])
    reach=[x for x in rows if x[4]>=0];norb=[x for x in rows if x[4]==1]
    fds=[x[1] for x in rows if x[1] is not None]
    brk_d=brk.depth_vs_ref.dropna()*100
    COMBO[f"{rise}|{val}"]=dict(rows=rows,sum=dict(n=len(rows),tk=int(E.ticker.nunique()),c2=int(E.cond2.sum()),c3=int(E.cond3.sum()),
        rep=round(float(E.repeats.mean()),2),first_med=round(float(np.median(fds)),1) if fds else None,brk_med=round(float(brk_d.median()),1) if len(brk_d) else None,
        reach50=len(reach),norb50=len(norb),norb_tk=int(len(set(r_[0].split('_')[0] for r_ in norb)))))
    print(rise,val,len(rows),COMBO[f"{rise}|{val}"]['sum'],flush=True)
json.dump(dict(combos=COMBO),open('web/data/combos.json','w',ensure_ascii=False and None) if False else open('web/data/combos.json','w'),separators=(',',':'))
meta=[{k:v for k,v in e.items() if k!='run'} for e in EP.values()]
json.dump(meta,open('web/data/epmeta.json','w'),ensure_ascii=False,separators=(',',':'))
runs={e['id']:e['run'] for e in EP.values()}
b=gzip.compress(json.dumps(runs,separators=(',',':')).encode(),9)
open('web/px/ep.txt','w').write(base64.b64encode(b).decode())
print(len(EP),'episodes',round(len(b)/1e6,2),'MB gz')
