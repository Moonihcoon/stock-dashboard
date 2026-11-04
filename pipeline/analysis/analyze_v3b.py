import pickle,pandas as pd,numpy as np
from analyze_v3 import *
legs2=[l for l in LEGS if l['grp']>=2]; legs1=[l for l in LEGS if l['grp']==1]
def ev(legs,lv,w,tp,stop):
    rr=[sim(l,[x/100 for x in lv],w,tp,20,stop) for l in legs]; rr=[x for x in rr if x]
    if not rr: return None
    df=pd.DataFrame(rr);win=df.ret>0
    wins=df.ret[win].mean() if win.any() else np.nan;loss=-df.ret[~win].mean() if (~win).any() else np.nan
    return dict(n=len(df),fill=len(df)/len(legs)*100,win=win.mean()*100,cap=(df.ret*df.cap).sum()/df.cap.sum()*100,pl=wins/loss if loss==loss and loss else np.nan,worst=df.ret.min()*100)
G=pickle.load(open('R3.pkl','rb'))['R']['grid']
out=[]
for (name,tp,stop),v in G.items():
    legs=legs2 if name=='leg2p' else legs1
    a=[l for l in legs if l['y']<=2022];b=[l for l in legs if l['y']>=2023]
    # 후보: 체결률 75%+, 전체 승률 80%+ 중 자본가중 수익 상위 8
    c=v[(v.win>=80)&(v.fill_rate>=75)].sort_values('cap',ascending=False).head(8)
    for _,r in c.iterrows():
        e1=ev(a,r.levels,W2,tp/100,stop);e2=ev(b,r.levels,W2,tp/100,stop)
        out.append(dict(name=name,tp=tp,stop=stop,levels=r.levels,fill=r.fill_rate,win=r.win,cap=r['cap'],pl=r.pl,worst=r.worst,
            win_a=e1['win'] if e1 else np.nan,cap_a=e1['cap'] if e1 else np.nan,win_b=e2['win'] if e2 else np.nan,cap_b=e2['cap'] if e2 else np.nan,fill_b=e2['fill'] if e2 else np.nan,n_a=e1['n'] if e1 else 0,n_b=e2['n'] if e2 else 0))
O=pd.DataFrame(out);O.to_pickle('G9.pkl')
pd.set_option('display.width',250)
print(O.round(1).to_string())
