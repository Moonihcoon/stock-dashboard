const $=(s,r=document)=>r.querySelector(s);
const fmt=n=>n==null?'–':Math.round(n).toLocaleString('ko-KR');
const f1=n=>n.toLocaleString('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});
const ld=(url)=>fetch(url).then(r=>{if(!r.ok)throw new Error(url);return r.json()});
const ldz=async(url)=>{const r=await fetch(url);if(!r.ok)throw new Error(url);const bin=Uint8Array.from(atob(await r.text()),c=>c.charCodeAt(0));
  return JSON.parse(await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).text())};
let DATES=null;const D=i=>DATES[i];
const ymd=s=>s.slice(2).replace(/-/g,'.');
const pctTxt=p=>(p>=0?'+':'−')+f1(Math.abs(p))+'%';
const MKT=m=>m==='KOSPI'?'코스피':'코스닥';

/* ---------- 차트 (캔들 + 거래대금 + 보조 도구) ---------- */
function niceTicks(lo,hi,n){const span=hi-lo||1,raw=span/n,p=Math.pow(10,Math.floor(Math.log10(raw)));let st=[1,2,2.5,5,10].map(m=>m*p).find(s=>s>=raw);const o=[];for(let v=Math.ceil(lo/st)*st;v<=hi+1e-9;v+=st)o.push(v);return o}
function drawChart(box,rows,opt={}){
  box.replaceChildren();
  if(!rows||!rows.length){box.textContent='표시할 데이터가 없습니다.';return}
  const m=opt.m||{mode:'none',list:[],hl:[],vl:[],pend:null},ref=opt.ref,W=Math.max(300,box.clientWidth),HP=300,HV=110,gap=26,L=66,R=12,T=10,B=24;
  const H=T+HP+gap+HV+B,n=rows.length,step=(W-L-R)/n,bw=Math.max(1,Math.min(14,step*0.7));
  let lo=Math.min(...rows.map(r=>r[3])),hi=Math.max(...rows.map(r=>r[2]));
  const lv=(opt.lines||[]);lv.forEach(l=>{lo=Math.min(lo,l.y);hi=Math.max(hi,l.y)});
  const pad=(hi-lo)*0.05;lo=Math.max(0,lo-pad);hi+=pad;
  const vmax=Math.max(...rows.map(r=>r[5]))||1,vt=niceTicks(0,vmax*1.05,3),vtop=vt[vt.length-1]>=vmax?vt[vt.length-1]:vmax*1.05;
  const X=i=>L+step*(i+.5),Y=v=>T+HP*(hi-v)/(hi-lo),YV=v=>T+HP+gap+HV*(1-v/vtop),PV=y=>hi-(y-T)/HP*(hi-lo);
  const NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');svg.setAttribute('class','c');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('height',H);svg.setAttribute('role','img');svg.setAttribute('aria-label',opt.label||'주가 차트');
  if(m.mode!=='none')svg.style.cursor='crosshair';
  const mk=(t,a,txt)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;svg.appendChild(e);return e};
  const lab=(x,y,t,c,anchor)=>mk('text',{x,y,'text-anchor':anchor||'middle',style:`fill:${c};font-weight:700;font-size:12.5px;paint-order:stroke;stroke:var(--panel);stroke-width:4px;stroke-linejoin:round`},t);
  niceTicks(lo,hi,5).forEach(v=>{mk('line',{class:'gl',x1:L,x2:W-R,y1:Y(v),y2:Y(v)});mk('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},fmt(v))});
  vt.forEach(v=>{mk('line',{class:'gl',x1:L,x2:W-R,y1:YV(v),y2:YV(v)});mk('text',{x:L-6,y:YV(v)+4,'text-anchor':'end'},fmt(v)+'억')});
  const every=Math.max(1,Math.ceil(90/step));
  rows.forEach((r,i)=>{if(i%every===0)mk('text',{x:X(i),y:H-6,'text-anchor':'middle'},ymd(D(r[0])))});
  rows.forEach((r,i)=>{const up=r[4]>=r[1],c=up?'var(--up)':'var(--down)';
    mk('line',{x1:X(i),x2:X(i),y1:Y(r[2]),y2:Y(r[3]),stroke:c,'stroke-width':1});
    const y1=Y(Math.max(r[1],r[4])),y2=Y(Math.min(r[1],r[4]));
    mk('rect',{x:X(i)-bw/2,y:y1,width:bw,height:Math.max(1,y2-y1),fill:c});
    mk('rect',{x:X(i)-bw/2,y:YV(r[5]),width:bw,height:Math.max(0,YV(0)-YV(r[5])),fill:c,opacity:.75})});
  (opt.marks||[]).forEach((mm,mi)=>{const i=rows.findIndex(r=>r[0]===mm.di);if(i<0)return;
    mk('line',{x1:X(i),x2:X(i),y1:T,y2:T+HP+gap+HV,stroke:'var(--mark)','stroke-width':1.2,'stroke-dasharray':'4 3'});
    mk('text',{x:Math.min(W-R-4,X(i)+4),y:T+10+13*mi,style:'fill:var(--mark);font-weight:600','text-anchor':X(i)>W-80?'end':'start'},mm.t)});
  lv.forEach(l=>{mk('line',{x1:L,x2:W-R,y1:Y(l.y),y2:Y(l.y),stroke:'var(--mark)','stroke-width':1,'stroke-dasharray':'2 3'});mk('text',{x:L+4,y:Y(l.y)-3,style:'fill:var(--mark)'},l.t)});
  /* 사용자 가로선·세로선 */
  const rtxt=p=>ref?` (${ref.t} ${pctTxt((p/ref.p-1)*100)})`:'';
  m.hl.forEach(h=>{mk('line',{x1:L,x2:W-R,y1:Y(h),y2:Y(h),stroke:'var(--accent)','stroke-width':1.4});lab(W-R-4,Y(h)-5,fmt(h)+rtxt(h),'var(--accent)','end')});
  m.vl.forEach(i=>{if(i<0||i>=n)return;mk('line',{x1:X(i),x2:X(i),y1:T,y2:T+HP+gap+HV,stroke:'var(--accent)','stroke-width':1.4});lab(X(i),H-B+2,ymd(D(rows[i][0])),'var(--accent)',X(i)>W-60?'end':'middle')});
  /* 측정선 */
  m.list.forEach(q=>{const a=q.a,b=q.b,pct=(b.p/a.p-1)*100,c=pct>=0?'var(--up)':'var(--down)';
    mk('line',{x1:X(a.i),y1:Y(a.p),x2:X(b.i),y2:Y(b.p),stroke:c,'stroke-width':2});
    [a,b].forEach(z=>mk('circle',{cx:X(z.i),cy:Y(z.p),r:4,fill:c,stroke:'var(--panel)','stroke-width':1.5}));
    lab(Math.min(W-40,Math.max(L+30,(X(a.i)+X(b.i))/2)),(Y(a.p)+Y(b.p))/2-8,pctTxt(pct),c)});
  let rb=null,rbt=null,snap=null,chx=null,chy=null,cyl=null,cxl=null;
  if(m.pend){mk('circle',{cx:X(m.pend.i),cy:Y(m.pend.p),r:5,fill:'var(--accent)',stroke:'var(--panel)','stroke-width':1.5});
    rb=mk('line',{x1:X(m.pend.i),y1:Y(m.pend.p),x2:X(m.pend.i),y2:Y(m.pend.p),stroke:'var(--accent)','stroke-width':1.5,'stroke-dasharray':'4 3'});rbt=lab(X(m.pend.i),Y(m.pend.p)-10,'','var(--accent)')}
  if(m.mode==='measure')snap=mk('circle',{r:5,fill:'none',stroke:'var(--accent)','stroke-width':2,visibility:'hidden'});
  if(m.mode==='cross'){chx=mk('line',{y1:T,y2:T+HP+gap+HV,stroke:'var(--ink)','stroke-width':1,'stroke-dasharray':'3 3',visibility:'hidden'});
    chy=mk('line',{x1:L,x2:W-R,stroke:'var(--ink)','stroke-width':1,'stroke-dasharray':'3 3',visibility:'hidden'});
    cyl=lab(W-R-4,0,'','var(--ink)','end');cxl=lab(0,H-B+2,'','var(--ink)');cyl.setAttribute('visibility','hidden');cxl.setAttribute('visibility','hidden')}
  const cross=mk('line',{y1:T,y2:T+HP+gap+HV,stroke:'var(--ink-3)','stroke-width':1,visibility:'hidden'});
  const tip=document.createElement('div');tip.className='tip';tip.hidden=true;
  box.appendChild(svg);box.appendChild(tip);
  const pt0=ev=>{const rc=svg.getBoundingClientRect(),x=(ev.clientX-rc.left)*W/rc.width,y=(ev.clientY-rc.top)*H/rc.height,i=Math.floor((x-L)/step);return {rc,x,y,i}};
  const pick=ev=>{const {rc,x,y,i}=pt0(ev);if(i<0||i>=n)return null;const r=rows[i];let best=null;[[1,'시가'],[2,'고가'],[3,'저가'],[4,'종가']].forEach(([k,nm])=>{const dd=Math.abs(Y(r[k])-y);if(!best||dd<best.dd)best={dd,p:r[k],k:nm}});return {i,p:best.p,k:best.k,rc,x,y}};
  svg.addEventListener('pointermove',ev=>{const {rc,x,y,i}=pt0(ev);
    if(i<0||i>=n){[cross,snap,chx,chy,cyl,cxl].forEach(e=>e&&e.setAttribute('visibility','hidden'));tip.hidden=true;return}
    const r=rows[i],pr=i?rows[i-1][4]:null,ch=pr?(r[4]/pr-1)*100:null;
    cross.setAttribute('x1',X(i));cross.setAttribute('x2',X(i));cross.setAttribute('visibility',m.mode==='cross'?'hidden':'visible');
    if(snap){const pt=pick(ev);snap.setAttribute('cx',X(i));snap.setAttribute('cy',Y(pt.p));snap.setAttribute('visibility','visible');
      if(rb){const pct=(pt.p/m.pend.p-1)*100;rb.setAttribute('x2',X(i));rb.setAttribute('y2',Y(pt.p));rbt.setAttribute('x',(X(i)+X(m.pend.i))/2);rbt.setAttribute('y',(Y(pt.p)+Y(m.pend.p))/2-8);rbt.textContent=pctTxt(pct)}}
    if(chx&&y>=T&&y<=T+HP){const pv=PV(y);chx.setAttribute('x1',X(i));chx.setAttribute('x2',X(i));chx.setAttribute('visibility','visible');
      chy.setAttribute('y1',y);chy.setAttribute('y2',y);chy.setAttribute('visibility','visible');
      cyl.setAttribute('y',y-5);cyl.textContent=fmt(pv)+rtxt(pv);cyl.setAttribute('visibility','visible');
      cxl.setAttribute('x',Math.min(W-40,Math.max(L+30,X(i))));cxl.textContent=ymd(D(r[0]));cxl.setAttribute('visibility','visible')}
    else if(chx){[chx,chy,cyl,cxl].forEach(e=>e.setAttribute('visibility','hidden'))}
    tip.innerHTML=`<b>${D(r[0])}</b><br>시 ${fmt(r[1])} 고 ${fmt(r[2])}<br>저 ${fmt(r[3])} 종 ${fmt(r[4])}`+(ch==null?'':` <span class="${ch>=0?'up':'dn'}">(${pctTxt(ch)})</span>`)+`<br>거래대금 ${f1(r[5])}억`;
    tip.hidden=false;const tx=X(i)*rc.width/W;tip.style.left=Math.min(Math.max(0,tx+12),rc.width-tip.offsetWidth)+'px';tip.style.top='8px'});
  svg.addEventListener('pointerleave',()=>{[cross,snap,chx,chy,cyl,cxl].forEach(e=>e&&e.setAttribute('visibility','hidden'));tip.hidden=true});
  svg.addEventListener('click',ev=>{if(m.mode==='none'||m.mode==='cross')return;
    if(m.mode==='measure'){const pt=pick(ev);if(!pt)return;const q={i:pt.i,p:pt.p,k:pt.k};
      if(!m.pend)m.pend=q;else{let a=m.pend,b=q;if(b.i<a.i)[a,b]=[b,a];m.list.push({a,b});m.pend=null}}
    else if(m.mode==='h'){const {y}=pt0(ev);if(y<T||y>T+HP)return;m.hl.push(Math.round(PV(y)))}
    else if(m.mode==='v'){const {i}=pt0(ev);if(i<0||i>=n)return;m.vl.push(i);m.vl.sort((a,b)=>a-b)}
    if(opt.changed)opt.changed()});
}
const MOUNTED=[];
const HINT={none:'도구를 고르면 차트 위에서 선을 그리거나 구간을 잴 수 있습니다.',measure:'시작 지점과 끝 지점을 차례로 누르세요. 시가·고가·저가·종가 중 가까운 값에 붙습니다. 앞 지점 대비 뒤 지점의 등락률이 나옵니다. (Esc 취소)',h:'가격 차트를 누르면 그 높이에 가로선이 생기고 가격과 기준 대비 %가 표시됩니다.',v:'차트를 누르면 그 날짜에 세로선이 생깁니다. 선이 둘 이상이면 선 사이 기간과 등락률을 보여 줍니다.',cross:'마우스를 올리면 십자선과 함께 가격·날짜·기준 대비 %가 축에 표시됩니다.'};
function mountChart(el,rows,opt={}){
  if(el._key!==opt.key||!el._shell){
    el._key=opt.key;const mode=el._m?el._m.mode:'none';el._m={mode,list:[],hl:[],vl:[],pend:null};
    el.innerHTML=`<div class="cw"><div class="chartbox" data-r="chart"></div><aside class="tools" aria-label="차트 보조메뉴"><h4>보조메뉴</h4><div class="modes" data-r="modes"><button type="button" class="btn" data-m="none">기본</button><button type="button" class="btn" data-m="measure">구간 측정</button><button type="button" class="btn" data-m="h">가로선</button><button type="button" class="btn" data-m="v">세로선</button><button type="button" class="btn" data-m="cross">십자선</button></div><p class="hint" data-r="hint"></p><ol data-r="list"></ol><div class="row"><button type="button" class="btn" data-r="undo">마지막 삭제</button><button type="button" class="btn" data-r="clr">모두 지우기</button></div></aside></div>`;
    el._shell=1;if(!MOUNTED.includes(el))MOUNTED.push(el);
  }
  const q=s=>$(`[data-r=${s}]`,el),cb=q('chart');el._rows=rows;el._opt=opt;
  const side=()=>{const m=el._m,R=el._rows,rf=el._opt.ref;
    el.querySelectorAll('[data-m]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===m.mode));
    q('hint').textContent=m.mode==='measure'&&m.pend?'끝 지점을 누르세요. (Esc로 취소)':HINT[m.mode];
    const it=[];
    m.list.forEach((x,k)=>{const pct=(x.b.p/x.a.p-1)*100,d1=D(R[x.a.i][0]),d2=D(R[x.b.i][0]),cal=Math.round((new Date(d2)-new Date(d1))/864e5);
      it.push(`<li><b class="${pct>=0?'up':'dn'}">${pctTxt(pct)}</b><small>${ymd(d1)} ${x.a.k} ${fmt(x.a.p)}</small><small>→ ${ymd(d2)} ${x.b.k} ${fmt(x.b.p)}</small><small>${x.b.i-x.a.i}거래일 · ${cal}일</small><button type="button" aria-label="삭제" data-t="list" data-k="${k}">×</button></li>`)});
    m.hl.forEach((p,k)=>{it.push(`<li><b>${fmt(p)}</b><small>가로선${rf?` · ${rf.t} ${pctTxt((p/rf.p-1)*100)}`:''}</small><button type="button" aria-label="삭제" data-t="hl" data-k="${k}">×</button></li>`)});
    m.vl.forEach((i,k)=>{let extra='';if(k){const pi=m.vl[k-1],c0=R[pi][4],c1=R[i][4];extra=`<small>앞 선 대비 ${i-pi}거래일 · 종가 ${pctTxt((c1/c0-1)*100)}</small>`}
      it.push(`<li><b>${ymd(D(R[i][0]))}</b><small>세로선 · 종가 ${fmt(R[i][4])}</small>${extra}<button type="button" aria-label="삭제" data-t="vl" data-k="${k}">×</button></li>`)});
    q('list').innerHTML=it.join('')||'<li class="mut">그려 둔 선이 없습니다.</li>';
    q('list').querySelectorAll('button[data-k]').forEach(b=>b.onclick=()=>{m[b.dataset.t].splice(+b.dataset.k,1);redraw();side()})};
  const redraw=()=>drawChart(cb,el._rows,{...el._opt,m:el._m,changed:()=>{redraw();side()}});
  el._redraw=redraw;
  el.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{el._m.mode=b.dataset.m;el._m.pend=null;redraw();side()});
  q('undo').onclick=()=>{const m=el._m;if(m.pend)m.pend=null;else if(m.mode==='h'&&m.hl.length)m.hl.pop();else if(m.mode==='v'&&m.vl.length)m.vl.pop();else if(m.list.length)m.list.pop();else if(m.hl.length)m.hl.pop();else m.vl.pop();redraw();side()};
  q('clr').onclick=()=>{Object.assign(el._m,{list:[],hl:[],vl:[],pend:null});redraw();side()};
  redraw();side();
  if(!el._ro){el._ro=new ResizeObserver(()=>{if(cb.offsetWidth)el._redraw()});el._ro.observe(cb)}
}
document.addEventListener('keydown',ev=>{if(ev.key==='Escape')MOUNTED.forEach(el=>{if(el._m&&el._m.pend){el._m.pend=null;el._redraw();}})});

/* ---------- 종목 시세 (episodes) ---------- */
function decodeRun(u){const out=[];let di=u.d0,c=u.c[0];
  for(let i=0;i<u.c.length;i++){let pc=c;if(i){di+=u.d[i-1];c+=u.c[i]}
    out.push([di,pc+u.o[i],c+u.h[i],c-u.l[i],c,u.v[i]/10])}return out}
let EPM=null,EPX=null,CMB=null;
async function loadEp(){if(!EPM){const [a,b,c]=await Promise.all([ld('data/epmeta.json'),ldz('px/ep.txt'),ld('data/combos.json')]);EPM={};a.forEach(e=>EPM[e.id]=e);EPX=b;CMB=c.combos}}
const epRows=id=>decodeRun(EPX[id]);
const f6txt=v=>v===1?'20% 반등 없음':v===0?'반등 있음':'미도달';

/* ---------- 탭: 종목 차트 ---------- */
let LIST=[];
function tab1(){
  const e=LIST[+$('#sel').value],rows=epRows(e.id);
  $('#chips').innerHTML=[['시장',MKT(e.mkt)],['상승 시작일',D(e.start)],['5거래일 상승률',`+${f1(e.rise)}%`],['일 평균 거래대금',fmt(e.avgv)+'억'],['시가총액',e.mcap==null?'–':fmt(e.mcap)+'억'],['고점일',D(e.peakDate)],['고점까지 상승',`+${fmt(e.tot)}%`],['6개월 최대낙폭',e.s[5]==null?'–':f1(e.s[5])+'%'],['첫 반등 저점(고점 대비)',e.s[1]==null?'–':f1(e.s[1])+'%'],['반등 / 이탈 후 재반등',`${e.s[2]}회 / ${e.s[3]}회`],['−50% 구간',f6txt(e.s[4])]].map(([a,b])=>`<div class="chip"><small>${a}</small><b>${b}</b></div>`).join('');
  const lines=$('#lv').checked?[.33,.38,.43].map((p,i)=>({y:e.peak*(1-p),t:`${i+1}차 −${p*100}%`})):[];
  mountChart($('#cb1'),rows,{key:'s'+e.id,marks:[{di:e.start,t:'상승 시작'},{di:e.peakDate,t:'고점'}],lines,ref:{p:e.peak,t:'고점 대비'},label:e.name+' 일봉'});
  const body=rows.map((r,i)=>({r,pr:i?rows[i-1][4]:null})).reverse().map(({r,pr})=>{const ch=pr?(r[4]/pr-1)*100:null;return `<tr><td>${D(r[0])}</td><td>${fmt(r[4])}</td><td class="${ch==null?'':ch>=0?'up':'dn'}">${ch==null?'–':pctTxt(ch)}</td><td>${f1(r[5])}</td></tr>`}).join('');
  $('#tw1').innerHTML=`<table><thead><tr><th>일자</th><th>종가</th><th>등락률</th><th>거래대금(억)</th></tr></thead><tbody>${body}</tbody></table>`;
}
/* ---------- 탭: 조건검색 ---------- */
function tab3(){
  const key=`${$('#f-rise').value}|${$('#f-val').value}`,yr=$('#f-year').value,mk=$('#f-mk').value,C=CMB[key];
  let list=C.rows.map(r=>({e:EPM[r[0]],s:r})).filter(x=>(!yr||D(x.e.start).startsWith(yr))&&(!mk||x.e.mkt===mk)).sort((a,b)=>b.e.start-a.e.start);
  const s=C.sum;
  $('#sc-sum').innerHTML=`조건: 5거래일 내 장중 +${$('#f-rise').value}% 이상, 5일 중 3일 이상 거래대금 ${fmt($('#f-val').value)}억 이상 → <b>${s.n}건 (${s.tk}종목)</b>. −30% 하락 후 +10% 반등 ${s.c2}건, 이탈 후 재반등 ${s.c3}건, 사례당 평균 ${s.rep}회 반복. 첫 반등 저점 중앙값 ${s.first_med}%, 이탈 후 추가 하락 중앙값 ${s.brk_med}%. −50%까지 내려간 ${s.reach50}건 중 20% 반등이 없던 건 <b>${s.norb50}건(${s.norb_tk}종목)</b>. 표시 ${list.length}건.`;
  $('#tw3').innerHTML=`<table><thead><tr><th class="l">종목명</th><th class="l">시장</th><th>상승 시작일</th><th>5일 상승률</th><th>일 평균 거래대금(억)</th><th>시가총액(억)</th><th>첫 반등 저점</th><th>반등</th><th>재반등</th><th class="l">−50% 구간</th></tr></thead><tbody>${list.map((x,i)=>{const e=x.e;return `<tr class="pick" data-i="${i}" tabindex="0"><td class="l">${e.name}</td><td class="l">${MKT(e.mkt)}</td><td>${D(e.start)}</td><td class="up">+${f1(e.rise)}%</td><td>${fmt(e.avgv)}</td><td>${fmt(e.mcap)}</td><td class="dn">${x.s[1]==null?'–':f1(x.s[1])+'%'}</td><td>${x.s[2]}</td><td>${x.s[3]}</td><td class="l ${x.s[4]===1?'up':'mut'}">${f6txt(x.s[4])}</td></tr>`}).join('')}</tbody></table>`;
  const show=i=>{const x=list[i];if(!x){$('#cb3').replaceChildren();$('#cb3')._shell=0;$('#sc-title').textContent='조건에 맞는 종목이 없습니다.';return}
    const e=x.e;document.querySelectorAll('#tw3 tr.pick').forEach(r=>r.classList.toggle('sel',+r.dataset.i===i));
    $('#sc-title').textContent=`${e.name} (${MKT(e.mkt)}) 일봉, 상승 시작 ${D(e.start)}`;
    mountChart($('#cb3'),epRows(e.id),{key:'x'+e.id,marks:[{di:e.start,t:'상승 시작'},{di:e.peakDate,t:'고점'}],ref:{p:e.peak,t:'고점 대비'},label:e.name+' 일봉'})};
  document.querySelectorAll('#tw3 tr.pick').forEach(r=>{const go=()=>show(+r.dataset.i);r.onclick=go;r.onkeydown=ev=>{if(ev.key==='Enter')go()}});
  show(0);
}
/* ---------- 탭: 날짜별 상위 200 ---------- */
let RS=null,RSMAP=null;
async function loadRs(){if(RS===null){try{RS=await ld('data/reasons.json')}catch(e){RS=[]}
  RSMAP={};RS.forEach(x=>{(RSMAP[x.d+'|'+x.n]=RSMAP[x.d+'|'+x.n]||[]).push(x)})}return RS}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const safeUrl=u=>/^https?:\/\//i.test(u)?u:'#';
let TICK=null;const TOP={};
async function topMonth(ym){if(!(ym in TOP))TOP[ym]=ld(`data/top/${ym}.json`).catch(()=>({}));return TOP[ym]}
async function tab2(){
  const v=$('#dt').value;if(!v)return;
  let idx=DATES.indexOf(v);
  if(idx<0){let j=DATES.findIndex(x=>x>v);idx=j<0?DATES.length-1:Math.max(0,j-1);$('#dt').value=DATES[idx]}
  const date=DATES[idx],data=await topMonth(date.slice(0,7)),rows=(data[idx]||[]);
  const mk=$('#mk').value,mv=+$('#mv').value||0;
  let list=rows.map((r,k)=>({rk:k+1,ti:r[0],t:TICK[r[0]],rate:r[1],val:r[2],close:r[3],mc:r[4]})).filter(x=>(!mk||x.t[2]===mk)&&x.val>=mv);
  const cnt=m=>rows.filter(r=>TICK[r[0]][2]===m).length;
  $('#cal-sum').innerHTML=rows.length?`<b>${date}</b> 상승률 상위 ${rows.length}개 중 ${list.length}개 표시 (코스피 ${cnt('KOSPI')} · 코스닥 ${cnt('KOSDAQ')}). 1위 ${TICK[rows[0][0]][1]} +${f1(rows[0][1])}%`:`<b>${date}</b> 자료가 없습니다.`;
  await loadRs();
  const why=x=>{const L=RSMAP[date+'|'+x.t[1]]||[],a=L.find(z=>z.dir!=='down')||L[0];return a?`<a href="${esc(safeUrl(a.u))}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" title="${esc(a.h||'')}">${esc(a.r||a.h)}</a>`:'<span class="mut">–</span>'};
  const body=list.map(x=>`<tr class="pick" data-t="${x.ti}"><td>${x.rk}</td><td class="l">${esc(x.t[1])}<br><small class="mut">${x.t[0]}</small></td><td class="l">${MKT(x.t[2])}</td><td class="up">+${f1(x.rate)}%</td><td>${fmt(x.val)}</td><td>${x.mc==null?'–':fmt(x.mc)}</td><td>${fmt(x.close)}</td><td class="l" style="min-width:180px;max-width:320px;overflow:hidden;text-overflow:ellipsis">${why(x)}</td><td><button type="button" class="btn" data-c="${x.ti}" aria-label="${esc(x.t[1])} 일봉 차트 보기">차트 보기</button></td></tr>`).join('');
  T2X={date,rows:list.map(x=>[x.rk,x.t[1],x.t[0],MKT(x.t[2]),x.rate,x.val,x.mc,x.close,(()=>{const L=RSMAP[date+'|'+x.t[1]]||[],a=L.find(z=>z.dir!=='down')||L[0];return a?(a.r||a.h):''})(),(()=>{const L=RSMAP[date+'|'+x.t[1]]||[],a=L.find(z=>z.dir!=='down')||L[0];return a?a.u:''})()])};
  $('#t2c').hidden=true;$('#cb2')._shell=0;$('#cb2')._key=null;
  $('#tw2').innerHTML=`<table><thead><tr><th>순위</th><th class="l">종목명</th><th class="l">시장</th><th>상승률</th><th>거래대금(억)</th><th>시가총액(억)</th><th>종가</th><th class="l">상승 이유</th><th>차트</th></tr></thead><tbody>${body}</tbody></table>`;
  document.querySelectorAll('#tw2 tr.pick').forEach(r=>{r.onclick=()=>showT2(+r.dataset.t,idx,r)});
  document.querySelectorAll('#tw2 button[data-c]').forEach(b=>{b.onclick=ev=>{ev.stopPropagation();showT2(+b.dataset.c,idx,b.closest('tr'))}});
}
const PXM={};
async function pxMonth(ym){if(!(ym in PXM))PXM[ym]=ldz(`px/m/${ym}.txt`).catch(()=>({}));return PXM[ym]}
async function stockRows(ti,a,b){
  const yms=[...new Set(DATES.slice(a,b+1).map(s=>s.slice(0,7)))];
  const parts=await Promise.all(yms.map(pxMonth));let rows=[];
  parts.forEach(p=>{if(p[ti])rows=rows.concat(decodeRun(p[ti]))});
  return rows.filter(r=>r[0]>=a&&r[0]<=b).sort((x,y)=>x[0]-y[0])}
async function showT2(ti,idx,tr){
  document.querySelectorAll('#tw2 tr.pick').forEach(x=>x.classList.toggle('sel',x===tr));
  const box=$('#cb2'),wrap=$('#t2c');wrap.hidden=false;$('#t2-title').textContent=TICK[ti][1]+' 불러오는 중...';
  wrap.scrollIntoView({block:'nearest',behavior:'smooth'});
  try{
    const n=+$('#cn').value||120,rows=await stockRows(ti,Math.max(0,idx-n),Math.min(DATES.length-1,idx+20)),rp=rows.find(x=>x[0]===idx);
    if(!rows.length||!rp){$('#t2-title').textContent=TICK[ti][1]+': 이 날짜 주변 시세가 없습니다.';box.replaceChildren();box._shell=0;return}
    $('#t2-title').textContent=`${TICK[ti][1]} (${MKT(TICK[ti][2])}) 일봉 · 선택일 ${D(idx)} · 아래 막대 거래대금(억원)`;
    mountChart(box,rows,{key:'c'+ti+'_'+idx+'_'+n,marks:[{di:idx,t:'선택일'}],ref:{p:rp[4],t:'선택일 종가 대비'},label:TICK[ti][1]+' 일봉'});
  }catch(e){$('#t2-title').textContent='시세를 불러오지 못했습니다. 잠시 뒤 다시 눌러 주세요.'}
}
/* ---------- 탭: 상승 이유 ---------- */
async function loadTick(){if(!TICK)TICK=await ld('data/tick.json')}
async function tab5(){
  const rs=await loadRs();
  if(!rs.length){$('#rs-dt').innerHTML='';$('#rs-sum').textContent='아직 수집된 상승 이유가 없습니다. PC의 수집 프로그램이 data/reasons.json을 올리면 여기에 표시됩니다.';$('#tw5').innerHTML='';return}
  if(!ready.rs){ready.rs=1;const ds=[...new Set(rs.map(x=>x.d))].sort().reverse();$('#rs-dt').innerHTML=ds.map(d=>`<option>${d}</option>`).join('');
    ['rs-dt','rs-up','rs-top'].forEach(i=>$('#'+i).onchange=tab5);$('#rs-q').oninput=tab5}
  const date=$('#rs-dt').value,q=$('#rs-q').value.trim(),up=$('#rs-up').checked,onlyTop=$('#rs-top').checked;
  await loadTick();
  const di=DATES.indexOf(date),rate={};
  if(di>=0){const t=(await topMonth(date.slice(0,7)))[di]||[];t.forEach(r=>{rate[TICK[r[0]][1]]={r:r[1]}})}
  const mkt={};TICK.forEach(t=>mkt[t[1]]=t[2]);
  let list=rs.filter(x=>x.d===date&&(!up||x.dir!=='down')&&(!q||x.n.includes(q))&&(!onlyTop||rate[x.n]));
  list.sort((a,b)=>((rate[b.n]?rate[b.n].r:-1)-(rate[a.n]?rate[a.n].r:-1))||(b.t||'').localeCompare(a.t||''));
  const nm=new Set(list.map(x=>x.n)).size;
  $('#rs-sum').innerHTML=`<b>${date}</b> 기사 ${list.length}건 · 종목 ${nm}개`+(di<0?' (휴장일이라 상승률은 표시하지 않습니다)':'');
  $('#tw5').innerHTML=`<table><thead><tr><th class="l">종목명</th><th class="l">시장</th><th>상승률</th><th class="l">이유</th><th class="l">공시 제목</th><th class="l">출처</th><th>공시일</th></tr></thead><tbody>${list.map(x=>{const rt=rate[x.n];return `<tr><td class="l">${esc(x.n)}</td><td class="l">${mkt[x.n]?MKT(mkt[x.n]):'–'}</td><td class="${rt?'up':'mut'}">${rt?'+'+f1(rt.r)+'%':'–'}</td><td class="l" style="white-space:normal;min-width:200px">${esc(x.r||'')}</td><td class="l" style="white-space:normal;min-width:220px"><a href="${esc(safeUrl(x.u))}" target="_blank" rel="noopener noreferrer">${esc(x.h)}</a></td><td class="l">${esc(x.s||'')}</td><td>${esc(x.t||'')}</td></tr>`}).join('')}</tbody></table>`;
}
/* ---------- 탭 전환 ---------- */
const ready={};
async function open(name){
  document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-selected',b.dataset.tab===name));
  ['stats','list','stocks','screen','calendar','reasons'].forEach(t=>$('#p-'+t).hidden=t!==name);
  try{
    if(name==='stocks'){await loadEp();
      if(!ready.s){ready.s=1;LIST=CMB['80|3000'].rows.map(r=>({...EPM[r[0]],s:r})).sort((a,b)=>a.name.localeCompare(b.name,'ko'));$('#n-list').textContent=LIST.length;
        $('#sel').innerHTML=LIST.map((e,i)=>`<option value="${i}">${e.name} · ${D(e.start)}</option>`).join('');$('#sel').onchange=tab1;$('#lv').onchange=tab1}
      tab1()}
    if(name==='screen'){await loadEp();
      if(!ready.x){ready.x=1;const ys=[...new Set(Object.values(EPM).map(e=>D(e.start).slice(0,4)))].sort();$('#f-year').innerHTML='<option value="">전체</option>'+ys.map(y=>`<option>${y}</option>`).join('');
        ['f-rise','f-val','f-year','f-mk'].forEach(i=>$('#'+i).onchange=tab3);tab3()}
      else{const c=$('#cb3');if(c._redraw)c._redraw()}}
    if(name==='reasons')await tab5();
    if(name==='calendar'){if(!ready.c){ready.c=1;await loadTick();$('#dt').value=DATES[DATES.length-1];
        $('#dt').onchange=tab2;$('#mk').onchange=tab2;$('#mv').oninput=tab2;$('#today').onclick=()=>{$('#dt').value=DATES[DATES.length-1];tab2()};$('#t2x').onclick=()=>{$('#t2c').hidden=true;document.querySelectorAll('#tw2 tr.sel').forEach(x=>x.classList.remove('sel'))};$('#cn').onchange=()=>{const s=document.querySelector('#tw2 tr.sel');if(s&&!$('#t2c').hidden)s.querySelector('button[data-c]').click()};
        const step=d=>{let i=DATES.indexOf($('#dt').value);if(i<0)i=DATES.length-1;i=Math.min(DATES.length-1,Math.max(0,i+d));$('#dt').value=DATES[i];tab2()};
        $('#prev').onclick=()=>step(-1);$('#next').onclick=()=>step(1)}
      await tab2()}
  }catch(err){const p=$('#p-'+name);const m=document.createElement('p');m.className='note';m.textContent='데이터를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.';p.prepend(m)}
}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{open(b.dataset.tab);try{history.replaceState(null,'','#'+b.dataset.tab)}catch(e){}});
ld('data/dates.json').then(d=>{DATES=d;const h=location.hash.slice(1);open(['stats','list','stocks','screen','calendar','reasons'].includes(h)?h:'stats')}).catch(()=>{document.body.append('날짜 데이터를 불러오지 못했습니다.')});

/* ---------- 엑셀 다운로드 ---------- */
let T2X=null,XLSXP=null;
const loadXlsx=()=>XLSXP||(XLSXP=new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';s.onload=()=>ok(window.XLSX);s.onerror=()=>{XLSXP=null;no()};document.head.append(s)}));
const numify=v=>{if(typeof v!=='string')return v;const s=v.trim().replace(/−/g,'-');if(/^[+-]?[\d,]+(\.\d+)?%?$/.test(s))return +s.replace(/[,%+]/g,'');return v};
function tableRows(tb,skip=[]){const hs=[...tb.querySelectorAll('thead th')].map(th=>th.innerText.replace(/[▲▼↑↓]/g,'').trim());
  const keep=hs.map((h,i)=>skip.includes(h)?-1:i).filter(i=>i>=0);
  const body=[...tb.querySelectorAll('tbody tr')].filter(r=>r.style.display!=='none'&&!r.hidden).map(r=>{const c=[...r.children];return keep.map(i=>numify((c[i]?c[i].innerText:'').replace(/\s*\n\s*/g,' ').trim()))});
  return [keep.map(i=>hs[i]),...body]}
async function saveXlsx(aoa,name,sheet){
  try{const X=await loadXlsx();const ws=X.utils.aoa_to_sheet(aoa);ws['!cols']=aoa[0].map((h,i)=>({wch:Math.min(60,Math.max(8,...aoa.slice(0,300).map(r=>String(r[i]??'').length*1.6)))}));
    const wb=X.utils.book_new();X.utils.book_append_sheet(wb,ws,sheet);X.writeFile(wb,name+'.xlsx')}
  catch(e){const csv=aoa.map(r=>r.map(v=>{v=v==null?'':String(v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}).join(',')).join('\r\n');
    const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));a.download=name+'.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}}
document.addEventListener('click',async ev=>{const b=ev.target.closest('button[data-x]');if(!b)return;const k=b.dataset.x,t0=b.textContent;b.disabled=true;b.textContent='만드는 중...';
  try{
    if(k==='list'){const tb=$('#lst');if(tb)await saveXlsx(tableRows(tb),'surge_list_'+DATES[DATES.length-1],'종목목록')}
    if(k==='calendar'&&T2X){await saveXlsx([['순위','종목명','종목코드','시장','상승률(%)','거래대금(억)','시가총액(억)','종가','상승 이유','기사 링크'],...T2X.rows],'top200_'+T2X.date,'상승200')}
    if(k==='reasons'){const tb=$('#tw5 table');if(tb){const a=tableRows(tb);const links=[...tb.querySelectorAll('tbody tr')].map(r=>{const l=r.querySelector('a[href^="http"]');return l?l.href:''});a[0].push('기사 링크');a.slice(1).forEach((r,i)=>r.push(links[i]||''));await saveXlsx(a,'reasons_'+$('#rs-dt').value,'상승이유')}}
  }finally{b.disabled=false;b.textContent=t0}});

/* ---------- 마지막 업데이트 시각 · 수동 업데이트 ---------- */
fetch('data/updated.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(u=>{if(u)$('#upd-t').textContent='최종 업데이트 '+u.t+' (시세 '+u.d+')'}).catch(()=>{});
$('#upd-btn').addEventListener('click',()=>{$('#upd-note').hidden=false});
