import{at as e,c as t,i as n,l as r,r as i,st as a,v as o,w as s}from"./ui-wC2GCM-8.js";import{R as c,c as l,w as u}from"./index-RPCgG-2I.js";import{C as d,E as f,S as p,T as m,_ as h,b as g,g as _,h as v,m as y,t as ee,v as te,w as b,x,y as S}from"./embed-DpaTuuw2.js";import{t as C}from"./score-DbyPN9BI.js";import{n as w}from"./problem-program-memory-DBF3b7K5.js";var T=a(e(),1),E=s(),D,O=`HoverCard`,[k,ne]=b(O,[x]),A=x(),[j,M]=k(O),N=e=>{let{__scopeHoverCard:t,children:n,open:r,defaultOpen:i,onOpenChange:a,openDelay:o=700,closeDelay:s=300}=e,c=A(t),l=T.useRef(0),u=T.useRef(0),d=T.useRef(!1),f=T.useRef(!1),[p,m]=y({prop:r,defaultProp:i??!1,onChange:a,caller:O}),h=T.useCallback(()=>{clearTimeout(u.current),l.current=window.setTimeout(()=>m(!0),o)},[o,m]),_=T.useCallback(()=>{clearTimeout(l.current),!d.current&&!f.current&&(u.current=window.setTimeout(()=>m(!1),s))},[s,m]),v=T.useCallback(()=>m(!1),[m]);return T.useEffect(()=>()=>{clearTimeout(l.current),clearTimeout(u.current)},[]),(0,E.jsx)(j,{scope:t,open:p,onOpenChange:m,onOpen:h,onClose:_,onDismiss:v,hasSelectionRef:d,isPointerDownOnContentRef:f,children:(0,E.jsx)(g,{...c,children:n})})};N.displayName=O;var P=`HoverCardTrigger`,F=T.forwardRef((e,t)=>{let{__scopeHoverCard:n,...r}=e,i=M(P,n),a=A(n);return(0,E.jsx)(h,{asChild:!0,...a,children:(0,E.jsx)(d.a,{"data-state":i.open?`open`:`closed`,...r,ref:t,onPointerEnter:f(e.onPointerEnter,G(i.onOpen)),onPointerLeave:f(e.onPointerLeave,G(i.onClose)),onFocus:f(e.onFocus,i.onOpen),onBlur:f(e.onBlur,i.onClose),onTouchStart:f(e.onTouchStart,e=>e.preventDefault())})})});F.displayName=P;var I=`HoverCardPortal`,[L,R]=k(I,{forceMount:void 0}),z=e=>{let{__scopeHoverCard:t,forceMount:n,children:r,container:i}=e,a=M(I,t);return(0,E.jsx)(L,{scope:t,forceMount:n,children:(0,E.jsx)(v,{present:n||a.open,children:(0,E.jsx)(_,{asChild:!0,container:i,children:r})})})};z.displayName=I;var B=`HoverCardContent`,V=T.forwardRef((e,t)=>{let n=R(B,e.__scopeHoverCard),{forceMount:r=n.forceMount,...i}=e,a=M(B,e.__scopeHoverCard);return(0,E.jsx)(v,{present:r||a.open,children:(0,E.jsx)(H,{"data-state":a.open?`open`:`closed`,...i,onPointerEnter:f(e.onPointerEnter,G(a.onOpen)),onPointerLeave:f(e.onPointerLeave,G(a.onClose)),ref:t})})});V.displayName=B;var H=T.forwardRef((e,t)=>{let{__scopeHoverCard:n,onEscapeKeyDown:r,onPointerDownOutside:i,onFocusOutside:a,onInteractOutside:o,...s}=e,c=M(B,n),l=A(n),u=T.useRef(null),d=m(t,u),[h,g]=T.useState(!1);return T.useEffect(()=>{if(h){let e=document.body;return D=e.style.userSelect||e.style.webkitUserSelect,e.style.userSelect=`none`,e.style.webkitUserSelect=`none`,()=>{e.style.userSelect=D,e.style.webkitUserSelect=D}}},[h]),T.useEffect(()=>{if(u.current){let e=()=>{g(!1),c.isPointerDownOnContentRef.current=!1,setTimeout(()=>{document.getSelection()?.toString()!==``&&(c.hasSelectionRef.current=!0)})};return document.addEventListener(`pointerup`,e),()=>{document.removeEventListener(`pointerup`,e),c.hasSelectionRef.current=!1,c.isPointerDownOnContentRef.current=!1}}},[c.isPointerDownOnContentRef,c.hasSelectionRef]),T.useEffect(()=>{u.current&&K(u.current).forEach(e=>e.setAttribute(`tabindex`,`-1`))}),(0,E.jsx)(p,{asChild:!0,disableOutsidePointerEvents:!1,onInteractOutside:o,onEscapeKeyDown:r,onPointerDownOutside:i,onFocusOutside:f(a,e=>{e.preventDefault()}),onDismiss:c.onDismiss,children:(0,E.jsx)(S,{...l,...s,onPointerDown:f(s.onPointerDown,e=>{e.currentTarget.contains(e.target)&&g(!0),c.hasSelectionRef.current=!1,c.isPointerDownOnContentRef.current=!0}),ref:d,style:{...s.style,userSelect:h?`text`:void 0,WebkitUserSelect:h?`text`:void 0,"--radix-hover-card-content-transform-origin":`var(--radix-popper-transform-origin)`,"--radix-hover-card-content-available-width":`var(--radix-popper-available-width)`,"--radix-hover-card-content-available-height":`var(--radix-popper-available-height)`,"--radix-hover-card-trigger-width":`var(--radix-popper-anchor-width)`,"--radix-hover-card-trigger-height":`var(--radix-popper-anchor-height)`}})})}),U=`HoverCardArrow`,W=T.forwardRef((e,t)=>{let{__scopeHoverCard:n,...r}=e,i=A(n);return(0,E.jsx)(te,{...i,...r,ref:t})});W.displayName=U;function G(e){return t=>t.pointerType===`touch`?void 0:e()}function K(e){let t=[],n=document.createTreeWalker(e,NodeFilter.SHOW_ELEMENT,{acceptNode:e=>e.tabIndex>=0?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_SKIP});for(;n.nextNode();)t.push(n.currentNode);return t}var q=N,J=F,Y=z,X=V,re={pending:`var(--color-stone-500)`,running:`var(--color-stone-500)`,done:`var(--color-green-700)`,failed:`var(--color-red-700)`},Z=e=>e.casesTotal!=null&&e.casesTotal>0&&e.casesPassed===e.casesTotal;function ie(e){if(e.status===`done`){if(e.loadError)return`failed to load`;if(e.casesTotal==null)return`done`;if(Z(e)){if(e.uberStrictPassed===!1)return`${e.casesPassed}/${e.casesTotal} passed · failed uber-strict`;let t=`success — ${e.casesPassed}/${e.casesTotal} passed`;return e.uberStrictPassed===!0?`${t} · passed uber-strict`:t}return`done — ${e.casesPassed}/${e.casesTotal} passed`}return e.status}function ae(e){return e.status===`done`&&(e.loadError||e.casesTotal&&e.casesPassed===0)?`var(--color-red-700)`:e.status===`done`&&Z(e)&&e.uberStrictPassed===!1?`var(--color-amber-700)`:re[e.status]}function oe(e){let t=new Date(e),n=t.toLocaleTimeString(void 0,{hour:`numeric`,minute:`2-digit`}),r=new Date;return t.getFullYear()===r.getFullYear()&&t.getMonth()===r.getMonth()&&t.getDate()===r.getDate()?n:`${t.toLocaleDateString(void 0,{month:`short`,day:`numeric`})}, ${n}`}var se=o.div`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
`,ce=o.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: var(--font-size-small);
  color: var(--color-stone-500);
`,Q=o.a`
  font-size: var(--font-size-xsmall);
  color: var(--color-stone-500);

  &:hover,
  &:focus-visible {
    color: var(--color-stone-900);
  }
`,le=o(Q).attrs({as:`button`,type:`button`})`
  font-family: inherit;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;

  &:disabled {
    cursor: default;
    text-decoration: none;
  }
`;function $({s:e}){let t=c(),[n,r]=(0,T.useState)(`idle`),i=e.problemSlug;return i?(0,E.jsx)(le,{onClick:async()=>{r(`busy`);try{let n=await l.dashboard.submissions[`:id`].download.$get({param:{id:e.id}});if(!n.ok)throw Error(`program fetch failed (${n.status})`);let r=await n.text();w(i,ee(`${e.problemName??i} downloaded`,r)),t({to:`/problems/$slug/editor`,params:{slug:i}})}catch{r(`failed`)}},disabled:n===`busy`,children:n===`busy`?`opening…`:n===`failed`?`failed — retry?`:`open in editor`}):null}var ue=o.button`
  font-family: ${t};
  font-size: var(--font-size-xsmall);
  font-style: italic;
  width: 1.5em;
  height: 1.5em;
  padding: 0;
  border: 1px solid var(--color-stone-400);
  border-radius: 50%;
  background: none;
  color: var(--color-stone-500);
  line-height: 1;
  cursor: help;

  &:hover,
  &:focus-visible {
    border-color: var(--color-stone-600);
    color: var(--color-stone-900);
  }
`,de=o.div`
  z-index: 2100;
  /* A uuid is 36 monospace characters and must not wrap — reading it off in one
     line is the reason to open this at all. */
  width: max-content;
  max-width: min(90vw, 420px);
  background: var(--color-paper);
  border: 1px solid var(--color-stone-400);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: var(--font-size-small);
  user-select: text;

  dl {
    margin: 0;
  }
  dt {
    font-size: var(--font-size-xsmall);
    color: var(--color-stone-500);
  }
  dd {
    margin: 0 0 8px;
    font-family: ${t};
    white-space: nowrap;
  }
  dd:last-of-type {
    margin-bottom: 0;
  }
`;function fe({s:e}){return(0,E.jsxs)(q,{openDelay:100,closeDelay:200,children:[(0,E.jsx)(J,{asChild:!0,children:(0,E.jsx)(ue,{type:`button`,"aria-label":`Submission id and exact time`,children:`i`})}),(0,E.jsx)(Y,{children:(0,E.jsx)(X,{side:`bottom`,align:`end`,sideOffset:6,asChild:!0,children:(0,E.jsx)(de,{children:(0,E.jsxs)(`dl`,{children:[(0,E.jsx)(`dt`,{children:`Submission id`}),(0,E.jsx)(`dd`,{children:e.id}),(0,E.jsx)(`dt`,{children:`Submitted`}),(0,E.jsx)(`dd`,{children:new Date(e.createdAt).toLocaleString()})]})})})})]})}function pe({problemId:e}){let{data:t,isLoading:a}=u(e?{problemId:e}:void 0);return a?(0,E.jsx)(r,{children:`Loading…`}):t?.length?(0,E.jsx)(`div`,{children:t.map(e=>(0,E.jsxs)(i,{style:{padding:`12px 14px`},children:[(0,E.jsxs)(se,{children:[(0,E.jsx)(`strong`,{children:e.problemName??e.problemId}),(0,E.jsxs)(ce,{children:[(0,E.jsx)($,{s:e}),(0,E.jsx)(Q,{href:`/api/v1/dashboard/submissions/${e.id}/download`,children:`download`}),oe(e.createdAt),(0,E.jsx)(fe,{s:e})]})]}),(0,E.jsxs)(`div`,{children:[(0,E.jsx)(`span`,{style:{color:ae(e),fontWeight:700},children:ie(e)}),e.score!=null&&(0,E.jsxs)(r,{children:[` `,`· score `,(0,E.jsx)(C,{value:e.score})]})]}),e.status===`failed`&&e.error&&(0,E.jsx)(n,{style:{marginTop:8,marginBottom:0},children:e.error}),e.status===`done`&&e.loadError&&(0,E.jsx)(n,{style:{marginTop:8,marginBottom:0},children:e.loadError}),e.status===`done`&&!e.loadError&&!Z(e)&&e.output&&(0,E.jsx)(n,{style:{marginTop:8,marginBottom:0},children:e.output})]},e.id))}):(0,E.jsx)(r,{children:`No submissions yet.`})}export{pe as t};