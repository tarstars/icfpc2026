import{_ as e,at as t,l as n,m as r,st as i,v as a,w as o,y as s}from"./ui-wC2GCM-8.js";import{p as c}from"./index-RPCgG-2I.js";import{t as l}from"./problem-order-BQKUI1UZ.js";var u=i(t()),d=o(),f=a.section`
  margin-top: 24px;

  && h2 {
    margin: 0 0 4px;
  }
  && ul {
    margin: 0;
  }
`;function p(){let{data:t,isLoading:i}=c(),a=(0,u.useMemo)(()=>{let e=(t??[]).filter(e=>e.status===`graded`&&e.problemSetVisible);e.sort((e,t)=>(e.orderInSet??1/0)-(t.orderInSet??1/0));let n=new Map;for(let t of e){let e=t.problemSetName??`Unassigned`,r=n.get(e);r?r.push(t):n.set(e,[t])}return[...n.entries()].sort(([e],[t])=>l(e)-l(t)||e.localeCompare(t,void 0,{numeric:!0}))},[t]);return(0,d.jsxs)(r,{children:[(0,d.jsx)(`p`,{children:(0,d.jsx)(s,{to:`/standings`,children:`← Overall standings`})}),(0,d.jsx)(`h1`,{children:`Standings by problem`}),i&&(0,d.jsx)(`p`,{children:`Loading…`}),!i&&a.length===0&&(0,d.jsx)(`p`,{children:(0,d.jsx)(n,{children:`No graded problems yet.`})}),a.map(([t,n])=>(0,d.jsxs)(f,{children:[(0,d.jsx)(`h2`,{children:t}),(0,d.jsx)(e,{children:n.map(e=>(0,d.jsx)(`li`,{children:(0,d.jsx)(s,{to:`/standings/$slug`,params:{slug:e.slug},children:e.name})},e.id))})]},t))]})}export{p as component};