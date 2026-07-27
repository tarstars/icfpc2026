import{at as e,c as t,p as n,st as r,v as i,w as a,y as o}from"./ui-wC2GCM-8.js";import{L as s,m as c}from"./index-RPCgG-2I.js";var l=r(e()),u=a(),d=`https://www.timeanddate.com/worldclock/fixedtime.html?msg=ICFPC+2026&iso=20260724T12&p1=1440`,f=`https://www.timeanddate.com/worldclock/fixedtime.html?msg=ICFPC+2026&iso=20260725T12&p1=1440`,p=`https://www.timeanddate.com/worldclock/fixedtime.html?msg=ICFPC+2026&iso=20260727T12&p1=1440`,m=`https://discord.gg/KXej6gAWwP`,h=[{date:`25 July`,body:(0,u.jsxs)(u.Fragment,{children:[`To be eligible for prizes,`,` `,(0,u.jsx)(o,{to:`/dashboard`,hash:`source-code`,children:`link your source code`}),` `,`in the dashboard. You can provide a link to a private repository and make it public after the contest.`]})},{date:`25 July`,body:(0,u.jsx)(u.Fragment,{children:`Editor improvement: you can hover or click on the registers below a room to see which little man they belong to.`})},{date:`25 July`,body:(0,u.jsxs)(u.Fragment,{children:[`Standings improvements: the `,(0,u.jsx)(o,{to:`/standings`,children:`standings`}),` page shows how many problems a team has completed, and you can click a team to see their performance on every problem.`]})},{date:`25 July`,body:(0,u.jsx)(u.Fragment,{children:`The triple-dot menu in the editor now lets you upload programs (from a file or the clipboard) and clear the grid.`})},{date:`25 July`,body:(0,u.jsxs)(u.Fragment,{children:[`We’ve released a new instruction named split (`,(0,u.jsx)(n,{children:`Y`}),`).`,` `,(0,u.jsx)(o,{to:`/split`,children:`View the documentation here`}),`.`]})},{date:`25 July`,body:(0,u.jsxs)(u.Fragment,{children:[`We’ve released 4 new problems. View them under “Semester 4” in the`,` `,(0,u.jsx)(o,{to:`/problem-sets`,children:`problem sets`}),` tab.`]})},{date:`25 July`,body:(0,u.jsx)(u.Fragment,{children:`The lightning round has ended!`})},{date:`24 July`,body:(0,u.jsx)(u.Fragment,{children:`Interpreter fix: a pipe ending with an arrowhead *between* two rooms would sometimes fail to parse. This bug has been fixed. Affected submissions will be re-judged.`})},{date:`24 July`,body:(0,u.jsx)(u.Fragment,{children:`The editor no longer shows an error for a run that passes and then hits a wall on the same tick.`})},{date:`24 July`,body:(0,u.jsxs)(u.Fragment,{children:[`Sudoku Auditor is now`,` `,(0,u.jsx)(o,{to:`/grading`,hash:`uber-strict`,children:`uber-strict`}),`: a full pass is also judged against a hidden corpus to prevent hardcoding private test case outputs.`]})},{date:`24 July`,body:(0,u.jsxs)(u.Fragment,{children:[`We added per-problem rate limiting. Rapid submissions see a `,(0,u.jsx)(n,{children:`429`}),` `,`error; retry after a delay.`]})},{date:`24 July`,body:(0,u.jsx)(u.Fragment,{children:`Interpreter fix: rooms and displays with holes in their borders no longer load.`})},{date:`24 July`,body:(0,u.jsxs)(u.Fragment,{children:[`Interpreter fix: `,(0,u.jsx)(n,{children:`U`}),` now correctly turns little men away from the wall a pipe is attached to in all cases. See the`,` `,(0,u.jsx)(o,{to:`/language-reference`,children:`reference`}),`.`]})},{date:`24 July`,body:(0,u.jsxs)(u.Fragment,{children:[(0,u.jsxs)(n,{children:[`GET /api/v1/submissions/`,`{id}`]}),` now returns your score. See the `,(0,u.jsx)(o,{to:`/api-help`,children:`API reference`}),`.`]})},{date:`24 July`,body:(0,u.jsx)(u.Fragment,{children:`The contest has begun!`})}],g=Date.parse(`2026-07-24T12:00:00Z`),_=3600*1e3;function v(e,t){let n=e?.start?Date.parse(e.start):g,r=(e,t)=>e?Date.parse(e):n+t*_,i=(t-n)/_;return{startMs:n,lightningEndMs:r(e?.lightningEnd,24),endMs:r(e?.end,72),freezeStartMs:r(e?.freezeStart,22),freezeEndMs:r(e?.freezeEnd,26),finalFreezeMs:r(e?.finalFreeze,70),started:(e?.started??!1)||i>=0,ended:(e?.submissionsClosed??!1)||i>=72,standingsFrozen:e?.standingsFrozen??(i>=22&&i<26||i>=70)}}function y(){let[e,t]=(0,l.useState)(()=>Date.now());return(0,l.useEffect)(()=>{let e=setInterval(()=>t(Date.now()),1e3);return()=>clearInterval(e)},[]),e}function b(e,t){let n=Math.max(0,Math.floor((e-t)/1e3)),r=Math.floor(n/86400),i=Math.floor(n%86400/3600),a=Math.floor(n%3600/60),o=n%60,s=e=>String(e).padStart(2,`0`);return r>0?`${r}d ${s(i)}h ${s(a)}m ${s(o)}s`:`${s(i)}h ${s(a)}m ${s(o)}s`}function x({clock:e,nowMs:t}){if(e.standingsFrozen)return t<e.freezeEndMs?(0,u.jsxs)(`li`,{children:[(0,u.jsxs)(`span`,{children:[(0,u.jsx)(o,{to:`/standings`,children:`Standings`}),` unfreeze in`]}),(0,u.jsx)(A,{children:b(e.freezeEndMs,t)})]}):(0,u.jsxs)(`li`,{children:[(0,u.jsxs)(`span`,{children:[`The `,(0,u.jsx)(o,{to:`/standings`,children:`standings`}),` are frozen.`]}),(0,u.jsx)(`span`,{})]});let n=t<e.freezeStartMs?e.freezeStartMs:e.finalFreezeMs;return t>=n?null:(0,u.jsxs)(`li`,{children:[(0,u.jsxs)(`span`,{children:[(0,u.jsx)(o,{to:`/standings`,children:`Standings`}),` freeze in`]}),(0,u.jsx)(A,{children:b(n,t)})]})}function S({clock:e,nowMs:t}){if(!e.started)return(0,u.jsxs)(D,{children:[(0,u.jsxs)(O,{children:[`The `,(0,u.jsx)(T,{href:d,children:`contest starts`}),` in`,` `,(0,u.jsx)(A,{children:b(e.startMs,t)}),`.`]}),(0,u.jsx)(C,{})]});if(e.ended)return(0,u.jsxs)(D,{children:[(0,u.jsx)(O,{children:`The contest has ended.`}),e.standingsFrozen?(0,u.jsxs)(`p`,{children:[`The `,(0,u.jsx)(o,{to:`/standings`,children:`standings`}),` are frozen as of two hours before the end of the contest. Final results will be revealed at the awards ceremony at`,` `,(0,u.jsx)(T,{href:`https://icfp26.sigplan.org/`,children:`ICFP 2026`}),`.`]}):(0,u.jsxs)(`p`,{children:[`Final `,(0,u.jsx)(o,{to:`/standings`,children:`standings`}),` are up.`]}),(0,u.jsx)(C,{})]});let n=t<e.lightningEndMs;return(0,u.jsxs)(D,{children:[(0,u.jsx)(O,{$live:!0,children:`The contest is live.`}),(0,u.jsxs)(k,{children:[n&&(0,u.jsxs)(`li`,{children:[(0,u.jsxs)(`span`,{children:[(0,u.jsx)(T,{href:f,children:`Lightning round ends`}),` `,`in`]}),(0,u.jsx)(A,{children:b(e.lightningEndMs,t)})]}),(0,u.jsxs)(`li`,{children:[(0,u.jsxs)(`span`,{children:[(0,u.jsx)(T,{href:p,children:`Contest ends`}),` in`]}),(0,u.jsx)(A,{children:b(e.endMs,t)})]}),(0,u.jsx)(x,{clock:e,nowMs:t})]}),n&&(0,u.jsx)(`p`,{children:`We plan to release more problems and a language update after the lightning round.`}),(0,u.jsx)(C,{})]})}function C(){return(0,u.jsxs)(`p`,{children:[(0,u.jsx)(`b`,{children:(0,u.jsx)(T,{href:m,children:`Join the Discord`})}),` `,`to ask questions or report problems.`]})}function w(){let{data:e}=s(),{data:t}=c(),n=y(),r=v(t,n);return(0,u.jsxs)(E,{children:[(0,u.jsx)(`h1`,{children:`ICFP Programming Contest 2026`}),(0,u.jsx)(S,{clock:r,nowMs:n}),(0,u.jsx)(`h2`,{children:`Participating`}),(0,u.jsxs)(`ol`,{children:[!e&&(0,u.jsxs)(`li`,{children:[(0,u.jsx)(`a`,{href:`/signup`,children:`Create an account`}),`. Only one team member needs to register (teammates share that sign-in).`]}),(0,u.jsxs)(`li`,{children:[`Read the `,(0,u.jsx)(o,{to:`/textbook`,children:`Textbook`}),`.`]}),(0,u.jsxs)(`li`,{children:[`Work through the `,(0,u.jsx)(o,{to:`/problem-sets`,children:`Problem Sets`}),` — each problem’s page explains how to submit.`]}),r.started&&n<r.lightningEndMs&&(0,u.jsx)(`li`,{children:`Check back after the lightning round for more problems and a language update.`}),r.started&&!r.ended&&(0,u.jsxs)(`li`,{children:[`To be eligible for prizes, link your team’s source code on the`,` `,(0,u.jsx)(o,{to:`/dashboard`,children:`dashboard`}),` before the contest ends.`]})]}),(0,u.jsx)(`h2`,{children:`Announcements`}),(0,u.jsx)(j,{children:h.map((e,t)=>(0,u.jsxs)(`li`,{children:[(0,u.jsx)(M,{children:e.date}),(0,u.jsx)(`div`,{children:e.body})]},t))}),(0,u.jsx)(`h2`,{children:`Additional Links`}),(0,u.jsxs)(`ul`,{children:[(0,u.jsxs)(`li`,{children:[`See`,` `,(0,u.jsx)(o,{to:`/grading`,hash:`submitting`,children:`Submitting your work`}),` `,`for how to submit a solution.`]}),(0,u.jsxs)(`li`,{children:[`See `,(0,u.jsx)(o,{to:`/grading`,children:`Grading`}),` for how submissions are scored and teams are ranked.`]}),(0,u.jsxs)(`li`,{children:[`See `,(0,u.jsx)(o,{to:`/standings`,children:`Standings`}),` for the standings.`]}),(0,u.jsxs)(`li`,{children:[`See the `,(0,u.jsx)(o,{to:`/language-reference`,children:`Detailed Reference`}),` for language minutiae and `,(0,u.jsx)(o,{to:`/editor-help`,children:`Editor Help`}),` for the editor.`]})]}),(0,u.jsx)(`h2`,{children:`About`}),(0,u.jsxs)(`p`,{children:[`This is the 29th instance of the annual ICFP Programming Contest, held online. It runs from`,` `,(0,u.jsx)(T,{href:d,children:`Friday July 24th at 12:00 UTC`}),` `,`to `,(0,u.jsx)(T,{href:p,children:`Monday July 27th at 12:00 UTC`}),`, with a 24-hour lightning round ending`,` `,(0,u.jsx)(T,{href:f,children:`Saturday July 25th at 12:00 UTC`}),`. Winners will be announced at`,` `,(0,u.jsx)(T,{href:`https://icfp26.sigplan.org/`,children:`ICFP 2026`}),` in Indianapolis, Indiana.`]}),(0,u.jsxs)(N,{children:[(0,u.jsx)(`dt`,{children:`Discord`}),(0,u.jsxs)(`dd`,{children:[(0,u.jsx)(T,{href:m,children:`Join the Discord`}),` to ask questions or report problems.`]}),(0,u.jsx)(`dt`,{children:`Social Media`}),(0,u.jsxs)(`dd`,{children:[(0,u.jsx)(T,{href:`https://bsky.app/profile/icfpcontest.bsky.social`,children:`Bluesky`}),` `,`· `,(0,u.jsx)(T,{href:`https://x.com/icfpcontest2026`,children:`Twitter`})]}),(0,u.jsx)(`dt`,{children:`Teaching Assistants`}),(0,u.jsxs)(`dd`,{children:[(0,u.jsx)(T,{href:`https://eieio.games`,children:`Nolen Royalty`}),`,`,` `,(0,u.jsx)(T,{href:`https://github.com/eliothedeman`,children:`Eliot Hedeman`}),`, `,(0,u.jsx)(T,{href:`https://github.com/hcnelson99`,children:`Henry Nelson`}),`,`,` `,(0,u.jsx)(T,{href:`https://www.frankchiarulli.com/`,children:`Frank Chiarulli Jr`})]})]}),(0,u.jsx)(P,{children:`Last updated: 25 July 2026.`})]})}var T=i.a.attrs({target:`_blank`,rel:`noopener noreferrer`})``,E=i.main`
  max-width: 940px;
  margin: 0 auto;
  padding: 8px 15px 64px;
  font-size: var(--font-size-regular);
  line-height: 1.5;

  h1 {
    font-size: var(--font-size-xlarge);
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 0.5em;
  }

  h2 {
    font-size: var(--font-size-large);
    font-weight: 700;
    line-height: 1.2;
    margin-top: 1rem;
    margin-bottom: 0.25em;
  }

  p {
    margin-bottom: 0.7em;
  }

  ul,
  ol {
    margin-bottom: 0.7em;
    padding-left: 1.25em;
  }

  a {
    color: #337ab7;
    text-decoration: none;
  }
  a:hover,
  a:focus {
    color: #23527c;
    text-decoration: underline;
  }
`,D=i.section`
  border: 1px solid var(--color-stone-400);
  background: var(--color-stone-50);
  padding: 12px 16px;
  margin-bottom: 20px;

  p {
    margin-bottom: 0.4em;
  }
  p:last-child {
    margin-bottom: 0;
  }
`,O=i.p`
  font-weight: 700;
  ${e=>e.$live&&`color: var(--color-green-700);`}
`,k=i.ul`
  display: grid;
  grid-template-columns: max-content max-content;
  column-gap: 10px;
  list-style: none;
  padding-left: 0 !important;
  margin-bottom: 0.4em;

  li {
    display: contents;
  }
`,A=i.span`
  font-family: ${t};
  font-weight: 700;
  font-variant-numeric: tabular-nums;
`,j=i.ul`
  list-style: none;
  padding-left: 0 !important;

  li {
    display: flex;
    gap: 12px;
    margin-bottom: 0.4em;
  }
`,M=i.span`
  flex: none;
  width: 4.5em;
  font-weight: 700;
  color: var(--color-stone-600);
`,N=i.dl`
  margin: 0 0 20px;

  dt {
    font-weight: 700;
  }
  dd {
    margin-bottom: 0.4em;
  }

  @media (min-width: 768px) {
    display: grid;
    grid-template-columns: max-content 1fr;
    column-gap: 24px;
    row-gap: 6px;

    dt {
      text-align: right;
    }
    dd {
      margin-bottom: 0;
    }
  }
`,P=i.p`
  color: var(--color-stone-500);
  font-size: var(--font-size-small);
  border-top: 1px solid var(--color-stone-500);
  padding-top: 12px;
`;export{w as component};