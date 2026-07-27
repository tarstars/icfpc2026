import{d as e,l as t,v as n,w as r,y as i}from"./ui-wC2GCM-8.js";import{C as a,_ as o}from"./index-RPCgG-2I.js";import{t as s}from"./score-DbyPN9BI.js";var c=r(),l=n.table`
  border-collapse: collapse;
  margin: 12px 0 20px;
  font-size: var(--font-size-regular);
  max-width: 100%;

  /* A cell's rule spans its padding too, so padding on the outer edges ran the
     header line past the text it underlines — and past the heading above it.
     Dropping it lands the line's ends on the first and last columns' text, and
     the table's left edge on the page margin with everything else. */
  th:first-child,
  td:first-child {
    padding-left: 0;
  }
  th:last-child,
  td:last-child {
    padding-right: 0;
  }
`,u=n.th`
  text-align: ${e=>e.$num?`right`:`left`};
  white-space: nowrap;
  border-bottom: 2px solid var(--color-stone-400);
  padding: 6px 14px;
  font-size: var(--font-size-small);
  color: var(--color-stone-600);
`,d=n.td`
  border-bottom: 1px solid var(--color-stone-200);
  padding: 6px 14px;
  text-align: ${e=>e.$num?`right`:`left`};
  white-space: ${e=>e.$num?`nowrap`:`normal`};
`,f=n(d)`
  max-width: 40ch;
`,p=n.section`
  margin-top: 28px;

  && h2 {
    margin: 0 0 4px;
    line-height: 1.1;
  }
  && table {
    margin: 0;
  }
`,m=n.p`
  && {
    margin: 0 0 6px;
    line-height: 1;
    font-size: var(--font-size-small);
    color: var(--color-stone-500);
  }
`;function h(e){return e.toFixed(2)}function g(e){return e?new Date(e).toLocaleString():`not yet computed`}function _({updatedAt:n,frozen:r}){return(0,c.jsxs)(c.Fragment,{children:[(0,c.jsx)(`p`,{children:(0,c.jsxs)(t,{children:[`Last updated `,g(n),`.`]})}),r&&(0,c.jsx)(e,{children:`Standings are currently frozen.`})]})}function v(){let{data:e}=a();return e?(0,c.jsx)(_,{updatedAt:e.updatedAt,frozen:e.frozen}):null}function y({teamId:e,teamName:t}){return(0,c.jsx)(i,{to:`/standings/team/$teamId`,params:{teamId:e},children:t??e})}function b(){let{data:e,isLoading:n}=a();return n?(0,c.jsx)(`p`,{children:`Loading…`}):e?e.teams.length===0?(0,c.jsx)(`p`,{children:(0,c.jsx)(t,{children:`No standings yet.`})}):(0,c.jsxs)(l,{children:[(0,c.jsx)(`thead`,{children:(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(u,{children:`Rank`}),(0,c.jsx)(u,{children:`Team`}),(0,c.jsx)(u,{$num:!0,children:`Points`}),(0,c.jsx)(u,{$num:!0,children:`Fully solved`})]})}),(0,c.jsx)(`tbody`,{children:e.teams.map(t=>(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(d,{children:t.rank}),(0,c.jsx)(f,{children:(0,c.jsx)(y,{teamId:t.teamId,teamName:t.teamName})}),(0,c.jsx)(d,{$num:!0,children:h(t.points)}),(0,c.jsxs)(d,{$num:!0,children:[t.fullPasses,`/`,e.problemCount]})]},t.teamId))})]}):null}var x=e=>e.casesTotal>0&&e.casesPassed===e.casesTotal,S=n.tr`
  & > td {
    padding-top: 20px;
  }
`;function C({rows:e}){return(0,c.jsxs)(l,{children:[(0,c.jsx)(`thead`,{children:(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(u,{children:`Problem`}),(0,c.jsx)(u,{children:`Set`}),(0,c.jsx)(u,{$num:!0,children:`Rank`}),(0,c.jsx)(u,{$num:!0,children:`Passed`}),(0,c.jsx)(u,{$num:!0,children:`Score`}),(0,c.jsx)(u,{$num:!0,children:`Points`})]})}),(0,c.jsx)(`tbody`,{children:e.map((n,r)=>(0,c.jsxs)(r>0&&e[r-1].set!==n.set?S:`tr`,{children:[(0,c.jsx)(d,{children:(0,c.jsx)(i,{to:`/standings/$slug`,params:{slug:n.slug},children:n.name})}),(0,c.jsx)(d,{children:(0,c.jsx)(t,{children:n.set})}),(0,c.jsx)(d,{$num:!0,children:n.standing?.rank==null?`—`:`${n.standing.rank} of ${n.standing.fieldSize}`}),(0,c.jsx)(d,{$num:!0,children:n.standing==null?`—`:`${n.standing.casesPassed}/${n.standing.casesTotal}`}),(0,c.jsx)(d,{$num:!0,children:n.standing==null||n.standing.score==null||!x(n.standing)?`—`:(0,c.jsx)(s,{value:n.standing.score})}),(0,c.jsx)(d,{$num:!0,children:n.standing==null?`—`:h(n.standing.points)})]},n.problemId))})]})}function w({rows:e}){return(0,c.jsxs)(l,{children:[(0,c.jsx)(`thead`,{children:(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(u,{children:`Rank`}),(0,c.jsx)(u,{children:`Team`}),(0,c.jsx)(u,{$num:!0,children:`Score`}),(0,c.jsx)(u,{$num:!0,children:`Test points`}),(0,c.jsx)(u,{$num:!0,children:`Ranking points`}),(0,c.jsx)(u,{$num:!0,children:`Total`})]})}),(0,c.jsx)(`tbody`,{children:e.map(e=>(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(d,{children:e.rank??`—`}),(0,c.jsx)(f,{children:(0,c.jsx)(y,{teamId:e.teamId,teamName:e.teamName})}),(0,c.jsx)(d,{$num:!0,children:e.score==null?`—`:(0,c.jsx)(s,{value:e.score})}),(0,c.jsx)(d,{$num:!0,children:h(e.passPoints)}),(0,c.jsx)(d,{$num:!0,children:h(e.rankPoints)}),(0,c.jsx)(d,{$num:!0,children:h(e.points)})]},e.teamId))})]})}function T({rows:e}){return(0,c.jsxs)(l,{children:[(0,c.jsx)(`thead`,{children:(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(u,{children:`Rank`}),(0,c.jsx)(u,{children:`Team`}),(0,c.jsx)(u,{$num:!0,children:`Passed`}),(0,c.jsx)(u,{$num:!0,children:`Test points`}),(0,c.jsx)(u,{$num:!0,children:`Ranking points`}),(0,c.jsx)(u,{$num:!0,children:`Total`})]})}),(0,c.jsx)(`tbody`,{children:e.map(e=>(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(d,{children:e.rank??`—`}),(0,c.jsx)(f,{children:(0,c.jsx)(y,{teamId:e.teamId,teamName:e.teamName})}),(0,c.jsxs)(d,{$num:!0,children:[e.casesPassed,`/`,e.casesTotal]}),(0,c.jsx)(d,{$num:!0,children:h(e.passPoints)}),(0,c.jsx)(d,{$num:!0,children:h(e.rankPoints)}),(0,c.jsx)(d,{$num:!0,children:h(e.points)})]},e.teamId))})]})}function E({rows:e}){return(0,c.jsxs)(l,{children:[(0,c.jsx)(`thead`,{children:(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(u,{children:`Team`}),(0,c.jsx)(u,{$num:!0,children:`Passed`})]})}),(0,c.jsx)(`tbody`,{children:e.map(e=>(0,c.jsxs)(`tr`,{children:[(0,c.jsx)(f,{children:(0,c.jsx)(y,{teamId:e.teamId,teamName:e.teamName})}),(0,c.jsxs)(d,{$num:!0,children:[e.casesPassed,`/`,e.casesTotal]})]},e.teamId))})]})}function D({problemId:e}){let{data:n,isLoading:r}=o(e);if(r)return(0,c.jsx)(`p`,{children:`Loading…`});if(!n)return null;let a=n.rows,s=a.filter(e=>x(e)&&e.uberStrictPassed).sort((e,t)=>(e.score??1/0)-(t.score??1/0)),l=a.filter(e=>x(e)&&!e.uberStrictPassed).sort((e,t)=>(e.rank??1/0)-(t.rank??1/0)),u=a.filter(e=>!x(e)&&e.rank!=null).sort((e,t)=>e.rank-t.rank||t.casesPassed-e.casesPassed),d=a.filter(e=>!x(e)&&e.rank==null).sort((e,t)=>t.casesPassed-e.casesPassed);return(0,c.jsxs)(c.Fragment,{children:[(0,c.jsx)(_,{updatedAt:n.updatedAt,frozen:n.frozen}),a.length===0&&(0,c.jsx)(`p`,{children:(0,c.jsx)(t,{children:`No submissions have been judged for this problem yet.`})}),s.length>0&&(0,c.jsxs)(p,{children:[(0,c.jsx)(`h2`,{children:`Solved`}),(0,c.jsx)(m,{children:l.length>0?`Teams that passed every test case and the uber-strict check`:`Teams that passed every test case`}),(0,c.jsx)(w,{rows:s})]}),l.length>0&&(0,c.jsxs)(p,{children:[(0,c.jsx)(`h2`,{children:`Failed the uber-strict check`}),(0,c.jsxs)(m,{children:[`Passed every public and private case but failed the`,` `,(0,c.jsx)(i,{to:`/grading`,hash:`uber-strict`,children:`uber-strict`}),` `,`check, so ranked below every team that passed it.`]}),(0,c.jsx)(T,{rows:l})]}),u.length>0&&(0,c.jsxs)(p,{children:[(0,c.jsx)(`h2`,{children:`Partial passes`}),(0,c.jsx)(m,{children:`Teams that passed some test cases, including a private one`}),(0,c.jsx)(T,{rows:u})]}),d.length>0&&(0,c.jsxs)(p,{children:[(0,c.jsx)(`h2`,{children:`Not ranked`}),(0,c.jsx)(E,{rows:d})]})]})}export{C as i,b as n,D as r,v as t};