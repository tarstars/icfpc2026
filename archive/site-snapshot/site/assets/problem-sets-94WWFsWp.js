import{at as e,l as t,m as n,r,st as i,v as a,w as o,y as s}from"./ui-wC2GCM-8.js";import{A as c,L as l,p as u,v as d}from"./index-RPCgG-2I.js";import{t as f}from"./score-DbyPN9BI.js";import{t as p}from"./problem-order-BQKUI1UZ.js";var m=i(e()),h=o(),g=a(r)`
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: baseline;
  column-gap: 24px;
  row-gap: 2px;
  padding: 6px 10px;
  margin-bottom: 6px;
  max-width: 640px;
`,_=a.h3`
  && {
    grid-area: 1 / 1;
    margin: 0;
  }
`,v={solved:`var(--color-green-700)`,attempted:`var(--color-yellow-900)`,untouched:`var(--color-stone-400)`},y=a.div`
  grid-area: 1 / 2;
  text-align: right;
  font-size: var(--font-size-regular);
  color: ${e=>v[e.$tone]};
`,b=a.div`
  grid-area: 2 / 1;
  font-size: var(--font-size-small);
`,x=a.div`
  grid-area: 2 / 2;
  text-align: right;
  font-size: var(--font-size-small);
  color: var(--color-stone-500);
`;function S(e,t,n){if(!e)return t?{tone:`untouched`,value:`not attempted`,rank:null}:null;let r=e.casesTotal>0&&e.bestCasesPassed===e.casesTotal,i=e.bestCasesPassed>0,a=e.rank!=null&&e.fieldSize!=null?{rank:e.rank,of:e.fieldSize}:n&&i?{rank:6,of:11}:null;return r?{tone:`solved`,value:e.score==null?`solved`:(0,h.jsxs)(h.Fragment,{children:[`solved: `,(0,h.jsx)(f,{value:e.score})]}),rank:a}:{tone:`attempted`,value:`${e.bestCasesPassed} of ${e.casesTotal} tests passed`,rank:a}}function C({problem:e,status:t,graded:n}){let{data:r}=l(),i=S(t,n,r?.user.role===`admin`);return(0,h.jsxs)(g,{children:[(0,h.jsx)(_,{children:(0,h.jsx)(s,{to:`/problems/$slug`,params:{slug:e.slug},children:e.name})}),i&&(0,h.jsx)(y,{$tone:i.tone,children:i.value}),n&&(0,h.jsx)(b,{children:(0,h.jsx)(s,{to:`/standings/$slug`,params:{slug:e.slug},children:`Standings →`})}),i?.rank&&(0,h.jsxs)(x,{children:[`rank `,i.rank.rank,` of `,i.rank.of]})]})}var w=a.details`
  margin-top: 1.5rem;

  summary {
    cursor: pointer;
    font-size: var(--font-size-large);
    font-weight: 700;
    margin-bottom: 0.4em;
    color: var(--color-stone-600);
  }

  summary::marker {
    color: var(--color-stone-500);
  }
`;function T(){let{data:e,isPending:r}=l(),i=c(e),{data:a,isLoading:o}=u(),{data:f}=d({enabled:!!e}),g=(0,m.useMemo)(()=>{let e=new Map;for(let t of f??[])e.set(t.problemId,t);return e},[f]),{semesters:_,practiceSets:v,unpublished:y}=(0,m.useMemo)(()=>{let e=new Map,t=new Map,n=[],r=[...a??[]].sort((e,t)=>(e.orderInSet??1/0)-(t.orderInSet??1/0));for(let i of r){if(i.status===`practice`){if(i.problemSetName&&i.problemSetVisible){let e=t.get(i.problemSetName);e||(e=[],t.set(i.problemSetName,e)),e.push(i)}else n.push(i);continue}if(!i.problemSetName)continue;let r=e.get(i.problemSetName);r||(r={visible:i.problemSetVisible??!1,problems:[]},e.set(i.problemSetName,r)),r.problems.push(i)}return{semesters:[...e.entries()].sort(([e,t],[n,r])=>Number(r.visible)-Number(t.visible)||p(e)-p(n)||e.localeCompare(n,void 0,{numeric:!0})),practiceSets:[...t.entries()].sort(([e],[t])=>e.localeCompare(t,void 0,{numeric:!0})),unpublished:n}},[a]);return r?(0,h.jsx)(n,{children:(0,h.jsx)(`p`,{children:`Loading…`})}):!i&&!o&&_.length===0&&v.length===0?(0,h.jsxs)(n,{children:[(0,h.jsx)(`h1`,{children:`Problem Sets`}),(0,h.jsx)(`p`,{children:(0,h.jsx)(t,{children:`No problem sets have been released yet. Check back soon.`})})]}):(0,h.jsxs)(n,{children:[(0,h.jsx)(`h1`,{children:`Problem Sets`}),(0,h.jsxs)(`p`,{children:[`Before starting on the problem sets, you may want to read the`,` `,(0,h.jsx)(s,{to:`/textbook`,children:`textbook`}),`.`]}),v.map(([e,t])=>(0,h.jsxs)(w,{children:[(0,h.jsx)(`summary`,{children:e}),t.map(e=>(0,h.jsx)(C,{problem:e,status:g.get(e.id),graded:!1},e.id))]},e)),o&&(0,h.jsx)(`p`,{children:`Loading…`}),!o&&_.length===0&&v.length===0&&y.length===0&&(0,h.jsx)(`p`,{children:(0,h.jsx)(t,{children:`No problems assigned to a set yet.`})}),_.map(([e,{problems:t}])=>(0,h.jsxs)(`section`,{children:[(0,h.jsx)(`h2`,{children:e}),t.map(e=>(0,h.jsx)(C,{problem:e,status:g.get(e.id),graded:!0},e.id))]},e)),y.length>0&&(0,h.jsxs)(w,{children:[(0,h.jsx)(`summary`,{children:`Unpublished Problems`}),y.map(e=>(0,h.jsx)(C,{problem:e,status:g.get(e.id),graded:!1},e.id))]})]})}export{T as component};