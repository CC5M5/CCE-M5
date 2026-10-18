import{c as l,j as e}from"./createLucideIcon.wXoZYO8l.js";import{r as p}from"./index.CVf8TyFT.js";/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const x=l("ArrowLeft",[["path",{d:"m12 19-7-7 7-7",key:"1l729n"}],["path",{d:"M19 12H5",key:"x3x0zl"}]]);/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const y=l("EyeOff",[["path",{d:"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49",key:"ct8e1f"}],["path",{d:"M14.084 14.158a3 3 0 0 1-4.242-4.242",key:"151rxh"}],["path",{d:"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143",key:"13bj9a"}],["path",{d:"m2 2 20 20",key:"1ooewy"}]]);/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const b=l("Eye",[["path",{d:"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0",key:"1nclc0"}],["circle",{cx:"12",cy:"12",r:"3",key:"1v7zrd"}]]);/**
 * @license lucide-react v0.441.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const f=l("Play",[["polygon",{points:"6 3 20 12 6 21 6 3",key:"1oa8hb"}]]);function g(r){if(!r)return"";const n=document.createElement("div");n.innerHTML=r;const m=["BR","P","DIV","SPAN","B","STRONG","I","EM","U","SUP","SUB","H1","H2","H3","H4","H5","H6","UL","OL","LI"],c=["class","style"],o=s=>{if(s.nodeType===Node.ELEMENT_NODE){const t=s.tagName.toUpperCase();if(!m.includes(t)){s.replaceWith(...s.childNodes);return}for(const a of Array.from(s.attributes)){const i=a.name.toLowerCase();if(!c.includes(i)){s.removeAttribute(a.name);continue}if(i==="style"){const d=a.value.replace(/expression\s*\(/gi,"").replace(/javascript\s*:/gi,"").replace(/data\s*:/gi,"").replace(/behavior\s*:/gi,"");s.setAttribute(a.name,d)}}if(/^on\w+/i.test(t)){s.replaceWith(...s.childNodes);return}}for(const t of Array.from(s.childNodes))o(t)};for(const s of Array.from(n.childNodes))o(s);return n.innerHTML}function w({htmlVisual:r,titulo:n,slug:m,tono:c,enlaceAudio:o,compact:s=!1}){const[t,a]=p.useState(!0),i=p.useMemo(()=>typeof document>"u"?(r||"").replace(/<script\b[^\<]*(?:(?!<\/script>)<[^\<]*)*<\/script>/gi,"").replace(/javascript:/gi,"").replace(/on\w+\s*=/gi,""):g(r||""),[r]),d=()=>{a(h=>!h)},u=t?"cancion-con-acordes":"cancion-con-acordes sin-acordes";return e.jsxs("div",{className:`bg-white rounded-xl border border-slate-200 ${s?"p-4":"p-6 md:p-8"} font-mono leading-relaxed`,children:[!s&&e.jsxs("div",{className:"flex flex-wrap items-center gap-3 mb-4 no-print",children:[e.jsx("button",{type:"button",onClick:d,className:"btn-secondary text-sm","aria-pressed":t,children:t?e.jsxs(e.Fragment,{children:[e.jsx(y,{className:"w-4 h-4"})," Sin acordes"]}):e.jsxs(e.Fragment,{children:[e.jsx(b,{className:"w-4 h-4"})," Con acordes"]})}),c&&e.jsxs("span",{className:"inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium",children:["Tono: ",c]}),o?e.jsxs("a",{href:o,target:"_blank",rel:"noopener noreferrer",className:"btn-secondary text-sm",children:[e.jsx(f,{className:"w-4 h-4"})," Escuchar"]}):e.jsxs("button",{type:"button",disabled:!0,className:"btn-secondary text-sm opacity-50 cursor-not-allowed",title:"Audio no disponible",children:[e.jsx(f,{className:"w-4 h-4"})," Audio no disponible"]}),e.jsxs("a",{href:"/CCE-M5/cancionero/",className:"btn-secondary text-sm",children:[e.jsx(x,{className:"w-4 h-4"})," Volver al cancionero"]})]}),e.jsx("div",{className:u,dangerouslySetInnerHTML:{__html:i},"aria-label":`Letra ${t?"con acordes":"sin acordes"} de ${n}`})]})}export{w as default};
