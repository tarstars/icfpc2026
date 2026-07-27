import{v as e,w as t}from"./ui-wC2GCM-8.js";var n=t(),r=[{limit:0x38d7ea4c68000,suffix:`Q`},{limit:0xe8d4a51000,suffix:`T`},{limit:1e9,suffix:`B`},{limit:1e6,suffix:`M`},{limit:1e3,suffix:`K`}];function i(e){if(!Number.isFinite(e))return`—`;let t=Math.abs(e);for(let n of r)if(t>=n.limit){let t=e/n.limit,r=Math.abs(t)>=100?0:Math.abs(t)>=10?1:2;return t.toFixed(r)+n.suffix}return String(Math.round(e))}function a(e){return Math.round(e).toLocaleString()}var o=e.abbr`
  border-bottom: 1px dotted var(--color-stone-500);
  text-decoration: none;
  cursor: help;
`;function s({value:e}){return(0,n.jsx)(o,{title:`${a(e)} (lower is better)`,children:i(e)})}export{s as t};