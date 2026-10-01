"""Build the standalone teaching guide; does not start or modify the application.

Run from the repository root: python docs/build_reviewer_guide.py
Requires the Python Markdown package in the documentation environment. The generated
HTML has no network, CDN, provider, or JavaScript package dependencies.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

import markdown

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "REVIEWER_GUIDE.md"
OUTPUT = SOURCE.with_suffix(".html")

CSS = r"""
:root{color-scheme:light;--paper:#faf9f5;--sheet:#fff;--ink:#232c2a;--muted:#586560;--rule:#d6ded7;--accent:#19624c;--wash:#e9f1ec;--mark:#f5e6af;--code:#eef1ed}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:5rem}body{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:17px;line-height:1.75}a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,input,select{font:inherit}button{cursor:pointer}button,.button{padding:.45rem .8rem;border:1px solid var(--rule);background:var(--sheet);color:var(--ink);border-radius:6px;text-decoration:none;font-size:.85rem}button:hover,.button:hover{background:var(--wash)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}[hidden]{display:none!important}.skip{position:fixed;left:1rem;top:-5rem;z-index:100;background:var(--sheet);padding:.75rem}.skip:focus{top:1rem}.top{height:62px;position:sticky;top:0;z-index:20;background:var(--paper);border-bottom:1px solid var(--rule);display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem;gap:1rem}.brand{font-weight:760;letter-spacing:-.03em;font-size:1.35rem;color:var(--ink);text-decoration:none}.top-actions{display:flex;align-items:center;gap:.5rem}.reading{font-size:.75rem;color:var(--muted)}.layout{display:grid;grid-template-columns:285px minmax(0,1fr);max-width:1640px;margin:auto}.sidebar{position:sticky;top:62px;height:calc(100vh - 62px);padding:1.5rem 1rem 2rem 1.4rem;border-right:1px solid var(--rule);overflow:auto}.sidebar h2{margin:0;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}.search{margin:.7rem 0 .4rem;display:flex;align-items:center;gap:.4rem}.search input{width:100%;padding:.6rem;border:1px solid var(--rule);border-radius:6px;background:var(--sheet);color:var(--ink);font-size:.85rem}.search button{padding:.4rem .6rem}.search-count{font-size:.75rem;color:var(--muted);min-height:1.5rem}.chapter-nav{display:grid;gap:.2rem;margin-top:.75rem}.chapter-nav a{display:grid;grid-template-columns:1.8rem 1fr;align-items:start;text-decoration:none;color:var(--muted);font-size:.79rem;line-height:1.4;padding:.55rem .65rem;border-radius:5px;border-left:3px solid transparent}.chapter-nav a:hover,.chapter-nav a[aria-current=true]{color:var(--accent);background:var(--wash);border-left-color:var(--accent)}.chapter-nav .num{font-variant-numeric:tabular-nums;font-size:.75rem}.sidebar-note{font-size:.73rem;line-height:1.55;color:var(--muted);margin-top:1.5rem}.main{min-width:0;padding:3.2rem clamp(1.1rem,4vw,4.5rem) 6rem}.intro,.chapter{max-width:1010px;margin:auto}.intro h1{font-size:clamp(2rem,3.8vw,3.7rem);line-height:1.12;letter-spacing:-.045em;max-width:22ch;margin:0 0 1.2rem}.intro>p{max-width:80ch}.kicker{color:var(--accent);text-transform:uppercase;font-size:.72rem;font-weight:750;letter-spacing:.13em;margin:0 0 .7rem}.chapter{padding:2.6rem 0;border-top:1px solid var(--rule);margin-top:2rem;scroll-margin-top:1rem}.chapter h2{font-size:clamp(1.6rem,2.2vw,2.3rem);line-height:1.25;letter-spacing:-.035em;margin:0 0 1.35rem}.chapter h3{font-size:1.25rem;line-height:1.35;margin:2rem 0 .85rem;letter-spacing:-.02em}.chapter p,.chapter>ul,.chapter>ol{max-width:83ch}.chapter p{margin:.9rem 0}.chapter li{padding-left:.2rem;margin:.5rem 0}.chapter ul,.chapter ol{padding-left:1.4rem}.chapter strong{font-weight:690}.chapter pre{background:#223b33;color:#eaf4ed;padding:1.15rem 1.3rem;overflow:auto;border-radius:6px;font-size:.82rem;line-height:1.65;tab-size:4}.chapter code{font-family:Consolas,"Cascadia Code",monospace;font-size:.87em;background:var(--code);padding:.1rem .24rem;border-radius:3px;overflow-wrap:anywhere}.chapter pre code{padding:0;background:transparent;color:inherit;font-size:inherit;overflow-wrap:normal}.table-wrap{max-width:100%;overflow-x:auto;margin:1.4rem 0;border:1px solid var(--rule);border-radius:6px;background:var(--sheet)}table{border-collapse:collapse;width:100%;font-size:.86rem;line-height:1.55;text-align:left}th{background:var(--wash);font-weight:680}th,td{padding:.8rem .9rem;vertical-align:top;border-bottom:1px solid var(--rule)}tr:last-child td{border-bottom:0}td:first-child{font-weight:550}td code{font-size:.85em}blockquote{margin:1.3rem 0;border-left:3px solid var(--accent);padding:.1rem 1rem;color:var(--muted)}mark{background:var(--mark);color:var(--ink);border-radius:2px}.no-results{border:1px solid var(--rule);padding:2rem;border-radius:8px}.file-link{color:var(--accent)}.study-box{border:1px solid var(--rule);background:var(--sheet);border-radius:8px;padding:1.4rem;margin:1.3rem 0}.study-box h3{margin:0 0 .7rem}.study-box>p{font-size:.9rem;color:var(--muted)}.sandbox{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}.sandbox label{border:1px solid var(--rule);border-radius:5px;padding:.65rem;font-size:.87rem;display:flex;align-items:flex-start;gap:.55rem}.sandbox input{margin-top:.35rem;accent-color:var(--accent)}.result{display:block;margin:1rem 0 0;padding:1rem;background:var(--wash);border-radius:5px;font-size:.95rem}.calc-grid{display:flex;flex-wrap:wrap;gap:1rem}.calc-grid label{font-size:.85rem;display:grid;gap:.25rem}.calc-grid input,.calc-grid select{width:180px;max-width:100%;padding:.45rem;border:1px solid var(--rule);border-radius:5px;background:var(--sheet);color:var(--ink)}.cards details{padding:.8rem 0;border-bottom:1px solid var(--rule)}.cards details:last-child{border:0}.cards summary{cursor:pointer;font-weight:640;line-height:1.5;font-size:.95rem}.cards details p{font-size:.91rem;margin:.75rem 0 .2rem}.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin:1.1rem 0}.flow div{background:var(--wash);padding:.8rem;border:1px solid var(--rule);border-radius:6px;font-size:.82rem;line-height:1.5}.flow b{display:block;font-size:.9rem}.footer{font-size:.8rem;color:var(--muted);border-top:1px solid var(--rule);padding-top:1rem;max-width:1010px;margin:2rem auto}.mobile-nav{display:none}.group-tag{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;margin:1rem .65rem .3rem}.intro-actions{display:flex;flex-wrap:wrap;gap:.5rem;margin:1.5rem 0}.intro-actions .primary{background:var(--accent);border-color:var(--accent);color:#fff}.reading-note{padding:.9rem 1.1rem;background:var(--wash);border-left:3px solid var(--accent);font-size:.9rem;margin:1.5rem 0}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--paper:#18201c;--sheet:#202b25;--ink:#e2e9e3;--muted:#adbbb0;--rule:#3b4d41;--accent:#a4d8b6;--wash:#263b30;--mark:#655728;--code:#2d3931}.intro-actions .primary{background:#2d6b49;color:#fff}.chapter pre{background:#0e1812}}
@media(max-width:1000px){.layout{grid-template-columns:245px minmax(0,1fr)}.sidebar{padding-left:.8rem}.main{padding-left:1.5rem;padding-right:1.5rem}.reading{display:none}.sandbox{grid-template-columns:1fr}}
@media(max-width:760px){body{font-size:16px}.layout{display:block}.top{padding:0 1rem}.brand{font-size:1.15rem}.mobile-nav{display:block}.sidebar{display:none;position:sticky;top:62px;height:65vh;border-bottom:1px solid var(--rule);z-index:15;background:var(--paper)}.sidebar.open{display:block}.main{padding:2rem 1rem 4rem}.flow{grid-template-columns:1fr}.chapter{padding-top:2rem}.top-actions .md-link{display:none}table{font-size:.8rem}th,td{padding:.65rem;min-width:130px}td:first-child{min-width:140px}.calc-grid input,.calc-grid select{width:150px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{font-size:10pt;background:#fff;color:#111;line-height:1.5}.top,.sidebar,.intro-actions,.interactive-controls,.skip,.search-count,.no-results{display:none!important}.layout{display:block}.main{padding:0}.chapter[hidden],.intro[hidden]{display:block!important}.chapter{margin:1rem 0;padding:1rem 0;break-before:auto}.chapter h2{font-size:18pt;break-after:avoid}.chapter h3{break-after:avoid}.table-wrap{overflow:visible;border-color:#bbb}th{background:#eee}td,th{font-size:8pt;padding:5pt;border-color:#ddd}.chapter pre{white-space:pre-wrap;background:#eee;color:#111;border:1px solid #bbb;overflow:visible}.chapter code{background:#eee;color:#111}a{color:#111}.study-box{break-inside:avoid}.flow{grid-template-columns:repeat(3,1fr)}mark{background:transparent}.chapter p{max-width:none}.footer{color:#333}.intro h1{font-size:28pt}details p{display:block}.result{background:#eee;color:#111}@page{margin:16mm}}
"""

STUDY = r"""
<section class="chapter" id="study-lab" aria-labelledby="study-title">
<h2 id="study-title">Practice lab: make the ideas concrete</h2>
<p>These small examples run entirely in this page. They teach the recorded rules; they do not call the app, assess a real scenario, or reproduce model judgments.</p>
<div class="study-box"><h3>The whole pipeline</h3><div class="flow" aria-label="Six-step assessment flow">
<div><b>1. Retrieve</b>Keyword + local vectors; ten hits plus bounded related context.</div>
<div><b>2. Analyze</b>Propose facts, requirement findings, and up to three questions.</div>
<div><b>3. Score risk</b>Apply the demo rubric to provisional findings.</div>
<div><b>4. Validate + inspect coverage</b>Check sources, interpretations, and candidate dispositions. Recompute risk.</div>
<div><b>5. Recommend</b>Propose actions linked to validated gaps.</div>
<div><b>6. Decide + save</b>Ordered Python rules, evidence scores, stored assessment, completion event.</div>
</div></div>
<div class="study-box"><h3>Try the final-status rules</h3><p>Choose properties of the findings after validation. Change several together to see the precedence. This illustrates model-mode final checks, not the separate no-candidate local-review rule.</p>
<div class="sandbox interactive-controls" id="outcome-controls">
<label><input type="checkbox" id="has-breach"> A validated violation exists</label>
<label><input type="checkbox" id="has-conflict"> A validated conflict exists</label>
<label><input type="checkbox" id="has-unknown"> A validated unknown exists</label>
<label><input type="checkbox" id="has-unconfirmed"> A decisive claim is unconfirmed</label>
<label><input type="checkbox" id="has-gap"> A retrieved candidate is unresolved</label>
<label><input type="checkbox" id="has-met" checked> A validated met requirement exists</label>
</div><output class="result" id="outcome-result" aria-live="polite">Compliant within scope: at least one validated met requirement, with no blocking condition selected.</output>
</div>
<div class="study-box"><h3>Calculate a retrieval score</h3><p>Use 1-based ranks; leave a channel blank if the chunk did not appear there. RRF scores order chunks and do not express probability.</p>
<div class="calc-grid interactive-controls"><label>Lexical rank<input id="lex-rank" type="number" min="1" max="20" value="2"></label><label>Dense rank<input id="dense-rank" type="number" min="1" max="20" value="5"></label></div>
<output class="result" id="rrf-result" aria-live="polite">1/62 + 1/65 = 0.031514</output>
</div>
<div class="study-box"><h3>Calculate a finding evidence score</h3><p>Select already-recorded checks for one finding. The fact options follow a non-unknown finding; for an unknown finding the code gives 25 points when missing facts are named, otherwise 10.</p>
<div class="calc-grid interactive-controls">
<label>Validation<select id="score-validation"><option value="40">Confirmed · 40</option><option value="10">Pending · 10</option><option value="0">Rejected · 0</option></select></label>
<label>Quotation<select id="score-quote"><option value="20">Verified quote · 20</option><option value="10">Whole-clause fallback · 10</option><option value="0">No citation · 0</option></select></label>
<label>Deciding facts<select id="score-facts"><option value="25">Stated/confirmed · 25</option><option value="12">Inferred · 12</option><option value="5">Unknown · 5</option><option value="0">None · 0</option></select></label>
<label>Search<select id="score-search"><option value="10">Rank 4–10 · 10</option><option value="15">Rank 1–3 · 15</option><option value="5">Related only · 5</option><option value="0">Absent · 0</option></select></label>
</div><output class="result" id="score-result" aria-live="polite">95 points · high evidence band. This is not 95% probability or compliance.</output>
</div>
<div class="study-box cards"><h3>Explain first, then reveal</h3><p>Practice each answer aloud before opening it. The questions are also covered in chapters 24 and 25.</p>
<details><summary>Why can a case be non-compliant while some facts remain unknown?</summary><p>One validated breach decides non-compliance before the unknown rule. Unknowns do not erase an established violation, although they remain visible as other open checks.</p></details>
<details><summary>Why are valid citations insufficient?</summary><p>A matching quote proves the words occur in a retrieved clause. It does not prove applicability, correct fact interpretation, or that all relevant requirements were retrieved and assessed.</p></details>
<details><summary>What is the difference between a clause and a chunk?</summary><p>A clause is a numbered policy unit used for citations and findings. A chunk is a search-sized piece of that clause. Several chunks can point to the same source clause.</p></details>
<details><summary>Where are BM25, LangChain, and LangGraph used?</summary><p>They are not used in this runtime. The code uses PostgreSQL cover-density lexical ranking, provider SDK adapters, and ordinary Python workflow functions. They are alternatives to explain honestly.</p></details>
<details><summary>What do snapshot and activity date each control?</summary><p>The snapshot pins available published versions and index metadata. The activity date selects the version in force for the business activity. Clarification preserves the original snapshot.</p></details>
<details><summary>What does 95 high confidence mean?</summary><p>Ninety-five evidence-rubric points from validation, quotes, facts, and search. It is not a calibrated probability. Support and ordered status rules still govern the result.</p></details>
<details><summary>Why can headline accuracy exceed requirement agreement?</summary><p>A correct decisive breach can give the right headline even if other requirement judgments are missing or wrong. Clause-level agreement measures those underlying checks.</p></details>
<details><summary>Why measure unjustified compliance separately from false compliance?</summary><p>False compliance only covers known-breach labels. Unjustified compliance also covers clearance of cases labelled unknown or conflicting. Their denominators differ.</p></details>
<details><summary>What exactly does coverage cover?</summary><p>Classified and reviewed candidates in the retrieved bundle. It cannot detect unretrieved obligations or an incorrect disposition that validation accepts.</p></details>
<details><summary>Is local review equivalent to a local language model?</summary><p>No. It searches sources and records explicit user dispositions. Code checks source/choice consistency; the person interprets applicability and exceptions. Numerical model evidence scores are omitted.</p></details>
<details><summary>Can SSE resume interrupted computation?</summary><p>SSE replays persisted progress events after reconnection. An active computation interrupted by a server restart is marked failed, not resumed from a stage checkpoint.</p></details>
<details><summary>What can you say about the latest benchmark?</summary><p>The saved 30 September development run matched 12/13 statuses and 32/44 requirement labels, with zero observed unjustified clearances in nine eligible cases. It is a small tuned synthetic-set observation, not held-out accuracy.</p></details>
</div>
</section>
"""

JS = r"""
const chapters=[...document.querySelectorAll('.chapter')];
const links=[...document.querySelectorAll('.chapter-nav a')];
const search=document.getElementById('guide-search');
const count=document.getElementById('search-count');
const intro=document.querySelector('.intro');
const noResults=document.getElementById('no-results');
function clearMarks(){document.querySelectorAll('mark.search-hit').forEach(m=>{const p=m.parentNode;m.replaceWith(document.createTextNode(m.textContent));p.normalize()})}
function markText(section,query){
 const walker=document.createTreeWalker(section,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement.closest('script,style,input,select,option,button,summary,h2,h3')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
 const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
 for(const n of nodes){const value=n.nodeValue,lower=value.toLocaleLowerCase();let at=0,pos=lower.indexOf(query),found=false;const frag=document.createDocumentFragment();while(pos>=0){found=true;frag.append(document.createTextNode(value.slice(at,pos)));const mark=document.createElement('mark');mark.className='search-hit';mark.textContent=value.slice(pos,pos+query.length);frag.append(mark);at=pos+query.length;pos=lower.indexOf(query,at)}if(found){frag.append(document.createTextNode(value.slice(at)));n.replaceWith(frag)}}
}
function filterGuide(){clearMarks();const q=search.value.trim().toLocaleLowerCase();let visible=0;chapters.forEach(c=>{const show=!q||c.textContent.toLocaleLowerCase().includes(q);c.hidden=!show;if(show){visible++;if(q.length>=2)markText(c,q)}});links.forEach(a=>{const c=document.getElementById(a.hash.slice(1));a.hidden=c.hidden});intro.hidden=!!q;count.textContent=q?`${visible} matching chapters`:'Search chapters, code files, or terms';noResults.hidden=visible!==0}
let searchTimer;search.addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(filterGuide,150)});
document.getElementById('search-clear').addEventListener('click',()=>{clearTimeout(searchTimer);search.value='';filterGuide();search.focus()});
document.getElementById('print-guide').addEventListener('click',()=>window.print());
const menu=document.getElementById('menu-toggle'),sidebar=document.getElementById('guide-sidebar');
menu.addEventListener('click',()=>{const open=sidebar.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.textContent=open?'Close':'Chapters'});
links.forEach(a=>a.addEventListener('click',()=>{sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');menu.textContent='Chapters'}));
if('IntersectionObserver'in window){const observer=new IntersectionObserver(entries=>{const entry=entries.find(e=>e.isIntersecting);if(entry)links.forEach(a=>{if(a.hash==='#'+entry.target.id)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current')})},{rootMargin:'-70px 0px -65% 0px',threshold:0});chapters.forEach(c=>observer.observe(c))}
function value(id){return document.getElementById(id).checked}
function updateOutcome(){let status,reason;if(value('has-breach')){status='Non-compliant';reason='A validated violation decides, even with other unknowns or conflicts.'}else if(value('has-conflict')){status='Conflicting policy';reason='A validated conflict decides when no breach is established.'}else if(value('has-unknown')||value('has-unconfirmed')||value('has-gap')){status='Insufficient information';reason='Unknowns, unconfirmed decisive claims, or unresolved candidates block clearance.'}else if(value('has-met')){status='Compliant within scope';reason='At least one validated met requirement, with no blocking condition selected.'}else{status='Out of scope';reason='No applicable requirement is established. This is not positive clearance.'}document.getElementById('outcome-result').textContent=`${status}: ${reason}`}
document.querySelectorAll('#outcome-controls input').forEach(e=>e.addEventListener('change',updateOutcome));
function updateRrf(){const parts=[];let score=0;for(const id of ['lex-rank','dense-rank']){const e=document.getElementById(id);if(e.value==='')continue;const rank=Number(e.value);if(!Number.isInteger(rank)||rank<1||rank>20){document.getElementById('rrf-result').textContent='Enter a whole-number rank from 1 to 20, or leave the channel blank.';return}parts.push(`1/${60+rank}`);score+=1/(60+rank)}document.getElementById('rrf-result').textContent=parts.length?`${parts.join(' + ')} = ${score.toFixed(6)} · ranking score, not a probability.`:'No channel contribution: 0.000000'}
['lex-rank','dense-rank'].forEach(id=>document.getElementById(id).addEventListener('input',updateRrf));
function updateScore(){const points=['score-validation','score-quote','score-facts','score-search'].reduce((sum,id)=>sum+Number(document.getElementById(id).value),0);const band=points>=80?'high':points>=50?'medium':'low';document.getElementById('score-result').textContent=`${points} points · ${band} evidence band. This is not ${points}% probability or compliance.`}
['score-validation','score-quote','score-facts','score-search'].forEach(id=>document.getElementById(id).addEventListener('change',updateScore));
updateOutcome();updateRrf();updateScore();
"""


def file_links(content: str) -> str:
    """Link real source paths while leaving formulas, commands and wildcards alone."""
    def replace(match: re.Match[str]) -> str:
        raw = html.unescape(match.group(1))
        if "\n" in raw or "<" in raw or "*" in raw:
            return match.group(0)
        if raw.startswith(("apps/", "services/", "scripts/", "packages/", "docs/", "data/", ".github/")):
            path = ROOT / raw
        elif "/" not in raw and (ROOT / raw).is_file():
            path = ROOT / raw
        else:
            return match.group(0)
        if not path.is_file():
            return match.group(0)
        href = quote("../" + path.relative_to(ROOT).as_posix(), safe="/.")
        return f'<a class="file-link" href="{href}">{match.group(0)}</a>'
    return re.sub(r"<code>([^<]+)</code>", replace, content)


def build() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    rendered = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    rendered = file_links(rendered)
    rendered = re.sub(
        r"<table>(.*?)</table>",
        r'<div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable comparison table"><table>\1</table></div>',
        rendered,
        flags=re.S,
    )
    sections = re.split(r"(?=<h2>)", rendered)
    intro = sections[0]
    nav = []
    body = []
    for section in sections[1:]:
        heading = re.search(r"<h2>(.*?)</h2>", section)
        assert heading is not None
        title = html.unescape(re.sub(r"<[^>]+>", "", heading.group(1)))
        number, label = title.split(". ", 1)
        ident = f"chapter-{number}"
        section = section.replace("<h2>", f'<h2 id="title-{number}">', 1)
        body.append(f'<section class="chapter" id="{ident}" aria-labelledby="title-{number}">{section}</section>')
        nav.append(f'<a href="#{ident}"><span class="num">{number.zfill(2)}</span><span>{html.escape(label)}</span></a>')
    nav.append('<a href="#study-lab"><span class="num">↗</span><span>Interactive practice lab</span></a>')
    words = len(text.split())
    reading_minutes = round(words / 220)
    intro = '<p class="kicker">Clause / reviewer preparation</p>' + intro
    intro += '<div class="intro-actions"><a class="button primary" href="#chapter-1">Start with the purpose</a><a class="button" href="#chapter-22">Find the code</a><a class="button" href="#chapter-16">Learn the metrics</a><a class="button" href="#study-lab">Practice the rules</a></div>'
    intro += '<p class="reading-note">Study one chapter at a time. The implementation uses PostgreSQL full text and a Python coordinator. BM25, LangChain, and LangGraph are explained as alternatives. All measurements here are identified by their scope and date.</p>'
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="A plain-English guide to Clause: architecture, every module and code file, retrieval, workflow, evaluation, technology tradeoffs, and reviewer practice."><title>Clause — understand and explain the app</title><style>{CSS}</style></head>
<body><a class="skip" href="#guide-main">Skip to the guide</a>
<header class="top"><a class="brand" href="#">Clause / study guide</a><div class="top-actions"><span class="reading">25 chapters · about {reading_minutes} minutes of reading</span><a class="button md-link" href="REVIEWER_GUIDE.md">Markdown</a><button id="print-guide" type="button">Print / PDF</button><button class="mobile-nav" id="menu-toggle" type="button" aria-controls="guide-sidebar" aria-expanded="false">Chapters</button></div></header>
<div class="layout"><aside class="sidebar" id="guide-sidebar" aria-label="Guide navigation"><h2>Learn the whole app</h2><div class="search"><label class="sr-only" for="guide-search" style="position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)">Search the guide</label><input type="search" id="guide-search" placeholder="Search metrics, files, concepts…"><button type="button" id="search-clear" aria-label="Clear search">×</button></div><p class="search-count" id="search-count" role="status">Search chapters, code files, or terms</p><nav class="chapter-nav" aria-label="Chapters">{''.join(nav)}</nav><p class="sidebar-note">Completed 1 October 2026.<br>Based on this checkout and saved development evidence.<br>Works offline; source links need the checkout.<br>No model calls from this page.</p></aside>
<main class="main" id="guide-main"><div class="intro">{intro}</div><p class="no-results" id="no-results" hidden>No chapters match. Try a shorter term or clear the search.</p>{''.join(body)}{STUDY}<footer class="footer">Generated from <a href="REVIEWER_GUIDE.md">REVIEWER_GUIDE.md</a>. Source files are linked relative to this checkout. This page is a teaching artifact, not a live assessment or a new evaluation run.</footer></main></div>
<noscript><p style="padding:1rem">All chapters are readable without JavaScript. Search, mobile chapter toggle, and calculators require JavaScript; use browser Find and Print instead.</p></noscript><script>{JS}</script></body></html>'''
    OUTPUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"Built {OUTPUT.relative_to(ROOT)}: {words:,} words, {len(body)} chapters.")


if __name__ == "__main__":
    build()
