from __future__ import annotations

import asyncio
import csv
import io
import json
import zipfile
import os
import secrets
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, Response, g, jsonify, render_template, request, send_file, session

from .cipher import ALPHABET_VERSION, encode_exact, group_345_rtl, normal_hebrew_view
from .crypto import derive_key, decrypt_json, decrypt_text, encrypt_json, encrypt_text, make_verifier, password_matches
from .gematria import breakdown, factorization_text, hebrew_numeral, hebrew_words, method_results, mispar_gadol, reduction_chain
from .hebrew_lexicon import HebrewLexicon, normalize_hebrew, strip_hebrew_marks
from .observatory import HOUSE_SYSTEMS, SIDEREAL_MODES, calculate_chart, format_chart
from .ollama_client import CHAT_MODEL, EMBED_INDEX_VERSION, EMBED_MODEL, REFERENCE_MODEL, chat as ollama_chat, embed as ollama_embed
from .storage import Store
from .torahcalc_reference import TorahCalcReference
from .parashah import weekly_parashah
from .research import analysis_record, enriched_methods, save_analysis, save_parashah_analysis, save_word_study
from .sefaria_online import SefariaClient, SefariaError, manuscript_image_urls, version_text

HOST = os.getenv("QUARRIES_HOST", "127.0.0.1")
PORT = int(os.getenv("QUARRIES_PORT", "8787"))
OPEN_BROWSER = os.getenv("QUARRIES_OPEN_BROWSER", "1").lower() not in {"0", "false", "no", "off"}
DEFAULT_AUTO_LOCK_SECONDS = 600
MAX_RAG_CHUNKS = 6

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.secret_key = secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")

@app.after_request
def quarries_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Quarries-Version"] = "0.10.7"
    return response

@app.get("/api/version")
def api_version():
    return jsonify(ok=True, version="0.10.7")


# Keys never go into cookies. They live only in process memory and are indexed by
# a random browser session id. Closing/restarting Quarries destroys them.
KEYRING: dict[str, dict] = {}
KEYRING_LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def chunk_text(text: str) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    chunks, current = [], []
    for word in words:
        current.append(word)
        if len(current) >= 180:
            chunks.append(" ".join(current)); current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a) ** .5; nb = sum(y*y for y in b) ** .5
    return dot/(na*nb) if na and nb else 0.0


def get_store() -> Store:
    if "store" not in g:
        g.store = Store()
    return g.store


@app.teardown_appcontext
def close_store(_exc=None):
    store = g.pop("store", None)
    if store:
        store.close()


def sid() -> str:
    if "sid" not in session:
        session["sid"] = secrets.token_urlsafe(24)
    return session["sid"]


def state(create=True) -> dict | None:
    s = sid()
    with KEYRING_LOCK:
        if create and s not in KEYRING:
            KEYRING[s] = {"app": None, "archive": None, "chat": None, "last": time.monotonic(), "reference": None}
        return KEYRING.get(s)


def touch() -> None:
    st = state()
    st["last"] = time.monotonic()


def seal_all() -> None:
    st = state()
    st.update({"app": None, "archive": None, "chat": None, "reference": None, "last": time.monotonic()})


def pref_auto_lock() -> int:
    try: return int(get_store().get_preference("auto_lock_seconds", str(DEFAULT_AUTO_LOCK_SECONDS)))
    except Exception: return DEFAULT_AUTO_LOCK_SECONDS


def enforce_auto_lock() -> None:
    st = state()
    if st.get("app") and time.monotonic() - st.get("last", 0) >= pref_auto_lock():
        seal_all()


@app.before_request
def before_request():
    enforce_auto_lock()
    if request.endpoint not in {"static"}:
        touch()


def auth_key(role: str, password: str) -> bytes | None:
    rec = get_store().auth_record(role)
    if rec is None: return None
    try:
        key = derive_key(password, rec["salt"])
        return key if password_matches(key, rec["verifier"]) else None
    except Exception:
        return None


def require_app():
    if not state().get("app"):
        return jsonify(ok=False, error="Application gate is locked."), 401


def require_key(name: str):
    base = require_app()
    if base: return base
    if not state().get(name):
        return jsonify(ok=False, error=f"{name.title()} is locked."), 401


def json_row(row):
    return {k: row[k] for k in row.keys()}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    store = get_store(); st = state()
    return jsonify(
        ok=True,
        initialized=store.initialized(),
        app_open=bool(st.get("app")), archive_open=bool(st.get("archive")), watcher_open=bool(st.get("chat")),
        auto_lock_seconds=pref_auto_lock(),
        models={"watcher": CHAT_MODEL, "reference": REFERENCE_MODEL, "embedding": EMBED_MODEL},
    )


@app.post("/api/setup")
def setup():
    store = get_store()
    if store.initialized(): return jsonify(ok=False,error="Quarries is already initialized."),400
    data=request.get_json(force=True)
    pairs=(("app",data.get("app"),data.get("app_confirm")),("archive",data.get("archive"),data.get("archive_confirm")),("chat",data.get("chat"),data.get("chat_confirm")))
    for role,a,b in pairs:
        if not a or len(a)<8: return jsonify(ok=False,error=f"{role.title()} password must contain at least 8 characters."),400
        if a!=b: return jsonify(ok=False,error=f"{role.title()} passwords do not match."),400
    for role,password,_ in pairs:
        salt=os.urandom(16); key=derive_key(password,salt); store.set_password(role,salt,make_verifier(key))
    state()["app"]=auth_key("app",pairs[0][1])
    return jsonify(ok=True)


@app.post("/api/login")
def login():
    password=request.get_json(force=True).get("password","")
    key=auth_key("app",password)
    if key is None: return jsonify(ok=False,error="The Gate remains sealed."),401
    st=state(); st.update({"app":key,"archive":None,"chat":None,"reference":None})
    return jsonify(ok=True)


@app.post("/api/unlock/<role>")
def unlock(role):
    if role not in ("archive","chat"): return jsonify(ok=False,error="Unknown gate."),404
    if require_app(): return require_app()
    password=request.get_json(force=True).get("password","")
    key=auth_key(role,password)
    if key is None: return jsonify(ok=False,error=f"The {role.title()} remains sealed."),401
    state()[role]=key
    return jsonify(ok=True)


@app.post("/api/lock-all")
def lock_all():
    seal_all(); return jsonify(ok=True)


# ---------------- Archive ----------------
@app.get("/api/archive/entries")
def archive_entries():
    denied=require_key("archive")
    if denied:return denied
    key=state()["archive"]; q=request.args.get("q","").lower().strip(); out=[]
    for row in get_store().list_entries():
        try:
            title=decrypt_text(key,row["title"],b"journal-title"); english=decrypt_text(key,row["english"],b"journal-english")
        except Exception: continue
        if q and q not in (title+"\n"+english).lower(): continue
        out.append({"id":row["id"],"title":title,"preview":" ".join(english.split())[:90],"updated_at":row["updated_at"]})
    return jsonify(ok=True,entries=out)


@app.get("/api/archive/entry/<int:entry_id>")
def archive_entry(entry_id):
    denied=require_key("archive")
    if denied:return denied
    row=get_store().get_entry(entry_id)
    if not row:return jsonify(ok=False,error="Leaf not found."),404
    key=state()["archive"]; english=decrypt_text(key,row["english"],b"journal-english")
    return jsonify(ok=True,entry={"id":entry_id,"title":decrypt_text(key,row["title"],b"journal-title"),"english":english,"hebrew":encode_exact(english),"grouped":group_345_rtl(encode_exact(english)).lstrip("\u200f"),"updated_at":row["updated_at"]})


@app.post("/api/archive/encode")
def archive_encode():
    denied=require_key("archive")
    if denied:return denied
    text=request.get_json(force=True).get("text","")
    return jsonify(ok=True,hebrew=encode_exact(text),grouped=group_345_rtl(encode_exact(text)).lstrip("\u200f"))


async def _index_entry(store: Store, key: bytes, entry_id: int, english: str) -> int:
    packed=[]; last_vector=[]
    for i,chunk in enumerate(chunk_text(english)):
        try: vector=await ollama_embed(chunk)
        except Exception: return 0
        last_vector=vector
        packed.append((i,encrypt_text(key,chunk,b"rag-chunk-content"),encrypt_json(key,vector,b"rag-chunk-vector")))
    if packed:
        store.replace_embedding_chunks(entry_id,packed,now_iso(),EMBED_MODEL,len(last_vector),EMBED_INDEX_VERSION)
    return len(packed)


@app.post("/api/archive/save")
def archive_save():
    denied=require_key("archive")
    if denied:return denied
    d=request.get_json(force=True); title=(d.get("title") or "Untitled Leaf").strip(); english=d.get("english","")
    if not english.strip():return jsonify(ok=False,error="Nothing was preserved."),400
    key=state()["archive"]; store=get_store(); now=now_iso(); enc=encode_exact(english); grp=group_345_rtl(enc)
    blobs=(encrypt_text(key,title,b"journal-title"),encrypt_text(key,english,b"journal-english"),encrypt_text(key,enc,b"journal-encoded"),encrypt_text(key,grp,b"journal-grouped"))
    eid=d.get("id")
    if eid:
        store.update_entry(int(eid),now,*blobs,None,ALPHABET_VERSION); eid=int(eid)
    else:
        eid=store.add_entry(now,*blobs,None,ALPHABET_VERSION)
    indexed=asyncio.run(_index_entry(store,key,eid,english))
    return jsonify(ok=True,id=eid,indexed=indexed,message=f"The Archive remembers. {'Indexed '+str(indexed)+' chunks.' if indexed else 'Saved without embeddings.'}")


@app.delete("/api/archive/entry/<int:entry_id>")
def archive_delete(entry_id):
    denied=require_key("archive")
    if denied:return denied
    get_store().delete_entry(entry_id); return jsonify(ok=True)


@app.post("/api/archive/reindex")
def archive_reindex():
    denied=require_key("archive")
    if denied:return denied
    store=get_store(); key=state()["archive"]; rows=store.entries_needing_index(EMBED_MODEL,EMBED_INDEX_VERSION); done=0
    for row in rows:
        try:
            english=decrypt_text(key,row["english"],b"journal-english")
            if asyncio.run(_index_entry(store,key,row["id"],english)): done+=1
        except Exception: pass
    return jsonify(ok=True,indexed=done,total=len(rows))


@app.post("/api/reference")
def set_reference():
    denied=require_app()
    if denied:return denied
    d=request.get_json(force=True); state()["reference"]={"title":d.get("title","Attached reference"),"content":d.get("content",""),"preview":d.get("preview","")}
    return jsonify(ok=True)

@app.delete("/api/reference")
def clear_reference():
    state()["reference"]=None; return jsonify(ok=True)


# ---------------- Hebrew ----------------
def hebrow(row, enrich: bool = False):
    if row is None:return None
    heb=row["hebrew"] or row["lemma"] or ""
    methods=enriched_methods(heb, include_reference=True) if enrich else method_results(heb)
    return {"id":row["id"],"strong_id":row["strong_id"],"entry_no":row["entry_no"],"hebrew":row["hebrew"],"lemma":row["lemma"],"pronunciation":row["pronunciation"],"transliteration":row["transliteration"],"morphology":row["morphology"],"language":row["language"],"gloss":row["gloss"],"definitions":row["definitions"],"notes":row["notes"],"mispar_gadol":mispar_gadol(heb),"breakdown":breakdown(heb),"methods":methods}

@app.get("/api/hebrew/search")
def hebrew_search():
    lex=HebrewLexicon()
    try: rows=lex.search(request.args.get("q",""),limit=80); return jsonify(ok=True,results=[hebrow(r) for r in rows])
    finally: lex.close()

@app.get("/api/hebrew/<int:word_id>")
def hebrew_detail(word_id):
    lex=HebrewLexicon()
    try:
        row=lex.get_word(word_id); data=hebrow(row, enrich=True)
        if not data:return jsonify(ok=False,error="Word not found."),404
        standard=next((m["value"] for m in data["methods"] if m["method"]=="Mispar Hechrachi"),0)
        matches=lex.gematria_matches(standard,data["gloss"] or data["definitions"] or "",limit=8) if standard else []
        data["same_value"]=[hebrow(r) for r in matches if r["id"]!=word_id]
        return jsonify(ok=True,word=data)
    finally:lex.close()

@app.get("/api/hebrew/saved")
def hebrew_saved():
    lex=HebrewLexicon(); out=[]
    try:
        for x in get_store().list_saved_hebrew_words():
            r=lex.get_word(x["word_id"])
            if r:
                d=hebrow(r); d["saved_at"]=x["saved_at"]; out.append(d)
        return jsonify(ok=True,results=out)
    finally:lex.close()

@app.post("/api/hebrew/saved/<int:word_id>")
def hebrew_save_word(word_id): get_store().save_hebrew_word(word_id,now_iso()); return jsonify(ok=True)
@app.delete("/api/hebrew/saved/<int:word_id>")
def hebrew_remove_word(word_id): get_store().remove_hebrew_word(word_id); return jsonify(ok=True)

@app.get("/api/hebrew/export")
def hebrew_export():
    lex=HebrewLexicon(); sio=io.StringIO(); w=csv.writer(sio)
    method_names=[m["method"] for m in method_results("אב")]
    w.writerow(["Strong's","Hebrew","Lemma","Transliteration","Pronunciation","Morphology","Language","Gloss","Definitions","Notes",*method_names,"Saved At"])
    try:
        for x in get_store().list_saved_hebrew_words():
            r=lex.get_word(x["word_id"])
            if r:
                heb=r["hebrew"] or r["lemma"] or ""; values={m["method"]:m["value"] for m in method_results(heb)}
                w.writerow([r["strong_id"],r["hebrew"],r["lemma"],r["transliteration"],r["pronunciation"],r["morphology"],r["language"],r["gloss"],r["definitions"],r["notes"],*[values.get(n,"") for n in method_names],x["saved_at"]])
    finally:lex.close()
    return Response(sio.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=quarries-hebrew-study-all-gematria.csv"})

@app.post("/api/gematria/calculate")
def gematria_calculate():
    text=request.get_json(force=True).get("text","")
    return jsonify(ok=True,text=text,mispar_gadol=mispar_gadol(text),breakdown=breakdown(text),methods=enriched_methods(text, include_reference=True))

@app.post("/api/gematria/batch")
def gematria_batch():
    d=request.get_json(force=True) or {}; texts=d.get("texts") or []
    if isinstance(texts,str): texts=[x.strip() for x in texts.splitlines() if x.strip()]
    texts=texts[:1000]
    results=[]; collisions={}
    for text in texts:
        methods=enriched_methods(text, include_reference=bool(d.get("include_reference",True)))
        results.append({"text":text,"methods":methods})
        for m in methods:
            collisions.setdefault(str(m["value"]),[]).append({"text":text,"method":m["method"]})
    collisions={k:v for k,v in collisions.items() if len(v)>1}
    return jsonify(ok=True,count=len(results),results=results,collisions=collisions)

@app.post("/api/gematria/extract")
def gematria_extract():
    d=request.get_json(force=True) or {}; raw=d.get("text","")
    words=[]; seen=set()
    for word in hebrew_words(raw):
        if word not in seen:
            seen.add(word); words.append(word)
    words=words[:1000]
    results=[]; collisions={}
    for word in words:
        methods=enriched_methods(word, include_reference=bool(d.get("include_reference",True)))
        results.append({"text":word,"methods":methods})
        for m in methods:
            collisions.setdefault(str(m["value"]),[]).append({"text":word,"method":m["method"]})
    collisions={k:v for k,v in collisions.items() if len(v)>1}
    return jsonify(ok=True,count=len(results),results=results,collisions=collisions)

@app.post("/api/gematria/analyze-numbers")
def gematria_analyze_numbers():
    d=request.get_json(force=True) or {}; nums=d.get("numbers") or []
    if isinstance(nums,(str,int)): nums=[nums]
    out=[]
    ref=TorahCalcReference()
    try:
        for raw in nums[:1000]:
            try:n=int(raw)
            except (TypeError,ValueError):continue
            out.append({"value":n,"hebrew_numeral":hebrew_numeral(n),"factorization":factorization_text(n),"reduction_chain":reduction_chain(n),"reference_hits":[dict(r) for r in ref.lookup_value(n)]})
    finally: ref.close()
    return jsonify(ok=True,results=out)

@app.post("/api/gematria/save")
def gematria_save():
    d=request.get_json(force=True) or {}; text=d.get("text","").strip()
    if not text:return jsonify(ok=False,error="Hebrew text is required."),400
    rec,path=save_analysis(text,d.get("source") or {"type":"manual"})
    return jsonify(ok=True,path=str(path),record=rec)

@app.post("/api/gematria/export")
def gematria_export():
    text=request.get_json(force=True).get("text",""); sio=io.StringIO(); w=csv.writer(sio); w.writerow(["Method","Hebrew Name","Value","Factorization","Reduction","Rule","Transformed","Reference PDF Pages","Reference Entries"])
    for x in enriched_methods(text,include_reference=True):
        refs=x.get("reference_hits",[]); w.writerow([x["method"],x["hebrew_name"],x["value"],x["factorization"]," > ".join(map(str,x["reduction_chain"])),x["rule"],x.get("transformed",""),"; ".join(str(r["source_page"]) for r in refs)," | ".join((r["body"] or "").replace("\n"," ") for r in refs)])
    return Response(sio.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=quarries-gematria-methods.csv"})



# ---------------- Tanakh reader / fuzzy word study ----------------
@app.get("/api/tanakh/books")
def tanakh_books():
    lex=HebrewLexicon()
    try:
        books=[{"book_code":r["book_code"],"book":r["book"],"chapters":r["chapters"],"verses":r["verses"]} for r in lex.books()]
        return jsonify(ok=True,books=books)
    finally:lex.close()

@app.get("/api/tanakh/chapters/<book_code>")
def tanakh_chapters(book_code):
    lex=HebrewLexicon()
    try:return jsonify(ok=True,book_code=book_code,chapters=lex.chapters(book_code))
    finally:lex.close()

@app.get("/api/tanakh/chapter/<book_code>/<int:chapter>")
def tanakh_chapter(book_code,chapter):
    lex=HebrewLexicon()
    try:
        rows=lex.chapter(book_code,chapter)
        return jsonify(ok=True,book_code=book_code,chapter=chapter,verses=[dict(r) for r in rows])
    finally:lex.close()

@app.post("/api/tanakh/word-study")
def tanakh_word_study():
    d=request.get_json(force=True) or {}
    surface=(d.get("word") or "").strip(); verse_ref=(d.get("reference") or "").strip()
    if not surface:return jsonify(ok=False,error="Hebrew word is required."),400
    lex=HebrewLexicon()
    try:
        ranked=lex.resolve_surface(surface,limit=5)
        candidates=[]
        for score,row,matched_form in ranked:
            item=hebrow(row,enrich=False)
            item["confidence"]=round(max(0.0,min(100.0,score)),1)
            item["matched_form"]=matched_form
            candidates.append(item)
        best_row=ranked[0][1] if ranked else None
        lemma=(best_row["lemma"] or best_row["hebrew"] or "") if best_row else ""
        surface_unpointed=normalize_hebrew(surface)
        surface_calc=surface_unpointed.replace("/","")
        lemma_unpointed=normalize_hebrew(lemma) if lemma else ""
        lemma_calc=lemma_unpointed.replace("/","")
        surface_methods=enriched_methods(surface_calc,include_reference=True)
        lemma_methods=enriched_methods(lemma_calc,include_reference=True) if lemma_calc else []
        occurrence_term=lemma_calc or surface_calc
        occurrences=[]
        for r in lex.occurrences(occurrence_term,limit=24):
            item=dict(r)
            item["hebrew_unpointed"]=normalize_hebrew(item.get("hebrew") or "")
            item["match_term"]=occurrence_term
            item["match_kind"]="same normalized consonantal token"
            occurrences.append(item)
        return jsonify(ok=True,
                       surface=surface,
                       surface_pointed=surface,
                       surface_unpointed=surface_unpointed,
                       surface_normalized=surface_calc,
                       lemma_pointed=lemma,
                       lemma_unpointed=lemma_unpointed,
                       lemma_normalized=lemma_calc,
                       vowel_removal={
                           "surface_original": surface,
                           "surface_without_marks": surface_unpointed,
                           "surface_gematria_input": surface_calc,
                           "lemma_original": lemma,
                           "lemma_without_marks": lemma_unpointed,
                           "lemma_gematria_input": lemma_calc,
                           "note": "Hebrew vowel points and cantillation marks are removed before Gematria calculation."
                       },
                       reference=verse_ref,
                       candidates=candidates,best=candidates[0] if candidates else None,
                       surface_methods=surface_methods,lemma_methods=lemma_methods,occurrences=occurrences)
    finally:lex.close()

@app.post("/api/research/word-study")
def research_word_study():
    d=request.get_json(force=True) or {}
    if not (d.get("surface") or "").strip():return jsonify(ok=False,error="Word study is empty."),400
    path=save_word_study(d)
    return jsonify(ok=True,path=str(path))

# ---------------- Sefaria online research ----------------
def _sefaria_error(exc):
    return jsonify(ok=False,error=str(exc),online=True),502

@app.get("/api/sefaria/text")
def sefaria_text():
    tref=(request.args.get("ref") or "").strip()
    try:
        payload=SefariaClient().text(tref)
        he=version_text(payload,"hebrew"); en=version_text(payload,"english")
        n=max(len(he),len(en))
        segments=[{"index":i+1,"hebrew":he[i] if i<len(he) else "","english":en[i] if i<len(en) else ""} for i in range(n)]
        return jsonify(ok=True,reference=tref,segments=segments,raw=payload)
    except SefariaError as exc:return _sefaria_error(exc)

@app.get("/api/sefaria/calendars")
def sefaria_calendars():
    try:
        y=request.args.get("year",type=int); m=request.args.get("month",type=int); d=request.args.get("day",type=int)
        return jsonify(ok=True,calendar=SefariaClient().calendars(y,m,d,1))
    except SefariaError as exc:return _sefaria_error(exc)

@app.get("/api/sefaria/topics")
def sefaria_topics():
    try:return jsonify(ok=True,results=SefariaClient().topics(request.args.get("q",""),request.args.get("limit",30,type=int)))
    except SefariaError as exc:return _sefaria_error(exc)

@app.get("/api/sefaria/topic/<slug>")
def sefaria_topic(slug):
    try:return jsonify(ok=True,topic=SefariaClient().topic(slug))
    except SefariaError as exc:return _sefaria_error(exc)

@app.get("/api/sefaria/related")
def sefaria_related():
    try:return jsonify(ok=True,related=SefariaClient().related(request.args.get("ref","")))
    except SefariaError as exc:return _sefaria_error(exc)

@app.get("/api/sefaria/manuscripts")
def sefaria_manuscripts():
    try:
        data=SefariaClient().manuscripts(request.args.get("ref",""))
        return jsonify(ok=True,manuscripts=data,image_urls=manuscript_image_urls(data))
    except SefariaError as exc:return _sefaria_error(exc)

@app.post("/api/sefaria/export")
def sefaria_export():
    d=request.get_json(force=True) or {}; tref=(d.get("reference") or "").strip()
    if not tref:return jsonify(ok=False,error="Reference is required."),400
    analysis=d.get("analysis") or {}; include_images=bool(d.get("include_images",True))
    try:
        client=SefariaClient(); text=client.text(tref); manuscripts=client.manuscripts(tref) if include_images else []
    except SefariaError as exc:return _sefaria_error(exc)
    he=version_text(text,"hebrew"); en=version_text(text,"english")
    report=[f"# Quarries Sefaria Study — {tref}","",f"Source: Sefaria · exported {now_iso()}",""]
    for i in range(max(len(he),len(en))):
        report += [f"## Segment {i+1}", he[i] if i<len(he) else "", "", en[i] if i<len(en) else "", ""]
    if analysis:
        report += ["## Quarries Analysis","","```json",json.dumps(analysis,ensure_ascii=False,indent=2),"```",""]
    manifest={"reference":tref,"exported_at":now_iso(),"source":"Sefaria","text":text,"analysis":analysis,"manuscripts":manuscripts}
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("analysis.md","\n".join(report)); z.writestr("analysis.json",json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr("manuscripts.json",json.dumps(manuscripts,ensure_ascii=False,indent=2))
        if include_images:
            import httpx
            for idx,url in enumerate(manuscript_image_urls(manuscripts)[:20],1):
                try:
                    r=httpx.get(url,timeout=20,follow_redirects=True,headers={"User-Agent":"Quarries/0.10.7"}); r.raise_for_status()
                    ctype=r.headers.get("content-type","").lower(); ext=".jpg"
                    if "png" in ctype:ext=".png"
                    elif "webp" in ctype:ext=".webp"
                    elif "jpeg" in ctype or "jpg" in ctype:ext=".jpg"
                    z.writestr(f"manuscripts/manuscript-{idx:02d}{ext}",r.content)
                except Exception as exc:
                    z.writestr(f"manuscripts/manuscript-{idx:02d}-ERROR.txt",f"{url}\n{exc}\n")
    bio.seek(0)
    safe="".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in tref)[:80] or "sefaria-study"
    return send_file(bio,mimetype="application/zip",as_attachment=True,download_name=f"quarries-{safe}.zip")

# ---------------- Weekly Parashah ----------------
@app.get("/api/parashah/week")
def parashah_week():
    raw = (request.args.get("date") or "").strip()
    on_date = None
    if raw:
        try:
            on_date = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return jsonify(ok=False, error="date must use YYYY-MM-DD"), 400
    return jsonify(ok=True, parashah=weekly_parashah(on_date))

@app.post("/api/parashah/analyze")
def parashah_analyze():
    d=request.get_json(force=True) or {}
    p=d.get("parashah") or weekly_parashah(); text=d.get("text") or p.get("hebrew_text") or ""
    words=[]; seen=set()
    for word in hebrew_words(text):
        if word not in seen:
            seen.add(word); words.append(word)
    limit=max(1,min(int(d.get("limit",500)),1000)); words=words[:limit]
    results=[]
    for word in words:
        results.append({"text":word,"methods":enriched_methods(word, include_reference=True)})
    payload={"saved_at":now_iso(),"parashah":p,"word_count":len(results),"results":results}
    path=save_parashah_analysis(p.get("title","parashah"),p.get("date",""),payload)
    return jsonify(ok=True,path=str(path),word_count=len(results),results=results,parashah=p)

# ---------------- Gematria Dictionary ----------------
@app.get("/api/dictionary/value/<int:value>")
def dictionary_value(value):
    ref=TorahCalcReference()
    try:
        rows=ref.lookup_value(value); return jsonify(ok=True,results=[dict(r) | {"factorization":factorization_text(value),"reduction_chain":reduction_chain(value)} for r in rows])
    finally:ref.close()

@app.get("/api/dictionary/search")
def dictionary_search():
    ref=TorahCalcReference()
    try:return jsonify(ok=True,results=[dict(r) | {"factorization":factorization_text(int(r["value"])),"reduction_chain":reduction_chain(int(r["value"]))} for r in ref.search_text(request.args.get("q",""),limit=60)])
    finally:ref.close()

@app.get("/api/dictionary/related/<int:section_id>")
def dictionary_related(section_id):
    ref=TorahCalcReference()
    try:return jsonify(ok=True,results=[dict(r) | {"score": score} for r, score in ref.related(section_id,limit=12)])
    finally:ref.close()

@app.get("/api/dictionary/methods")
def dictionary_methods():
    ref=TorahCalcReference()
    try:return jsonify(ok=True,methods=[dict(r) for r in ref.methods()])
    finally:ref.close()


# ---------------- Observatory ----------------
@app.post("/api/observatory")
def observatory():
    d=request.get_json(force=True)
    try:
        tz_name=d.get("timezone","America/New_York"); tz=ZoneInfo(tz_name)
        mode=d.get("chart_mode","Current")
        if mode=="Natal": raw=f"{d.get('birth_date','')} {d.get('birth_time','')}"
        else: raw=d.get("datetime","")
        dt=datetime.strptime(raw.strip(),"%Y-%m-%d %H:%M").replace(tzinfo=tz)
        chart=calculate_chart(local_dt=dt,latitude=float(d.get("latitude")),longitude=float(d.get("longitude")),timezone_name=tz_name,zodiac_mode=d.get("zodiac","Tropical"),sidereal_mode=d.get("sidereal","Lahiri"),house_system=d.get("houses","Placidus"))
        return jsonify(ok=True,report=format_chart(chart))
    except Exception as e:return jsonify(ok=False,error=str(e)),400


# ---------------- Watcher ----------------
def _messages(session_id:int,key:bytes):
    out=[]
    for row in get_store().list_chat_messages(session_id):
        try:out.append({"role":row["role"],"content":decrypt_text(key,row["content"],b"chat-message"),"created_at":row["created_at"]})
        except Exception:pass
    return out

@app.get("/api/watcher/sessions")
def watcher_sessions():
    denied=require_key("chat")
    if denied:return denied
    key=state()["chat"]; out=[]
    for r in get_store().list_chat_sessions():
        try:title=decrypt_text(key,r["title"],b"chat-title")
        except Exception:title="Encrypted conversation"
        out.append({"id":r["id"],"title":title,"updated_at":r["updated_at"]})
    return jsonify(ok=True,sessions=out)

@app.post("/api/watcher/sessions")
def watcher_new_session():
    denied=require_key("chat")
    if denied:return denied
    key=state()["chat"]; now=now_iso(); i=get_store().add_chat_session(now,encrypt_text(key,"New Conversation",b"chat-title")); return jsonify(ok=True,id=i)

@app.get("/api/watcher/session/<int:session_id>")
def watcher_session(session_id):
    denied=require_key("chat")
    if denied:return denied
    return jsonify(ok=True,messages=_messages(session_id,state()["chat"]))

@app.delete("/api/watcher/session/<int:session_id>")
def watcher_delete_session(session_id):
    denied=require_key("chat")
    if denied:return denied
    get_store().delete_chat_session(session_id);return jsonify(ok=True)


async def _memory_context(question:str, mode:str, archive_key:bytes|None, reference:dict|None) -> tuple[str,str]:
    parts=[]; labels=[]
    if mode in ("current","current_similar") and reference and reference.get("content"):
        parts.append("REFERENCE INTERPRETATION CONTRACT\nThe attached Quarries fields are immutable. Interpret them; do not recalculate or replace signs, houses, dignities, aspects, elements, modalities, polarity, glosses, or gematria from model memory. If discussing a supplied field, quote its supplied value exactly.\n\nREFERENCE CONTEXT — "+reference.get("title","Attached reference")+":\n"+reference["content"])
        labels.append("Reference: "+reference.get("title","Attached reference"))
    if mode in ("similar","current_similar"):
        if not archive_key:labels.append("Similar unavailable: Archive locked")
        else:
            try:
                qv=await ollama_embed(question); scored=[]
                for row in get_store().list_embedding_chunks():
                    if row["embedding_model"]!=EMBED_MODEL or row["index_version"]!=EMBED_INDEX_VERSION or int(row["embedding_dim"] or 0)!=len(qv):continue
                    try:vec=decrypt_json(archive_key,row["embedding"],b"rag-chunk-vector");scored.append((cosine(qv,vec),row))
                    except Exception:pass
                scored.sort(key=lambda p:p[0],reverse=True); count=0; used=set()
                for score,row in scored:
                    if count>=MAX_RAG_CHUNKS:break
                    try:
                        content=decrypt_text(archive_key,row["content"],b"rag-chunk-content"); title=decrypt_text(archive_key,row["title"],b"journal-title")
                        parts.append(f"RETRIEVED LEAF: {title}\nSimilarity: {score:.3f}\n{content}"); count+=1; used.add(row["entry_id"])
                    except Exception:pass
                labels.append(f"RAG: {count} chunks / {len(used)} Leaves")
            except Exception:labels.append("RAG unavailable")
    return "\n\n---\n\n".join(parts)," + ".join(labels) or "Empty Mind"

@app.post("/api/watcher/send")
def watcher_send():
    denied=require_key("chat")
    if denied:return denied
    d=request.get_json(force=True); q=(d.get("message") or "").strip(); mode=d.get("memory_mode","empty"); session_id=int(d.get("session_id") or 0)
    if not q:return jsonify(ok=False,error="Message is empty."),400
    key=state()["chat"]; store=get_store(); now=now_iso()
    if not session_id:session_id=store.add_chat_session(now,encrypt_text(key,"New Conversation",b"chat-title"))
    existing=_messages(session_id,key)
    store.add_chat_message(session_id,"user",encrypt_text(key,q,b"chat-message"),now)
    if not any(m["role"]=="user" for m in existing):store.rename_chat_session(session_id,encrypt_text(key," ".join(q.split())[:48] or "New Conversation",b"chat-title"),now)
    context,label=asyncio.run(_memory_context(q,mode,state().get("archive"),state().get("reference")))
    model=REFERENCE_MODEL if context and mode in ("current","current_similar") else None
    try:reply=asyncio.run(ollama_chat(([{"role":m["role"],"content":m["content"]} for m in existing]+[{"role":"user","content":q}])[-24:],context=context,model=model))
    except Exception:reply="The local model could not be reached. Confirm that Ollama is running and the configured models are installed."
    store.add_chat_message(session_id,"assistant",encrypt_text(key,reply,b"chat-message"),now_iso())
    return jsonify(ok=True,session_id=session_id,reply=reply,context_label=label,model=model or CHAT_MODEL)


# ---------------- Vault ----------------
@app.post("/api/preferences/auto-lock")
def auto_lock():
    denied=require_app()
    if denied:return denied
    seconds=int(request.get_json(force=True).get("seconds",DEFAULT_AUTO_LOCK_SECONDS))
    if seconds not in (60,300,600,900,1800,3600):return jsonify(ok=False,error="Unsupported auto-lock value."),400
    get_store().set_preference("auto_lock_seconds",str(seconds));return jsonify(ok=True)

@app.post("/api/vault/export")
def vault_export():
    denied=require_key("archive")
    if denied:return denied
    d=request.get_json(force=True); pw=d.get("password",""); confirm=d.get("confirm","")
    if len(pw)<8 or pw!=confirm:return jsonify(ok=False,error="Passwords must match and contain at least 8 characters."),400
    key=state()["archive"]; rows=[]
    for row in get_store().list_entries():
        english=decrypt_text(key,row["english"],b"journal-english")
        rows.append({"created_at":row["created_at"],"updated_at":row["updated_at"],"title":decrypt_text(key,row["title"],b"journal-title"),"english":english,"encoded":decrypt_text(key,row["hebrew"],b"journal-encoded") if row["hebrew"] else encode_exact(english),"alphabet_version":row["alphabet_version"] or "legacy"})
    salt=os.urandom(16); export_key=derive_key(pw,salt); payload=encrypt_json(export_key,{"version":4,"entries":rows},b"quarries-export")
    blob=b"QRYX4"+salt+payload
    return Response(blob,mimetype="application/octet-stream",headers={"Content-Disposition":f"attachment; filename=quarries-{datetime.now():%Y%m%d-%H%M%S}.qryx"})


def main():
    url=f"http://{HOST}:{PORT}"
    if OPEN_BROWSER:
        threading.Timer(.8, lambda: webbrowser.open(url)).start()
    app.run(host=HOST,port=PORT,debug=False,threaded=True,use_reloader=False)

if __name__ == "__main__":main()
