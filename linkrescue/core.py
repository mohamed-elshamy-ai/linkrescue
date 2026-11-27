"""LinkRescue core: save links, check them, keep a local text snapshot, search it."""
import difflib, hashlib, json, os, re, sqlite3, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser

UA = "LinkRescue/0.1 (+https://github.com/Hamasa-ElShamy/linkrescue)"
DB = os.environ.get("LINKRESCUE_DB") or os.path.expanduser("~/.linkrescue.db")
CHANGED_BELOW = 0.90   # similarity under this = "PAGE CHANGED"
MAX_BYTES = 2_000_000


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"}
    VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "area", "col"}
    JUNK = re.compile(r"(^|[\s_-])(nav|navigation|sidebar|sphinxsidebar|related|menu|breadcrumbs?|toc|cookie|footer|header|skip)([\s_-]|$)", re.I)

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self._in_title = [], "", False
        self.stack = []   # one flag per open element: does it start/continue a skipped region?
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag == "br":
                self.parts.append("\n")
            return
        a = dict(attrs)
        junk = tag in self.SKIP or tag not in ("html", "body", "main", "article") and bool(self.JUNK.search((a.get("class") or "") + " " + (a.get("id") or "") + " " + (a.get("role") or "")))
        self.stack.append((tag, junk))
        self.skipping += junk
        if tag == "title":
            self._in_title = True
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "div", "tr", "pre"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, j in self.stack[i:]:
                    self.skipping -= j
                del self.stack[i:]
                break

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        elif not self.skipping:
            self.parts.append(d)


def extract(html):
    p = _Text()
    p.feed(html)
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.parts))
    text = "\n".join(l.strip() for l in text.split("\n") if l.strip())
    return p.title.strip(), text


def db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS links(id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, status TEXT,
        detail TEXT, last_checked REAL, text TEXT, text_hash TEXT, added REAL, final_url TEXT, archive_url TEXT);
    CREATE TABLE IF NOT EXISTS snaps(id INTEGER PRIMARY KEY, link_id INTEGER, ts REAL, text TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(title, text, tokenize='unicode61 remove_diacritics 2');
    """)
    return c


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_BYTES)
        ctype = r.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ctype)
        enc = m.group(1) if m else "utf-8"
        return r.geturl(), ctype, raw.decode(enc, "replace")


def wayback(url, timeout=15):
    """Closest Internet Archive copy, or None. Needs internet access to archive.org."""
    api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": UA}), timeout=timeout) as r:
            d = json.load(r)
        c = d.get("archived_snapshots", {}).get("closest")
        return c["url"] if c and c.get("available") else None
    except Exception:
        return None


def classify(url, old_text, wb=wayback):
    """-> (status, detail, title, text, final_url)"""
    try:
        final, ctype, body = fetch(url)
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "BROKEN", f"HTTP {e.code}", "", "", url
        if e.code in (401, 403, 429, 999):
            return "BLOCKED", f"HTTP {e.code}: the site refused the check; this does not mean the page is gone", "", "", url
        return "ERROR", f"HTTP {e.code}", "", "", url
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {e}", "", "", url
    if "html" in ctype or "text" in ctype or not ctype:
        title, text = extract(body)
    else:
        return "AVAILABLE", f"non-text content ({ctype}); not snapshotted", "", "", final
    moved = urllib.parse.urlsplit(final)._replace(fragment="").geturl().rstrip("/") != \
        urllib.parse.urlsplit(url)._replace(fragment="").geturl().rstrip("/")
    if len(text) < 80 and re.search(r"(not found|404|no longer available|has been removed|page doesn.t exist)", (title + " " + text).lower()):
        return "BROKEN", "soft 404: HTTP 200 but the page says it is gone", title, text, final
    if moved and urllib.parse.urlsplit(final).path in ("", "/") and urllib.parse.urlsplit(url).path not in ("", "/"):
        return "CONTENT MOVED", f"redirects to the home page {final}", "", "", final
    if old_text:
        ratio = difflib.SequenceMatcher(None, old_text[:6000], text[:6000], autojunk=False).ratio()
        if ratio < CHANGED_BELOW:
            return "PAGE CHANGED", f"{round((1 - ratio) * 100)}% of the text differs from your saved copy", title, text, final
    if moved:
        return "CONTENT MOVED", f"redirects to {final}", title, text, final
    if len(text) < 40:
        return "AVAILABLE", f"ok, but only {len(text)} characters of text could be read (the page may need JavaScript, so the saved copy and 'find' will be weak)", title, text, final
    return "AVAILABLE", "ok", title, text, final


def normalize_url(url):
    """Add https:// when a bare domain is given; reject anything that is not a web address."""
    u = (url or "").strip()
    if not u: raise ValueError("empty address")
    if not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        if re.match(r"[\w-]+(\.[\w-]+)+(/|$|\?|#)", u, re.U): u = "https://" + u
        else: raise ValueError(f"'{u}' is not a web address (expected something like https://example.com/page)")
    if urllib.parse.urlsplit(u).scheme not in ("http", "https") or not urllib.parse.urlsplit(u).netloc:
        raise ValueError(f"'{u}' is not an http(s) web address")
    return u


def add(url, title=None, c=None):
    c = c or db()
    url = normalize_url(url)
    now = time.time()
    c.execute("INSERT OR IGNORE INTO links(url,title,status,added) VALUES(?,?,?,?)", (url, title or "", "NEW", now))
    c.commit()
    return c.execute("SELECT id FROM links WHERE url=?", (url,)).fetchone()[0]


def check(link_id, c=None, wb=wayback):
    c = c or db()
    row = c.execute("SELECT url,title,text FROM links WHERE id=?", (link_id,)).fetchone()
    url, otitle, old = row
    status, detail, title, text, final = classify(url, old, wb)
    now = time.time()
    arch = None
    if status in ("BROKEN", "CONTENT MOVED"):
        arch = wb(url)
        if arch:
            detail += f"; archived copy: {arch}"
        elif status == "BROKEN":
            detail += "; no archived copy found"
    c.execute("UPDATE links SET status=?,detail=?,last_checked=?,final_url=?,archive_url=? WHERE id=?",
              (status, detail, now, final, arch, link_id))
    if text and status in ("AVAILABLE", "PAGE CHANGED", "CONTENT MOVED"):
        h = hashlib.sha1(text.encode()).hexdigest()
        if not old or status == "PAGE CHANGED":
            c.execute("INSERT INTO snaps(link_id,ts,text) VALUES(?,?,?)", (link_id, now, text))
        # keep the first (or user-visible) copy as the reference text, so slow drift is still noticed
        if not old:
            c.execute("UPDATE links SET text=?,text_hash=?,title=? WHERE id=?", (text, h, otitle or title, link_id))
            c.execute("DELETE FROM fts WHERE rowid=?", (link_id,))
            c.execute("INSERT INTO fts(rowid,title,text) VALUES(?,?,?)", (link_id, otitle or title, text))
        elif status == "PAGE CHANGED":
            pass  # the saved reference stays; `accept` replaces it
    c.commit()
    return status, detail


def accept(link_id, c=None):
    """Make the newest snapshot the new reference copy."""
    c = c or db()
    r = c.execute("SELECT text FROM snaps WHERE link_id=? ORDER BY id DESC LIMIT 1", (link_id,)).fetchone()
    if not r:
        return False
    t = r[0]
    c.execute("UPDATE links SET text=?,text_hash=?,status='AVAILABLE' WHERE id=?", (t, hashlib.sha1(t.encode()).hexdigest(), link_id))
    c.execute("DELETE FROM fts WHERE rowid=?", (link_id,))
    ti = c.execute("SELECT title FROM links WHERE id=?", (link_id,)).fetchone()[0]
    c.execute("INSERT INTO fts(rowid,title,text) VALUES(?,?,?)", (link_id, ti, t))
    c.commit()
    return True


def diff(link_id, c=None):
    c = c or db()
    row = c.execute("SELECT text FROM links WHERE id=?", (link_id,)).fetchone()
    if row is None: raise ValueError(f"no saved link with id {link_id}. Run `linkrescue list` to see the ids.")
    old = row[0] or ""
    r = c.execute("SELECT text FROM snaps WHERE link_id=? ORDER BY id DESC LIMIT 1", (link_id,)).fetchone()
    new = r[0] if r else ""
    return [l for l in difflib.unified_diff(old.split("\n"), new.split("\n"), "saved", "latest", lineterm="", n=0)]


def import_file(path, c=None):
    """Bookmarks HTML, a text file with one URL per line, or a JSON list."""
    c = c or db()
    try:
        with open(path, "rb") as fh: data = fh.read()
    except OSError as e:
        raise ValueError(f"cannot read '{path}': {e.strerror or e}")
    if b"\0" in data[:4096]: raise ValueError(f"'{path}' looks like a binary file. Use a browser bookmarks export (.html), a .txt with one URL per line, or a JSON list.")
    raw = data.decode("utf-8", errors="replace")
    urls = []
    if raw.lstrip().startswith("["):
        try: lst = json.loads(raw)
        except ValueError as e: raise ValueError(f"'{path}' is not valid JSON: {e}")
        urls = [(u if isinstance(u, str) else (u.get("url") if isinstance(u, dict) else None), None) for u in lst]
    else:
        pairs = re.findall(r'<a [^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', raw, re.I | re.S)
        urls = [(u, re.sub(r"<[^>]+>", "", t).strip()) for u, t in pairs] or \
               [(u, None) for u in re.findall(r"https?://[^\s<>\"']+", raw)]
    n = 0
    for u, t in urls:
        if u:
            before = c.total_changes
            try: add(u, t, c)
            except ValueError: continue
            n += c.total_changes > before
    return n


def search(q, c=None, limit=10):
    c = c or db()
    toks = re.findall(r"\w+", q, re.U)
    if not toks:
        return []
    m = " ".join(f'"{t}"' for t in toks)
    return c.execute("SELECT l.id,l.url,l.status,l.title,snippet(fts,1,'[',']','...',12) FROM fts JOIN links l ON l.id=fts.rowid "
                     "WHERE fts MATCH ? ORDER BY rank LIMIT ?", (m, limit)).fetchall()
