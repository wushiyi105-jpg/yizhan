"""Web UI:http.server 单文件,零依赖。"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import agent, llm
from .db import Database

PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>译站 · 术语译对了吗</title>
<style>
:root{--bg:#f5f7f8;--card:#fff;--ink:#1f2529;--dim:#6b7680;--accent:#2f6f7d;--line:#dde5e8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:30px 18px 60px}
h1{font-size:25px;margin:0 0 4px}.sub{color:var(--dim);margin:0 0 18px}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:13px;margin-left:6px}
.tabs{display:flex;gap:8px;margin:16px 0}
.tab{padding:8px 16px;border:1px solid var(--line);background:var(--card);border-radius:8px;cursor:pointer}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:14px}
label{display:block;font-size:14px;color:var(--dim);margin:10px 0 4px}
input,textarea,select{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;font:inherit;background:#fff}
textarea{min-height:130px;resize:vertical}
button{padding:9px 18px;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;cursor:pointer}
button:disabled{opacity:.55;cursor:wait}
.out{white-space:pre-wrap;font:14px/1.8 Consolas,"Microsoft YaHei",monospace;background:#fbfdfd;border:1px solid var(--line);border-radius:8px;padding:14px;margin-top:12px;min-height:40px}
.row{display:flex;gap:10px}.row>*{flex:1}
.list div{padding:7px 0;border-bottom:1px dashed var(--line);font-size:14px}
a{color:var(--accent);cursor:pointer}

:root{--maxw:980px;--bg:#f4eddf;--card:#fffdf8;--ink:#28213a;--text:#28213a;--dim:#71697f;--line:#d9ccb9;--accent:#5c3d78;--muted:#71697f}
.wrap{max-width:980px}
body{background:#f4eddf;color:#28213a;font-family:"Songti SC","SimSun",Georgia,serif}
h1{color:#28213a}
header{max-width:980px;margin:0 auto}
input,textarea,select{background:#fff;color:#28213a;border-color:#d9ccb9;border-radius:2px}
button:not(.ghost):not(.tab){background:#5c3d78;color:#fff;border-radius:2px}
button.ghost{background:transparent!important;color:#5c3d78!important;border:1px solid #d9ccb9!important}
h2,h3{color:#5c3d78}
pre{background:#fafaf6;color:#28213a;border-color:#d9ccb9}
.item,.card{border-color:#d9ccb9;background:#fffdf8}
.k,.empty,.hint{color:#71697f}

h1{font-size:clamp(31px,5vw,39px);line-height:1.26}
.prod{display:block;font-size:11px;line-height:1.4;letter-spacing:.18em;font-weight:650;margin-bottom:8px;opacity:.72}
.lede,.sub{max-width:62ch;line-height:1.75}
.route{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin:16px auto 20px;border:1px solid var(--line);background:var(--line);max-width:var(--maxw)}
.route span{padding:11px 13px;background:var(--card);font-size:12px;line-height:1.5}
.route b{display:block;font-size:10px;letter-spacing:.1em;margin-bottom:3px;opacity:.66}
button{min-height:46px}
input,select{min-height:44px}
pre{white-space:pre-wrap}
@media(max-width:680px){
  .wrap{padding:20px 16px 56px}
  .route{grid-template-columns:1fr}
  h1{font-size:30px!important}
  .row>div{min-width:100%!important}
  button{width:100%}
}

h1{font-size:38px;color:#28213a}
.sub{color:#71697f;font-family:"PingFang SC","Microsoft YaHei",sans-serif;font-size:14px}
.tabs{margin:16px 0}
.tab{border:1px solid #d9ccb9;border-radius:0;background:#fffdf8;color:#71697f;padding:9px 16px}
.tab.on{background:#5c3d78;color:#fff;border-color:#5c3d78}
.card{background:#fffdf8;border:1px solid #d9ccb9;border-left:5px solid #5c3d78;border-radius:0;box-shadow:none}
button{background:#5c3d78;border-radius:0;letter-spacing:.05em}
button:hover{background:#4a3062}
input,textarea,select{background:#fffef9;border-color:#d3c5b1;border-radius:0;font-family:"PingFang SC","Microsoft YaHei",sans-serif}
input:focus,textarea:focus,select:focus{border-color:#5c3d78;box-shadow:0 0 0 2px #e3d9e9}
.out{background:#fbf7ef;border-color:#d9ccb9;color:#28213a;border-radius:0}
h2{color:#5c3d78}


/* mobile-32 */

@media(max-width:760px){
  main{grid-template-columns:1fr!important}
  aside{border-right:0!important;border-bottom:1px solid #d9ccb9;width:auto!important}
  section{padding:16px!important}
  .row{flex-wrap:wrap!important}
  .row>div{min-width:100%!important}
  h1{font-size:30px!important}
  .route{grid-template-columns:1fr!important}
  button{min-height:48px}
  pre{overflow-x:auto}
}

/* mobile-height */
@media(max-width:760px){main{min-height:auto!important}aside{min-height:0!important}}

/* mobile-sticky-cta */
.mobile-cta{display:none}
@media(max-width:760px){
  body{padding-bottom:88px}
  .route{grid-template-columns:repeat(3,minmax(0,1fr))!important}
  .route span{padding:8px 8px!important;font-size:11px!important;line-height:1.35!important}
  .route b{font-size:9px!important;margin-bottom:1px!important}
  .mobile-cta{position:fixed;left:12px;right:12px;bottom:12px;z-index:80;display:flex;
    padding:8px;border:1px solid rgba(0,0,0,.08);border-radius:12px;
    background:rgba(255,255,255,.94);backdrop-filter:blur(10px);
    box-shadow:0 10px 28px rgba(16,24,40,.18)}
  .mobile-cta button{width:100%;min-height:52px;margin:0!important;font-size:15px}
}
</style></head><body><div class="wrap">
<h1><span class="prod">译站</span>这一段，术语译对了吗 <span id="st" class="badge"></span></h1>
<p class="sub">给反复翻产品帮助文档的小团队：按段对齐，锁定项目词表、数字、链接和变量；改一次术语，先看受影响的段落，再决定同步。</p>
<div class="tabs"><div class="tab on" data-t="tr">翻译</div><div class="tab" data-t="term">术语表</div></div>


  <div class="route" aria-label="任务步骤"><span><b>01</b>贴原文分段</span><span><b>02</b>锁词表与变量</span><span><b>03</b>导出双语稿</span></div>
<div class="card" id="p-tr">
  <div class="row"><div><label>源语言</label><select id="src"><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option></select></div>
  <div><label>目标语言</label><select id="dst"><option value="en">英文</option><option value="zh">中文</option><option value="ja">日文</option></select></div></div>
  <label>原文(粘贴后直接翻,不必先入库)</label><textarea id="txt"></textarea>
  <div style="margin-top:12px"><button id="btnTr">翻译</button></div>
  <div class="out" id="trOut"></div>
</div>

<div class="card" id="p-term" style="display:none">
  <div class="row"><div><label>中文</label><input id="tZh"></div><div><label>英文</label><input id="tEn"></div></div>
  <label>备注(可选)</label><input id="tNote">
  <div style="margin-top:12px"><button id="btnTerm">加入术语表</button></div>
  <div class="list" id="terms" style="margin-top:12px"></div>
</div>
</div>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function loading(btn,on){if(on){btn.dataset.label=btn.dataset.label||btn.textContent.trim();btn.disabled=true;btn.textContent='处理中…';}else{btn.disabled=false;btn.textContent=btn.dataset.label||btn.textContent;}}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));['tr','term'].forEach(k=>$('p-'+k).style.display=k===t.dataset.t?'block':'none');});
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const j=await r.json();if(!r.ok)throw new Error(j.error||('HTTP '+r.status));return j;}
async function loadTerms(){const t=await api('/api/terms');
 $('terms').innerHTML=t.length?t.map(x=>`<div>[${x.id}] <b>${esc(x.zh)}</b> = ${esc(x.en)} ${x.note?'<span style="color:#6b7680">#'+esc(x.note)+'</span>':''}</div>`).join(''):'<div>术语表还是空的</div>';}
$('btnTr').onclick=async()=>{const btn=$('btnTr');loading(btn,true);
 try{const r=await api('/api/translate',{text:$('txt').value,src:$('src').value,dst:$('dst').value});
  let head=(r.offline?'【离线模式】':'')+(r.checks||[]).join(' · ')+'\\n\\n';$('trOut').textContent=head+r.output;}
 catch(e){$('trOut').textContent='❌ '+e.message;}finally{loading(btn,false);}};
$('btnTerm').onclick=async()=>{const btn=$('btnTerm');loading(btn,true);
 try{await api('/api/terms',{zh:$('tZh').value,en:$('tEn').value,note:$('tNote').value});$('tZh').value=$('tEn').value=$('tNote').value='';await loadTerms();}
 catch(e){alert(e.message);}finally{loading(btn,false);}};
(async()=>{try{const s=await api('/api/status');const b=$('st');b.textContent=s.mock?'离线模式':'模型模式';b.style.background=s.mock?'#fdecd6':'#dcefe3';b.style.color=s.mock?'#8a4a12':'#245c31';}catch(e){}await loadTerms();})();
</script>
<script>
(function(){
  var want = "翻译";
  function norm(t){ return String(t||'').replace(/\s+/g,''); }
  var all=[].slice.call(document.querySelectorAll('button'));
  var src=null, fallback=null;
  for(var i=0;i<all.length;i++){
    var b=all[i];
    if(b.offsetParent===null||b.disabled) continue;
    if(!fallback) fallback=b;
    if(norm(b.textContent).indexOf(norm(want))>=0){ src=b; break; }
  }
  if(!src) src=fallback;
  if(!src) return;
  var bar=document.createElement('div'); bar.className='mobile-cta';
  var btn=src.cloneNode(true); btn.removeAttribute('id'); btn.type='button';
  btn.addEventListener('click',function(e){e.preventDefault(); src.click();});
  bar.appendChild(btn); document.body.appendChild(bar);
})();
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    db: Database
    cfg: dict
    force_mock: bool

    def log_message(self, fmt, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        for enc in ("utf-8", "gbk"):
            try:
                return json.loads(raw.decode(enc))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/status":
            cfg = {**llm.default_config(), **self.cfg}
            self._json({"mock": self.force_mock or not cfg.get("api_key"), "model": cfg.get("model")})
        elif path == "/api/terms":
            self._json(self.db.list_terms())
        elif path == "/api/docs":
            self._json(self.db.list_docs())
        elif path == "/api/doc":
            q = parse_qs(urlparse(self.path).query)
            d = self.db.get_doc(q.get("id", ["0"])[0])
            self._json(d or {"error": "译稿不存在"}, 200 if d else 404)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json()
        if path == "/api/terms":
            zh, en = str(data.get("zh", "")).strip(), str(data.get("en", "")).strip()
            if not zh or not en:
                self._json({"error": "中文与英文都不能为空"}, 400)
                return
            tid = self.db.add_term(zh, en, str(data.get("note", "")))
            self._json({"id": tid})
            return
        if path == "/api/translate":
            text = str(data.get("text", "")).strip()
            if not text:
                self._json({"error": "原文不能为空"}, 400)
                return
            src = str(data.get("src", "zh"))
            dst = str(data.get("dst", "en"))
            if src == dst:
                self._json({"error": "源语言与目标语言相同"}, 400)
                return
            did = self.db.add_doc(src, dst, text)
            d = self.db.get_doc(did)
            try:
                r = agent.translate(d, self.db.list_terms(), config=self.cfg, force_mock=self.force_mock)
            except Exception as e:  # noqa: BLE001
                self._json({"error": str(e)}, 502)
                return
            if r.get("output") and not r.get("rejected"):
                self.db.update_output(did, r["output"])
            r["doc_id"] = did
            self._json(r)
            return
        self._json({"error": "not found"}, 404)


def _make_handler(db: Database, cfg: dict, force_mock: bool):
    class Handler(_Handler):
        pass

    Handler.db, Handler.cfg, Handler.force_mock = db, cfg, force_mock
    return Handler


def serve(host: str = "127.0.0.1", port: int = 8000, db_path: str | None = None, force_mock: bool = False):
    db = Database(db_path or os.environ.get("YIZHAN_DB"))
    httpd = ThreadingHTTPServer((host, port), _make_handler(db, llm.default_config(), force_mock))
    print(f"🌐 译站已启动  http://{host}:{httpd.server_address[1]}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        db.close()


if __name__ == "__main__":
    serve()
