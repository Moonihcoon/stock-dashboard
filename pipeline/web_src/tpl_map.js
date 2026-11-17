/* ---------- 탭: 시장 지도 (업종 트리맵 · 연도 칩 · 타임라인 바) ----------
   기존 탭 코드의 $, fmt, f1, ld, ldz, DATES, MKT, TICK/loadTick, TH/loadTh, RSMAP/loadRs, topMonth, stockRows,
   mountChart, saveXlsx, esc, safeUrl 을 그대로 씁니다. 이름이 겹치지 않도록 이 파일은 함수 하나로 감쌉니다. */
window.tabMap=(()=>{
const WD=['일','월','화','수','목','금','토'];
let inited=false,SPK={s:0,a:[],u:[]},DAYM=null,busy=false,STRONG=[];
const S={di:0,mk:'',th:'',q:'',sel:null,view:'map',play:null};
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{v?localStorage.setItem(k,v):localStorage.removeItem(k)}catch(e){}}};
const E=id=>document.getElementById('mp-'+id);

/* 하루치 데이터 */
async function loadDayM(di){
  const date=DATES[di],m=await topMonth(date.slice(0,7)),rows=m[di]||[];
  const TD=TH[date]||{top:[],map:{}};
  const items=rows.map((r,k)=>{const t=TICK[r[0]],L=RSMAP[date+'|'+t[1]]||[],a=L.find(z=>z.dir!=='down');
    return {rk:k+1,ti:r[0],code:t[0],name:t[1],mkt:t[2],ind:t[3]||'',rate:r[1],val:r[2],close:r[3],mc:r[4],why:a?(a.r||a.h):'',url:a?a.u:'',src:a?(a.s||''):'',L,th:TD.map[t[1]]||''}});
  const withInd=items.filter(x=>x.ind).length,byInd=items.length>0&&withInd>=items.length*.5;
  items.forEach(x=>{x.grp=byInd?(x.ind||'기타'):(x.mkt==='KOSPI'?'코스피':'코스닥')});
  return {date,items,TD,byInd,n:rows.length};
}
function filt(){const q=S.q.trim().toLowerCase();
  return DAYM.items.filter(x=>(!S.mk||x.mkt===S.mk)&&(!S.th||x.th===S.th)&&(!q||x.name.toLowerCase().includes(q)||x.why.toLowerCase().includes(q)||x.th.toLowerCase().includes(q)||x.ind.toLowerCase().includes(q)))}

/* 트리맵 */
function squarify(items,x,y,w,h){const out=[];const total=items.reduce((s,i)=>s+i.v,0);if(!total||w<=0||h<=0)return out;
  const k=(w*h)/total,arr=items.map(i=>({i,a:i.v*k}));let row=[],rx=x,ry=y,rw=w,rh=h;
  const worst=(r,side)=>{const s=r.reduce((t,q)=>t+q.a,0);let mx=0,mn=1e18;r.forEach(q=>{mx=Math.max(mx,q.a);mn=Math.min(mn,q.a)});return Math.max(side*side*mx/(s*s),(s*s)/(side*side*mn))};
  const lay=r=>{const s=r.reduce((t,q)=>t+q.a,0);
    if(rw>=rh){const cw=s/rh;let cy=ry;r.forEach(q=>{const ch=q.a/cw;out.push({i:q.i,x:rx,y:cy,w:cw,h:ch});cy+=ch});rx+=cw;rw-=cw}
    else{const ch=s/rw;let cx=rx;r.forEach(q=>{const cw=q.a/ch;out.push({i:q.i,x:cx,y:ry,w:cw,h:ch});cx+=cw});ry+=ch;rh-=ch}};
  for(const it of arr){const side=Math.min(rw,rh);if(!row.length||worst(row.concat(it),side)<=worst(row,side))row.push(it);else{lay(row);row=[it]}}
  if(row.length)lay(row);return out}
const shade=r=>{const a=Math.round(22+Math.min(Math.max(r,0),30)/30*68);return `color-mix(in srgb,var(--up) ${a}%,var(--panel))`};
function drawMap(){
  const svg=E('tm'),box=E('wrap'),W=box.clientWidth,H=box.clientHeight;if(!W||!DAYM)return;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  const list=filt();
  if(!list.length){svg.innerHTML=`<text x="${W/2}" y="${H/2}" text-anchor="middle" style="fill:var(--ink-2);font-size:14px">${DAYM.n?'조건에 맞는 종목이 없습니다.':'이 날짜는 자료가 없습니다(휴장일).'}</text>`;E('hint').textContent='';return}
  const g={};list.forEach(x=>{(g[x.grp]=g[x.grp]||{name:x.grp,kids:[],v:0}).kids.push(x)});
  const groups=Object.values(g).map(o=>{o.kids.forEach(k=>k.v=Math.max(k.val,3));o.kids.sort((a,b)=>b.v-a.v);o.v=o.kids.reduce((s,k)=>s+k.v,0);return o}).sort((a,b)=>b.v-a.v);
  const top=44,pad=4,rects=squarify(groups,pad,top,W-pad*2,H-top-pad);let out='';
  rects.forEach(R=>{const G=R.i,hh=R.w>60&&R.h>34?15:0,ix=R.x+2,iy=R.y+2+hh,iw=R.w-4,ih=R.h-4-hh,mx=Math.max(1,Math.floor(R.w/11));
    if(hh)out+=`<text class="gl" x="${R.x+5}" y="${R.y+14}">${esc(G.name.length>mx?G.name.slice(0,Math.max(1,mx-1))+'…':G.name)} · ${G.kids.length}</text>`;
    squarify(G.kids,ix,iy,iw,ih).forEach(T=>{const k=T.i,big=T.w>58&&T.h>30,mid=T.w>40&&T.h>20,c=Math.max(1,Math.floor(T.w/12));
      const nm=k.name.length>c?k.name.slice(0,Math.max(1,c-1))+'…':k.name;
      out+=`<g class="tile${S.sel===k.ti?' sel':''}" data-ti="${k.ti}" tabindex="0" role="button" aria-label="${esc(k.name)} +${f1(k.rate)}%"><rect x="${T.x}" y="${T.y}" width="${Math.max(0,T.w)}" height="${Math.max(0,T.h)}" rx="3" fill="${shade(k.rate)}"/>`+
        (mid?`<text x="${T.x+5}" y="${T.y+15}" font-size="12" font-weight="600" style="fill:var(--ink)">${esc(nm)}</text>`:'')+
        (big?`<text x="${T.x+5}" y="${T.y+30}" font-size="11.5" style="fill:var(--ink)">+${f1(k.rate)}%</text>`:'')+`</g>`});
  });
  svg.innerHTML=out;
  E('hint').textContent=`칸 크기=거래대금 · 색=상승률 · ${DAYM.byInd?'업종별':'시장별'} · ${list.length}종목`;
}

/* 패널 */
function renderPanel(){
  const d=new Date(DAYM.date+'T00:00:00'),items=DAYM.items;
  E('pt').innerHTML=`${DAYM.date}<small>${WD[d.getDay()]}요일</small>`;
  const cnt=m=>items.filter(x=>x.mkt===m).length;
  E('lead').innerHTML=items.length?`상승률 상위 ${items.length}개 (코스피 ${cnt('KOSPI')} · 코스닥 ${cnt('KOSDAQ')}). 1위 <b>${esc(items[0].name)}</b> <span style="color:var(--up)">+${f1(items[0].rate)}%</span>`:'이 날짜는 시세 자료가 없습니다(휴장일).';
  E('mk').innerHTML=[['','전체'],['KOSPI','코스피'],['KOSDAQ','코스닥']].map(([v,t])=>`<button type="button" class="pchip" data-mk="${v}" aria-pressed="${S.mk===v}">${t}</button>`).join('');
  E('th').innerHTML=DAYM.TD.top.length?`<span style="font-size:12px;color:var(--ink-2);align-self:center">테마</span>`+DAYM.TD.top.map(t=>`<button type="button" class="pchip" data-th="${esc(t[0])}" aria-pressed="${S.th===t[0]}">${esc(t[0])}<small>${t[1]}</small></button>`).join(''):'';
  renderSel();renderList();
  E('memo').value=store.get('r200memo:'+DAYM.date)||'';
}
function renderSel(){
  const k=DAYM.items.find(x=>x.ti===S.sel);
  E('sel').innerHTML=k?`<div class="sel-card"><h3>${esc(k.name)} <small style="font-weight:400;color:var(--ink-2)">${k.code} · ${MKT(k.mkt)}</small></h3>
  <div class="kv"><span>상승률 <b style="color:var(--up)">+${f1(k.rate)}%</b></span><span>거래대금 <b>${fmt(k.val)}억</b></span><span>시가총액 <b>${k.mc==null?'–':fmt(k.mc)+'억'}</b></span><span>종가 <b>${fmt(k.close)}</b></span>${k.ind?`<span>업종 <b>${esc(k.ind)}</b></span>`:''}${k.th?`<span>테마 <b>${esc(k.th)}</b></span>`:''}</div>
  ${k.L.length?`<ul>${k.L.slice(0,5).map(a=>`<li><a href="${esc(safeUrl(a.u))}" target="_blank" rel="noopener noreferrer">${esc(a.r||a.h)}</a> <span style="color:var(--ink-3);font-size:11.5px">${esc(a.s||'')}</span></li>`).join('')}</ul>`:'<div style="font-size:12.5px;color:var(--ink-2)">연결된 공시·뉴스가 없습니다 (수급/테마 가능성).</div>'}</div>`:'';
}
const hl=(s,q)=>{s=esc(s);if(!q)return s;const e=esc(q),i=s.toLowerCase().indexOf(e.toLowerCase());return i<0?s:s.slice(0,i)+'<mark>'+s.slice(i,i+e.length)+'</mark>'+s.slice(i+e.length)};
function renderList(){const L=filt(),q=S.q.trim();
  E('list').innerHTML=L.length?L.map(x=>`<li class="${S.sel===x.ti?'sel':''}"><button type="button" data-ti="${x.ti}"><span class="rk">${x.rk}</span><span class="nm">${hl(x.name,q)}<small style="font-weight:400;color:var(--ink-3)"> ${esc(x.ind||MKT(x.mkt))}</small></span><span class="rt">+${f1(x.rate)}%</span><span class="rs">${x.why?hl(x.why,q):(x.th?'테마: '+hl(x.th,q)+' · 뉴스·공시 미확인':'수급/테마 (뉴스 미확인)')}</span></button></li>`).join(''):`<li class="mp-empty">${DAYM.n?'조건에 맞는 종목이 없습니다.':'자료가 없습니다.'}</li>`;
}
async function pick(ti,toChart){S.sel=ti;renderSel();renderList();if(S.view==='map')drawMap();if(toChart)setView('chart');else if(S.view==='chart')await drawChartView()}

/* 일봉 차트 화면 */
async function drawChartView(){
  const k=DAYM.items.find(x=>x.ti===S.sel),box=E('cb');
  if(!k){E('ct').textContent='지도나 목록에서 종목을 고르면 일봉이 나옵니다.';box.replaceChildren();box._shell=0;return}
  E('ct').textContent=k.name+' 불러오는 중...';
  try{const di=S.di,rows=await stockRows(k.ti,Math.max(0,di-120),Math.min(DATES.length-1,di+20)),rp=rows.find(x=>x[0]===di);
    if(!rows.length||!rp){E('ct').textContent=k.name+': 이 날짜 주변 시세가 없습니다.';box.replaceChildren();box._shell=0;return}
    E('ct').textContent=`${k.name} (${MKT(k.mkt)}) 일봉 · 선택일 ${DATES[di]} · 아래 막대 거래대금(억원)`;
    mountChart(box,rows,{key:'m'+k.ti+'_'+di,marks:[{di,t:'선택일'}],ref:{p:rp[4],t:'선택일 종가 대비'},label:k.name+' 일봉'});
  }catch(e){E('ct').textContent='시세를 불러오지 못했습니다. 잠시 뒤 다시 눌러 주세요.'}}
function setView(v){S.view=v;E('vmap').setAttribute('aria-pressed',v==='map');E('vchart').setAttribute('aria-pressed',v==='chart');
  E('tm').style.display=v==='map'?'block':'none';E('hint').style.display=v==='map'?'block':'none';E('chartview').hidden=v!=='chart';
  if(v==='map')drawMap();else drawChartView()}

/* 타임라인 바 · 연도 칩 */
function drawTl(){
  const c=E('tlc'),box=E('tl');if(!SPK.a.length||!box.clientWidth)return;const dpr=window.devicePixelRatio||1,W=box.clientWidth,H=box.clientHeight;
  c.width=W*dpr;c.height=H*dpr;const x=c.getContext('2d');x.scale(dpr,dpr);x.clearRect(0,0,W,H);
  const cs=getComputedStyle(document.documentElement),up=cs.getPropertyValue('--up').trim()||'#c23b30',ink=cs.getPropertyValue('--ink').trim()||'#222';
  const n=DATES.length-SPK.s,mx=Math.max(...SPK.a.slice(SPK.s),1),bw=Math.max(1,W/n);
  for(let i=0;i<n;i++){const v=SPK.a[SPK.s+i],h=Math.max(2,(v/mx)*(H-6));x.globalAlpha=.25+.75*(v/mx);x.fillStyle=up;x.fillRect(i*W/n,H-h,Math.max(1,bw-.3),h)}
  x.globalAlpha=1;const cx=(S.di-SPK.s+.5)*W/n;x.fillStyle=ink;x.fillRect(cx-1,0,2,H);x.beginPath();x.arc(cx,5,5,0,7);x.fill();
}
function drawYears(){const n=DATES.length-SPK.s;let h='',last='';
  for(let i=SPK.s;i<DATES.length;i++){const y=DATES[i].slice(0,4);if(y!==last){last=y;h+=`<span style="left:${(i-SPK.s+.5)/n*100}%">${y}</span>`}}
  E('tlyr').innerHTML=h}
function buildEras(){const ys={};for(let i=SPK.s;i<DATES.length;i++){const y=DATES[i].slice(0,4);(ys[y]=ys[y]||[]).push(i)}
  E('eras').innerHTML=Object.entries(ys).map(([y,ix])=>{const best=ix.reduce((a,b)=>SPK.a[b]>SPK.a[a]?b:a);return `<button type="button" data-i="${best}" data-y="${y}">${y}년<small>${ix.length}거래일 · 최고 급등일 ${DATES[best].slice(5)}</small></button>`}).join('')}
function markEra(){document.querySelectorAll('#mp-eras button').forEach(b=>b.setAttribute('aria-current',b.dataset.y===DATES[S.di].slice(0,4)))}
function tlPick(ev){const r=E('tl').getBoundingClientRect(),n=DATES.length-SPK.s;go(SPK.s+Math.min(n-1,Math.max(0,Math.floor((ev.clientX-r.left)/r.width*n))))}

/* 이동·재생 */
async function go(di){di=Math.min(DATES.length-1,Math.max(SPK.s,di));if(di===S.di&&DAYM)return;S.di=di;await refresh(true)}
async function refresh(day){
  if(busy)return;busy=true;try{
    if(day||!DAYM||DAYM.date!==DATES[S.di])DAYM=await loadDayM(S.di);
    const d=new Date(DAYM.date+'T00:00:00');
    E('dtt').textContent=DAYM.date;E('dts').textContent=`${WD[d.getDay()]}요일 · 상위 10개 평균 +${f1(SPK.a[S.di])}% · 29.5%↑ ${SPK.u[S.di]}종목`;
    E('pick').value=DAYM.date;renderPanel();drawTl();markEra();
    if(S.view==='map')drawMap();else await drawChartView();
  }finally{busy=false}}
function stop(){if(S.play){clearInterval(S.play);S.play=null}E('play').setAttribute('aria-pressed',false);E('play').textContent='▶'}
const step=d=>{stop();go(S.di+d)};
const timer=()=>setInterval(async()=>{if(S.di>=DATES.length-1){stop();return}await go(S.di+1)},+E('spd').value);

function bind(){
  E('tm').addEventListener('mousemove',ev=>{const tip=E('tip'),g=ev.target.closest('.tile');if(!g){tip.style.display='none';return}
    const k=DAYM.items.find(x=>x.ti===+g.dataset.ti);if(!k)return;const r=E('wrap').getBoundingClientRect();
    tip.innerHTML=`<b>${esc(k.name)}</b> ${esc(k.grp)}<br>+${f1(k.rate)}% · 거래대금 ${fmt(k.val)}억<br>${k.why?esc(k.why):'<span style="opacity:.7">이유 미확인</span>'}`;
    tip.style.display='block';tip.style.left=Math.max(0,Math.min(ev.clientX-r.left+12,r.width-270))+'px';tip.style.top=(ev.clientY-r.top+14)+'px'});
  E('tm').addEventListener('mouseleave',()=>E('tip').style.display='none');
  E('tm').addEventListener('click',ev=>{const g=ev.target.closest('.tile');if(g)pick(+g.dataset.ti,true)});
  E('tm').addEventListener('keydown',ev=>{if(ev.key==='Enter'){const g=ev.target.closest('.tile');if(g)pick(+g.dataset.ti,true)}});
  E('list').addEventListener('click',ev=>{const b=ev.target.closest('button[data-ti]');if(b)pick(+b.dataset.ti,true)});
  E('mk').addEventListener('click',ev=>{const m=ev.target.closest('[data-mk]');if(m){S.mk=m.dataset.mk;renderPanel();if(S.view==='map')drawMap()}});
  E('th').addEventListener('click',ev=>{const t=ev.target.closest('[data-th]');if(t){S.th=S.th===t.dataset.th?'':t.dataset.th;renderPanel();if(S.view==='map')drawMap()}});
  E('q').addEventListener('input',()=>{S.q=E('q').value;renderList();if(S.view==='map')drawMap()});
  E('memob').onclick=()=>{const m=E('memo');m.hidden=!m.hidden;if(!m.hidden)m.focus()};
  E('memo').addEventListener('input',()=>store.set('r200memo:'+DAYM.date,E('memo').value));
  E('vmap').onclick=()=>setView('map');E('vchart').onclick=()=>setView('chart');
  E('eras').addEventListener('click',ev=>{const b=ev.target.closest('button[data-i]');if(b){stop();go(+b.dataset.i)}});
  let drag=false;const tl=E('tl');
  tl.addEventListener('pointerdown',ev=>{drag=true;tl.setPointerCapture(ev.pointerId);stop();tlPick(ev)});
  tl.addEventListener('pointermove',ev=>{if(drag)tlPick(ev)});tl.addEventListener('pointerup',()=>drag=false);
  E('prev').onclick=()=>step(-1);E('next').onclick=()=>step(1);
  E('prevs').onclick=()=>{stop();const p=[...STRONG].reverse().find(i=>i<S.di);if(p!=null)go(p)};
  E('nexts').onclick=()=>{stop();const n=STRONG.find(i=>i>S.di);if(n!=null)go(n)};
  E('pick').onchange=()=>{const v=E('pick').value;if(!v)return;stop();let i=DATES.indexOf(v);if(i<0){const j=DATES.findIndex(x=>x>v);i=j<0?DATES.length-1:Math.max(SPK.s,j-1)}go(i)};
  E('play').onclick=()=>{if(S.play){stop();return}E('play').setAttribute('aria-pressed',true);E('play').textContent='⏸';if(S.di>=DATES.length-1)S.di=SPK.s;S.play=timer()};
  E('spd').onchange=()=>{if(S.play){clearInterval(S.play);S.play=timer()}};
  document.addEventListener('keydown',ev=>{if($('#p-map').hidden||/INPUT|TEXTAREA|SELECT/.test(ev.target.tagName))return;if(ev.key==='ArrowLeft')step(-1);if(ev.key==='ArrowRight')step(1)});
  E('xl').onclick=async()=>{if(!DAYM)return;const b=E('xl'),t0=b.textContent;b.disabled=true;b.textContent='만드는 중...';
    try{await saveXlsx([['순위','종목명','종목코드','시장','업종','상승률(%)','거래대금(억)','시가총액(억)','종가','상승 이유','테마','근거 링크','출처'],
      ...filt().map(x=>[x.rk,x.name,x.code,MKT(x.mkt),x.ind,x.rate,x.val,x.mc,x.close,x.why||'수급/테마 (뉴스 미확인)',x.th,x.url,x.src])],'rank200_'+DAYM.date,'시장지도')}
    finally{b.disabled=false;b.textContent=t0}};
  new ResizeObserver(()=>{if(!inited||$('#p-map').hidden)return;if(S.view==='map')drawMap();drawTl()}).observe(E('wrap'));
  const mq=matchMedia('(prefers-color-scheme:dark)');mq.addEventListener&&mq.addEventListener('change',()=>{if(inited&&!$('#p-map').hidden){drawTl();if(S.view==='map')drawMap()}});
}

return async function tabMap(){
  if(inited){drawTl();if(S.view==='map')drawMap();return}
  const sp=await ld('data/spark.json');
  await Promise.all([loadTick(),loadTh(),loadRs()]);
  SPK=sp;inited=true;bind();
  const vals=SPK.a.slice(SPK.s).filter(v=>v>0).sort((a,b)=>a-b),p90=vals[Math.floor(vals.length*.9)]||0;
  for(let i=SPK.s;i<DATES.length;i++)if(p90>0&&SPK.a[i]>=p90)STRONG.push(i);
  buildEras();drawYears();E('pick').min=DATES[SPK.s];E('pick').max=DATES[DATES.length-1];
  S.di=-1;await go(DATES.length-1);
};
})();
