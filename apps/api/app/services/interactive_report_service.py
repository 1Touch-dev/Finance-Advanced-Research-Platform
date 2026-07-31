"""
Interactive report (G-10).

*"We need the reports to be interactive; reports that find and search."* — and
the two links sent on 31 July were both bubble charts where clicking a person
reveals the companies they touched. That is the format, stated as precisely as
it is going to be stated.

A PDF cannot do it. This produces a second artefact from the same markdown the
PDF is built from, so the two never drift: one document, two renderings.

Three decisions worth recording.

**Single file, no CDN.** Everything — styles, script, data, images — is inlined
into one .html. It opens by double-click, works with no network, survives being
emailed, and cannot break because a script host changed. A report about
corporate networks that phones out to three third parties when opened would be
a poor advertisement for the analysis inside it.

**No framework.** The interactions needed are search, filter, sort and a click
on a node. Vanilla JavaScript covers all four in less code than the loader for
a charting library, and it will still run in five years.

**The graph is laid out deterministically.** A force simulation puts the nodes
somewhere different on every open, which means two readers cannot describe the
same picture to each other. Nodes are placed on a circle in a fixed order, so
the layout is a property of the data and the same every time.
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph payload
# ---------------------------------------------------------------------------

def build_graph_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Nodes and links for the clickable view.

    Three node kinds. People and the entities they report at come from Section
    16; managers and the issuers they hold come from 13F. Both are bipartite,
    which is what makes "click a person, see their companies" the natural
    interaction rather than one bolted on.
    """
    graph = data.get("cooccurrence") or {}
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}

    def node(name: str, kind: str, meta: Optional[dict] = None) -> Optional[int]:
        if not name:
            return None
        key = f"{kind}:{name}"
        if key in seen:
            return seen[key]
        seen[key] = len(nodes)
        nodes.append({"id": len(nodes), "name": name, "kind": kind,
                      "meta": meta or {}, "degree": 0})
        return seen[key]

    # People and their outside seats.
    for person in (data.get("board_interlocks") or {}).get("people") or []:
        source = node(person.get("name"), "person", {
            "roles": ", ".join(person.get("roles_at_issuer") or []),
            "url": person.get("profile_url"),
        })
        if source is None:
            continue
        for seat in person.get("other_seats") or []:
            target = node(seat.get("issuer"), "entity", {
                "ticker": seat.get("ticker") or "",
                "roles": ", ".join(seat.get("roles") or []),
                "current": bool(seat.get("current")),
                "url": seat.get("source_url"),
            })
            if target is not None:
                links.append({"source": source, "target": target,
                              "kind": "seat",
                              "label": "current seat" if seat.get("current")
                                       else "former seat"})

    # Managers and the issuers they hold.
    institutional = graph.get("institutional") or {}
    for manager in institutional.get("managers") or []:
        source = node(manager.get("name"), "manager", {
            "issuers": manager.get("count"),
        })
        if source is None:
            continue
        for issuer in manager.get("issuers") or []:
            target = node(issuer, "issuer", {})
            if target is not None:
                links.append({"source": source, "target": target,
                              "kind": "holding", "label": "13F position"})

    # Family vehicles, where any were found.
    for link in (data.get("family_network") or {}).get("surname_links") or []:
        source = node(link.get("vehicle"), "vehicle",
                      {"kind": link.get("kind")})
        for name in link.get("insider_names") or []:
            target = node(name, "person", {})
            if source is not None and target is not None:
                links.append({"source": source, "target": target,
                              "kind": "surname",
                              "label": f"shares surname '{link.get('surname')}'"})

    for link in links:
        nodes[link["source"]]["degree"] += 1
        nodes[link["target"]]["degree"] += 1

    return {"nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------

_CSS = """
:root{--navy:#12283F;--ink:#14202E;--body:#253546;--muted:#64748B;
--accent:#B45309;--rule:#D7DEE6;--rule2:#EBEFF4;--tint:#F6F8FA;--neg:#A32020}
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 -apple-system,BlinkMacSystemFont,"Helvetica Neue",
Helvetica,Arial,sans-serif;color:var(--body);background:#fff}
header{position:sticky;top:0;z-index:20;background:var(--navy);color:#fff;
padding:14px 22px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;
box-shadow:0 1px 6px rgba(0,0,0,.18)}
header h1{font-size:16px;margin:0;font-weight:600;letter-spacing:.2px}
header .meta{font-size:12px;opacity:.75}
#q{flex:1;min-width:220px;padding:8px 12px;border:0;border-radius:5px;
font-size:14px;background:rgba(255,255,255,.12);color:#fff}
#q::placeholder{color:rgba(255,255,255,.6)}
#q:focus{outline:2px solid var(--accent);background:rgba(255,255,255,.2)}
#hits{font-size:12px;opacity:.8;white-space:nowrap}
.layout{display:flex;align-items:flex-start}
nav{position:sticky;top:64px;width:250px;flex:none;max-height:calc(100vh - 64px);
overflow:auto;padding:20px 12px 40px;border-right:1px solid var(--rule2);
font-size:13px}
nav a{display:block;padding:5px 10px;color:var(--body);text-decoration:none;
border-radius:4px;border-left:2px solid transparent}
nav a:hover{background:var(--tint)}
nav a.on{border-left-color:var(--accent);color:var(--navy);font-weight:600}
main{flex:1;min-width:0;padding:28px 40px 80px;max-width:960px}
h2{font-size:22px;color:var(--navy);margin:38px 0 12px;padding-bottom:7px;
border-bottom:2px solid var(--rule)}
h3{font-size:16px;color:var(--ink);margin:24px 0 8px}
h4{font-size:14px;color:var(--ink);margin:18px 0 6px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px}
th{background:var(--tint);text-align:left;padding:8px 10px;
border-bottom:2px solid var(--rule);cursor:pointer;user-select:none;
position:relative;white-space:nowrap}
th:hover{background:var(--rule2)}
th::after{content:'\\2195';opacity:.3;margin-left:6px;font-size:10px}
td{padding:7px 10px;border-bottom:1px solid var(--rule2);vertical-align:top}
tr:hover td{background:#FCFDFE}
img{max-width:100%;height:auto;display:block;margin:18px 0}
em{color:var(--muted)}
code{background:var(--tint);padding:1px 5px;border-radius:3px;font-size:12px}
mark{background:#FDE68A;padding:0 2px;border-radius:2px}
.hide{display:none !important}
blockquote{margin:14px 0;padding:10px 16px;border-left:3px solid var(--accent);
background:var(--tint);color:var(--body)}
/* graph */
#graph{border:1px solid var(--rule);border-radius:8px;margin:18px 0;
background:#fff;position:relative}
#graph svg{display:block;width:100%;height:620px;overflow:visible}
.gnode{cursor:pointer}
.gnode circle{transition:r .12s,fill .12s}
.gnode:hover circle{stroke:var(--accent);stroke-width:2.5}
.glink{stroke:var(--rule);stroke-width:1.1;transition:stroke .12s,
stroke-width .12s,opacity .12s}
.glink.lit{stroke:var(--accent);stroke-width:2.2;opacity:1}
.dim{opacity:.1}
.gtext{font-size:11px;fill:var(--body);pointer-events:none}
.gtext.lit{fill:var(--navy);font-weight:700}
#legend{padding:10px 14px;border-top:1px solid var(--rule2);font-size:12px;
color:var(--muted);display:flex;gap:18px;flex-wrap:wrap;align-items:center}
#legend b{color:var(--ink)}
.swatch{display:inline-block;width:10px;height:10px;border-radius:50%;
margin-right:5px;vertical-align:-1px}
#detail{padding:12px 14px;border-top:1px solid var(--rule2);font-size:13px;
min-height:56px;background:var(--tint)}
.controls{display:flex;gap:10px;padding:10px 14px;
border-bottom:1px solid var(--rule2);flex-wrap:wrap;align-items:center}
.controls button{border:1px solid var(--rule);background:#fff;padding:5px 12px;
border-radius:5px;cursor:pointer;font-size:12px;color:var(--body)}
.controls button:hover{border-color:var(--accent);color:var(--accent)}
.controls button.on{background:var(--navy);color:#fff;border-color:var(--navy)}
.note{font-size:12px;color:var(--muted);margin:8px 0 0}
@media(max-width:900px){nav{display:none}main{padding:20px}}
@media print{header,nav,.controls{display:none}main{max-width:none}}
"""

_JS = r"""
// ---- search ---------------------------------------------------------------
// Filters by section. A hit inside a table row hides the sibling rows, so a
// search on a person's name leaves that person's rows and nothing else.
var q=document.getElementById('q'),hits=document.getElementById('hits'),
    main=document.querySelector('main'),timer=null;

function clearMarks(root){
  root.querySelectorAll('mark').forEach(function(m){
    var t=document.createTextNode(m.textContent);
    m.parentNode.replaceChild(t,m);
  });
  root.normalize();
}

function markIn(node,re){
  if(node.nodeType===3){
    var m=node.data.match(re); if(!m) return 0;
    var span=document.createElement('span');
    span.innerHTML=node.data.replace(re,function(s){return '<mark>'+s+'</mark>';});
    node.parentNode.replaceChild(span,node); return 1;
  }
  if(node.nodeType!==1||node.tagName==='SCRIPT'||node.tagName==='MARK') return 0;
  var n=0,kids=Array.prototype.slice.call(node.childNodes);
  for(var i=0;i<kids.length;i++) n+=markIn(kids[i],re);
  return n;
}

function search(){
  var term=q.value.trim();
  clearMarks(main);
  var sections=main.querySelectorAll('section');
  if(term.length<2){
    sections.forEach(function(s){s.classList.remove('hide');
      s.querySelectorAll('tbody tr').forEach(function(r){r.classList.remove('hide');});});
    hits.textContent=''; syncNav(); return;
  }
  var esc=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  var re=new RegExp(esc,'gi'),total=0,shown=0;
  sections.forEach(function(s){
    var text=s.textContent.toLowerCase();
    if(text.indexOf(term.toLowerCase())===-1){s.classList.add('hide');return;}
    s.classList.remove('hide'); shown++;
    // Narrow tables to matching rows only.
    s.querySelectorAll('table').forEach(function(t){
      var rows=t.querySelectorAll('tbody tr'),any=false;
      rows.forEach(function(r){
        if(r.textContent.toLowerCase().indexOf(term.toLowerCase())>-1){
          r.classList.remove('hide'); any=true;
        } else r.classList.add('hide');
      });
      if(!any) rows.forEach(function(r){r.classList.remove('hide');});
    });
    total+=markIn(s,re);
  });
  hits.textContent=total+' match'+(total===1?'':'es')+' in '+shown+' section'+(shown===1?'':'s');
  syncNav();
}
q.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(search,140);});

// ---- sortable tables ------------------------------------------------------
// Numeric columns sort numerically, including $2.4B and 71.1% and 1,234.
function numOf(s){
  s=s.replace(/[,$%*\s]/g,'');
  var mult=1;
  if(/B$/i.test(s)){mult=1e9;s=s.slice(0,-1);}
  else if(/M$/i.test(s)){mult=1e6;s=s.slice(0,-1);}
  else if(/K$/i.test(s)){mult=1e3;s=s.slice(0,-1);}
  var v=parseFloat(s);
  return isNaN(v)?null:v*mult;
}
document.querySelectorAll('table').forEach(function(t){
  var head=t.querySelector('thead'); if(!head) return;
  head.querySelectorAll('th').forEach(function(th,idx){
    th.addEventListener('click',function(){
      var body=t.querySelector('tbody'); if(!body) return;
      var rows=Array.prototype.slice.call(body.querySelectorAll('tr'));
      var dir=th.dataset.dir==='asc'?-1:1;
      head.querySelectorAll('th').forEach(function(o){delete o.dataset.dir;});
      th.dataset.dir=dir===1?'asc':'desc';
      rows.sort(function(a,b){
        var A=(a.cells[idx]||{}).textContent||'',B=(b.cells[idx]||{}).textContent||'';
        var na=numOf(A),nb=numOf(B);
        if(na!==null&&nb!==null) return (na-nb)*dir;
        return A.localeCompare(B)*dir;
      });
      rows.forEach(function(r){body.appendChild(r);});
    });
  });
});

// ---- contents highlight ---------------------------------------------------
function syncNav(){
  var links=document.querySelectorAll('nav a');
  links.forEach(function(a){
    var s=document.getElementById(a.getAttribute('href').slice(1));
    a.classList.toggle('hide',!!(s&&s.classList.contains('hide')));
  });
}
window.addEventListener('scroll',function(){
  var best=null,bt=1e9;
  document.querySelectorAll('main section').forEach(function(s){
    if(s.classList.contains('hide')) return;
    var top=Math.abs(s.getBoundingClientRect().top-80);
    if(top<bt){bt=top;best=s.id;}
  });
  document.querySelectorAll('nav a').forEach(function(a){
    a.classList.toggle('on',a.getAttribute('href')==='#'+best);
  });
});

// ---- network graph --------------------------------------------------------
(function(){
  var host=document.getElementById('graph'); if(!host||!window.GRAPH) return;
  var G=window.GRAPH;
  if(!G.nodes.length){host.innerHTML='<p class="note" style="padding:16px">'+
    'No network could be built from this run.</p>';return;}

  var COLOR={person:'#12283F',entity:'#6D8296',manager:'#B45309',
             issuer:'#2C4257',vehicle:'#A32020'};
  var LABEL={person:'Insider',entity:'Outside seat',manager:'13F manager',
             issuer:'Issuer',vehicle:'Vehicle'};
  var filter='all';

  var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  host.insertBefore(svg,host.firstChild);

  // Which side of the plot each kind belongs on. Everything here is bipartite
  // — a person to the boards they sit on, a manager to the issuers it holds —
  // so two columns is the shape of the data rather than a choice of style.
  var LEFT={person:1,manager:1,vehicle:1};

  function draw(){
    while(svg.firstChild) svg.removeChild(svg.firstChild);
    var kinds=filter==='people'?['person','entity','vehicle']
             :filter==='capital'?['manager','issuer']
             :null;
    var nodes=G.nodes.filter(function(n){return !kinds||kinds.indexOf(n.kind)>-1;});
    var keep={}; nodes.forEach(function(n){keep[n.id]=true;});
    var links=G.links.filter(function(l){return keep[l.source]&&keep[l.target];});
    if(!nodes.length){
      svg.setAttribute('viewBox','0 0 1000 200');
      var t=document.createElementNS(svg.namespaceURI,'text');
      t.setAttribute('x',500);t.setAttribute('y',100);
      t.setAttribute('text-anchor','middle');t.setAttribute('class','gtext');
      t.textContent='Nothing in this layer for this issuer.';
      svg.appendChild(t);
      document.getElementById('detail').textContent='';
      return;
    }

    // Deterministic layout. A force simulation settles somewhere different on
    // every open, so two readers cannot describe the same picture; here the
    // order is by degree within each column and the result is reproducible.
    var left=nodes.filter(function(n){return LEFT[n.kind];})
                  .sort(function(a,b){return b.degree-a.degree;});
    var right=nodes.filter(function(n){return !LEFT[n.kind];})
                   .sort(function(a,b){return b.degree-a.degree;});

    var rows=Math.max(left.length,right.length);
    var gap=26, pad=40;
    var height=Math.max(320, rows*gap+pad*2);
    var W=1000, lx=300, rx=700;
    svg.setAttribute('viewBox','0 0 '+W+' '+height);
    svg.style.height=Math.min(1500,height)+'px';

    var pos={};
    function place(list,x){
      // Centre a short column against a long one so the plot stays balanced.
      var span=(list.length-1)*gap;
      var top=(height-span)/2;
      list.forEach(function(n,i){pos[n.id]={x:x,y:list.length===1?height/2:top+i*gap};});
    }
    place(left,lx); place(right,rx);

    var gl=document.createElementNS(svg.namespaceURI,'g');
    var gn=document.createElementNS(svg.namespaceURI,'g');
    svg.appendChild(gl);svg.appendChild(gn);

    var lineOf={};
    links.forEach(function(l,i){
      var a=pos[l.source],b=pos[l.target];
      if(!a||!b) return;
      var p=document.createElementNS(svg.namespaceURI,'path');
      // A cubic with horizontal handles keeps the bundle readable where many
      // edges leave one node.
      var mid=(a.x+b.x)/2;
      p.setAttribute('d','M'+a.x+','+a.y+' C'+mid+','+a.y+' '+mid+','+b.y+' '+b.x+','+b.y);
      p.setAttribute('fill','none');p.setAttribute('class','glink');
      gl.appendChild(p);
      (lineOf[l.source]=lineOf[l.source]||[]).push(i);
      (lineOf[l.target]=lineOf[l.target]||[]).push(i);
      l._el=p;
    });

    var els={};
    nodes.forEach(function(n){
      var p=pos[n.id]; if(!p) return;
      var onLeft=!!LEFT[n.kind];
      var g=document.createElementNS(svg.namespaceURI,'g');
      g.setAttribute('class','gnode');
      var c=document.createElementNS(svg.namespaceURI,'circle');
      c.setAttribute('cx',p.x);c.setAttribute('cy',p.y);
      c.setAttribute('r',Math.max(4,Math.min(13,3+n.degree*1.4)));
      c.setAttribute('fill',COLOR[n.kind]||'#888');
      c.setAttribute('stroke','#fff');c.setAttribute('stroke-width','1.2');
      g.appendChild(c);
      var t=document.createElementNS(svg.namespaceURI,'text');
      t.setAttribute('x',p.x+(onLeft?-16:16));t.setAttribute('y',p.y+3.5);
      t.setAttribute('text-anchor',onLeft?'end':'start');
      t.setAttribute('class','gtext');
      t.textContent=n.name.length>32?n.name.slice(0,31)+'\u2026':n.name;
      g.appendChild(t);
      gn.appendChild(g);
      els[n.id]={g:g,text:t,circle:c};
      g.addEventListener('click',function(){select(n);});
      g.addEventListener('mouseenter',function(){select(n);});
    });
    svg.addEventListener('mouseleave',function(){
      links.forEach(function(l){if(l._el){l._el.classList.remove('lit','dim');}});
      nodes.forEach(function(o){
        if(!els[o.id]) return;
        els[o.id].g.classList.remove('dim');
        els[o.id].text.classList.remove('lit');
      });
    });

    function select(n){
      var mine=lineOf[n.id]||[],near={};
      mine.forEach(function(i){near[links[i].source]=1;near[links[i].target]=1;});
      links.forEach(function(l,i){
        if(!l._el) return;
        l._el.classList.toggle('lit',mine.indexOf(i)>-1);
        l._el.classList.toggle('dim',mine.indexOf(i)===-1);
      });
      nodes.forEach(function(o){
        if(!els[o.id]) return;
        els[o.id].g.classList.toggle('dim',!near[o.id]);
        els[o.id].text.classList.toggle('lit',!!near[o.id]);
      });
      var byId={}; nodes.forEach(function(z){byId[z.id]=z;});
      var others=Object.keys(near).filter(function(k){return +k!==n.id;})
        .map(function(k){return byId[k]?byId[k].name:'';}).filter(Boolean);
      var meta=[];
      if(n.meta.roles) meta.push(n.meta.roles);
      if(n.meta.ticker) meta.push(n.meta.ticker);
      if(n.meta.issuers) meta.push(n.meta.issuers+' issuers held');
      document.getElementById('detail').innerHTML=
        '<b>'+n.name+'</b> &mdash; '+(LABEL[n.kind]||n.kind)+
        (meta.length?' ('+meta.join(', ')+')':'')+'<br>'+
        (others.length? 'Connected to '+others.length+': '+others.join(', ')
                      : 'No connections in this layer.');
    }

    document.getElementById('detail').innerHTML=
      '<b>'+nodes.length+' nodes, '+links.length+' connections.</b> '+
      'Click or hover any node to isolate what it connects to.';
  }

  document.querySelectorAll('.controls button[data-filter]').forEach(function(b){
    b.addEventListener('click',function(){
      document.querySelectorAll('.controls button[data-filter]')
        .forEach(function(o){o.classList.remove('on');});
      b.classList.add('on'); filter=b.dataset.filter; draw();
    });
  });
  draw();
})();
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "section"


def _sectionise(body_html: str) -> tuple:
    """Wrap each <h2> and its content in a <section>, and build a contents list.

    The search filters by section, so the document has to actually have them;
    a markdown converter emits a flat run of siblings.
    """
    parts = re.split(r"(?=<h2[^>]*>)", body_html)
    sections, contents = [], []

    if parts and not parts[0].lstrip().startswith("<h2"):
        sections.append(f'<section id="top">{parts.pop(0)}</section>')

    for part in parts:
        match = re.search(r"<h2[^>]*>(.*?)</h2>", part, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else "Section"
        slug = _slug(title)
        # Two sections can slug identically; suffix rather than lose one.
        base, n = slug, 2
        existing = {c[0] for c in contents}
        while slug in existing:
            slug = f"{base}-{n}"
            n += 1
        contents.append((slug, title))
        sections.append(f'<section id="{slug}">{part}</section>')

    return "".join(sections), contents


def generate_interactive_report(markdown_content: str, data: Dict[str, Any],
                                output_path: str, entity_name: str = "",
                                ticker: str = "") -> Dict[str, Any]:
    """Write a single self-contained interactive HTML beside the PDF."""
    try:
        import markdown as md_lib
    except ImportError:
        logger.warning("markdown package unavailable; interactive report skipped")
        return {"written": False, "reason": "markdown package not installed"}

    converter = md_lib.Markdown(extensions=["tables", "attr_list", "md_in_html"])
    body_html = converter.convert(markdown_content)

    # Give every table a thead so the sort handler has something to bind to.
    body_html = re.sub(r"<table>", '<table class="sortable">', body_html)

    sections_html, contents = _sectionise(body_html)
    graph = build_graph_payload(data)

    health = data.get("data_health") or {}
    news = (data.get("news_intelligence") or {}).get("summary") or {}
    subtitle = " · ".join(filter(None, [
        f"{health.get('healthy', 0)}/{health.get('total', 0)} sources"
        if health else None,
        f"{news.get('article_count')} articles" if news.get("article_count") else None,
        f"{len(graph['nodes'])} network nodes" if graph["nodes"] else None,
        datetime.now().strftime("%d %b %Y"),
    ]))

    nav_html = "".join(
        f'<a href="#{slug}">{html.escape(title)}</a>' for slug, title in contents)

    graph_block = f"""
<section id="network-explorer">
<h2>Network Explorer</h2>
<p>Every connection this report found, in one view. Click or hover a node to
isolate what it touches. Insiders and the outside boards they sit on come from
Section 16 filings; managers and the issuers they hold come from 13F. Node size
is the number of connections.</p>
<div id="graph">
  <div class="controls">
    <button data-filter="all" class="on">All</button>
    <button data-filter="people">People and seats</button>
    <button data-filter="capital">Managers and issuers</button>
    <span class="note" style="margin-left:auto">
      {len(graph['nodes'])} nodes, {len(graph['links'])} connections</span>
  </div>
  <div id="detail"></div>
  <div id="legend">
    <span><span class="swatch" style="background:#12283F"></span>Insider</span>
    <span><span class="swatch" style="background:#6D8296"></span>Outside seat</span>
    <span><span class="swatch" style="background:#B45309"></span>13F manager</span>
    <span><span class="swatch" style="background:#2C4257"></span>Issuer</span>
    <span><span class="swatch" style="background:#A32020"></span>Vehicle</span>
      <span style="margin-left:auto">People and managers on the left, the
      entities they touch on the right. Layout is fixed, not simulated, so the
      same data always draws the same picture.</span>
  </div>
</div>
</section>
"""

    document = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(entity_name or ticker)} — Intelligence Report</title>
<style>{_CSS}</style></head>
<body>
<header>
  <h1>{html.escape(entity_name or ticker)}
    <span class="meta">{html.escape(subtitle)}</span></h1>
  <input id="q" type="search" placeholder="Search the whole report — a person, a company, an amount…"
         autocomplete="off" spellcheck="false">
  <span id="hits"></span>
</header>
<div class="layout">
  <nav><a href="#network-explorer">Network Explorer</a>{nav_html}</nav>
  <main>{graph_block}{sections_html}</main>
</div>
<script>window.GRAPH={json.dumps(graph, default=str)};</script>
<script>{_JS}</script>
</body></html>"""

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(document)

    return {
        "written": True,
        "path": output_path,
        "bytes": len(document.encode("utf-8")),
        "sections": len(contents),
        "nodes": len(graph["nodes"]),
        "links": len(graph["links"]),
    }
