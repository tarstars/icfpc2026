import{at as e,c as t,l as n,m as r,st as i,v as a,w as o,y as s}from"./ui-wC2GCM-8.js";import{L as c,a as l,b as u,u as d}from"./index-RPCgG-2I.js";var f=i(e()),p=o();function m(e){return`${l(Math.max(0,Math.round((Date.now()-Date.parse(e))/1e3)))} ago`}function h({id:e}){let[t,n]=(0,f.useState)(!1);return(0,p.jsx)(E,{type:`button`,title:`Copy id`,onClick:()=>{navigator.clipboard.writeText(e).then(()=>{n(!0),setTimeout(()=>n(!1),1200)},()=>{})},children:t?`copied`:e})}function g({id:e}){let t=u();return(0,p.jsx)(E,{type:`button`,title:`Re-enqueue for the runner`,disabled:t.isPending,onClick:()=>t.mutate(e),children:t.isPending?`requeuing…`:t.isError?`failed — retry`:t.data?t.data.requeued.length>0?`requeued`:`already done`:`requeue`})}function _({name:e,slug:t}){return t?(0,p.jsx)(s,{to:`/standings/$slug`,params:{slug:t},children:e}):(0,p.jsx)(p.Fragment,{children:e})}function v({team:e,teamId:t,isTest:r}){return(0,p.jsxs)(p.Fragment,{children:[(0,p.jsx)(s,{to:`/standings/team/$teamId`,params:{teamId:t},children:e}),r&&(0,p.jsx)(n,{children:` (test)`})]})}function y(){let{data:e,isPending:t}=c(),{data:r,isPending:i,isError:a}=d();return t?(0,p.jsx)(b,{children:(0,p.jsx)(`p`,{children:`Loading…`})}):e?.user.role===`admin`?(0,p.jsxs)(b,{children:[(0,p.jsx)(`h1`,{children:`Grading queue`}),(0,p.jsxs)(`p`,{children:[(0,p.jsx)(s,{to:`/admin`,children:`← Admin`}),` ·`,` `,(0,p.jsx)(s,{to:`/queue`,children:`public view`})]}),i?(0,p.jsx)(`p`,{children:`Loading…`}):a||!r?(0,p.jsx)(`p`,{children:(0,p.jsx)(n,{children:`Couldn't load queue detail. Try reloading.`})}):(0,p.jsxs)(p.Fragment,{children:[(0,p.jsxs)(x,{children:[r.pending,` pending · `,r.running,` running`,r.oldestPendingSec!==null&&(0,p.jsxs)(p.Fragment,{children:[` · oldest pending `,l(r.oldestPendingSec)]}),r.oldestRunningSec!==null&&(0,p.jsxs)(p.Fragment,{children:[` · oldest running `,l(r.oldestRunningSec)]}),(0,p.jsx)(`br`,{}),`last hour: `,r.completedLastHour,` done, `,r.failedLastHour,` `,`failed`,r.medianLatencySec!==null&&(0,p.jsxs)(p.Fragment,{children:[` `,`· latency median `,l(r.medianLatencySec),r.p90LatencySec!==null&&` / p90 ${l(r.p90LatencySec)}`]}),(0,p.jsx)(`br`,{}),(0,p.jsxs)(n,{children:[`As of `,new Date(r.asOf).toLocaleTimeString(),`. Updates every 10s.`]})]}),(0,p.jsxs)(`h2`,{children:[`In flight (`,r.queued.length,`)`]}),r.queued.length===0?(0,p.jsx)(`p`,{children:(0,p.jsx)(n,{children:`The queue is empty.`})}):(0,p.jsxs)(S,{children:[(0,p.jsx)(`thead`,{children:(0,p.jsxs)(`tr`,{children:[(0,p.jsx)(C,{children:`Team`}),(0,p.jsx)(C,{children:`Problem`}),(0,p.jsx)(C,{children:`Status`}),(0,p.jsx)(C,{$num:!0,children:`Waiting`}),(0,p.jsx)(C,{children:`Submitted`}),(0,p.jsx)(C,{children:`Id`}),(0,p.jsx)(C,{})]})}),(0,p.jsx)(`tbody`,{children:r.queued.map(e=>(0,p.jsxs)(`tr`,{children:[(0,p.jsx)(w,{children:(0,p.jsx)(v,{team:e.team,teamId:e.teamId,isTest:e.isTest})}),(0,p.jsx)(w,{children:(0,p.jsx)(_,{name:e.problem,slug:e.slug})}),(0,p.jsx)(w,{children:e.status}),(0,p.jsx)(w,{$num:!0,children:l(e.latencySec)}),(0,p.jsx)(w,{children:m(e.createdAt)}),(0,p.jsx)(T,{children:(0,p.jsx)(h,{id:e.id})}),(0,p.jsx)(w,{children:(0,p.jsx)(g,{id:e.id})})]},e.id))})]}),(0,p.jsx)(`h2`,{children:`Recently finished`}),r.recent.length===0?(0,p.jsx)(`p`,{children:(0,p.jsx)(n,{children:`Nothing graded yet.`})}):(0,p.jsxs)(S,{children:[(0,p.jsx)(`thead`,{children:(0,p.jsxs)(`tr`,{children:[(0,p.jsx)(C,{children:`Team`}),(0,p.jsx)(C,{children:`Problem`}),(0,p.jsx)(C,{children:`Result`}),(0,p.jsx)(C,{$num:!0,children:`Took`}),(0,p.jsx)(C,{children:`Finished`}),(0,p.jsx)(C,{children:`Id`})]})}),(0,p.jsx)(`tbody`,{children:r.recent.map(e=>(0,p.jsxs)(`tr`,{children:[(0,p.jsx)(w,{children:(0,p.jsx)(v,{team:e.team,teamId:e.teamId,isTest:e.isTest})}),(0,p.jsx)(w,{children:(0,p.jsx)(_,{name:e.problem,slug:e.slug})}),(0,p.jsx)(w,{children:e.status===`failed`?`failed`:e.casesTotal===null?`done`:(0,p.jsxs)(p.Fragment,{children:[e.casesPassed,`/`,e.casesTotal]})}),(0,p.jsx)(w,{$num:!0,children:l(e.latencySec)}),(0,p.jsx)(w,{children:m(e.updatedAt)}),(0,p.jsx)(T,{children:(0,p.jsx)(h,{id:e.id})})]},e.id))})]})]})]}):(0,p.jsxs)(b,{children:[(0,p.jsx)(`h1`,{children:`Grading queue`}),(0,p.jsxs)(`p`,{children:[(0,p.jsx)(n,{children:`Teaching assistants only. `}),(0,p.jsx)(s,{to:`/login`,children:`Sign in`})]})]})}var b=a(r)`
  max-width: 1240px;
`,x=a.p`
  line-height: 1.6;
`,S=a.table`
  border-collapse: collapse;
  font-size: var(--font-size-small);
  margin-bottom: 1.5em;
`,C=a.th`
  border: 1px solid var(--color-stone-400);
  padding: 0.3em 0.7em;
  text-align: ${e=>e.$num?`right`:`left`};
`,w=a.td`
  border: 1px solid var(--color-stone-400);
  padding: 0.3em 0.7em;
  text-align: ${e=>e.$num?`right`:`left`};
  ${e=>e.$num&&`font-family: ui-monospace, SFMono-Regular, Menlo, monospace;`}
`,T=a(w)`
  font-family: ${t};
  font-size: var(--font-size-xsmall);
  white-space: nowrap;
`,E=a.button`
  font: inherit;
  color: inherit;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
`;export{y as component};