import{c as e,l as t,m as n,v as r,w as i}from"./ui-wC2GCM-8.js";import{y as a}from"./index-RPCgG-2I.js";var o=i();function s(e){if(e<60)return`${e}s`;let t=Math.floor(e/60),n=e%60;return n>0?`${t}m ${n}s`:`${t}m`}function c(){let{data:e,isPending:r,isError:i}=a();return(0,o.jsxs)(n,{children:[(0,o.jsx)(`h1`,{children:`Grading queue`}),r?(0,o.jsx)(`p`,{children:`Loading…`}):i||!e?(0,o.jsx)(`p`,{children:(0,o.jsx)(t,{children:`Couldn't load queue status. Try reloading.`})}):(0,o.jsxs)(o.Fragment,{children:[(0,o.jsx)(l,{children:e.medianLatencySec===null?(0,o.jsx)(o.Fragment,{children:`No submissions were graded in the last hour.`}):(0,o.jsxs)(o.Fragment,{children:[`Submissions are taking about`,` `,(0,o.jsx)(d,{children:s(e.medianLatencySec)}),` from submit to result.`]})}),(0,o.jsxs)(u,{children:[(0,o.jsxs)(`li`,{children:[(0,o.jsx)(d,{children:e.inFlight}),` submission`,e.inFlight===1?``:`s`,` in the queue right now`]}),(0,o.jsxs)(`li`,{children:[(0,o.jsx)(d,{children:e.completedLastHour}),` graded in the last hour`,e.p90LatencySec!==null&&(0,o.jsxs)(o.Fragment,{children:[` `,`(90% within `,(0,o.jsx)(d,{children:s(e.p90LatencySec)}),`)`]})]})]}),(0,o.jsx)(`p`,{children:(0,o.jsxs)(t,{children:[`As of `,new Date(e.asOf).toLocaleTimeString(),`. Updates automatically.`]})})]})]})}var l=r.p`
  font-size: var(--font-size-large);
`,u=r.ul`
  margin: 0 0 1em;
  padding-left: 1.5em;

  li {
    margin-bottom: 0.35em;
  }
`,d=r.span`
  font-family: ${e};
`;export{c as component,s as fmtDuration};