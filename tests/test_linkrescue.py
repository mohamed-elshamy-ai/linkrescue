import os, tempfile, threading, http.server, pytest
os.environ["LINKRESCUE_DB"] = tempfile.mktemp(suffix=".db")
from linkrescue import core

PAGES = {"/ok": "<title>Python Tutorial</title><p>Learn python loops and functions in this long tutorial about programming basics and data structures.</p>",
         "/paper": "<title>Research Paper</title><p>The model achieved ninety two percent accuracy on the benchmark dataset described in section five of this paper.</p>",
         "/soft": "<title>Not found</title><p>404 page not found</p>"}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/moved":
            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
        if self.path == "/":
            body = "<title>Home</title><p>Welcome to the home page of this site, with news and links to many other sections of it.</p>"
        elif self.path == "/blocked":
            self.send_response(403); self.end_headers(); return
        elif self.path in PAGES: body = PAGES[self.path]
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(body.encode())

@pytest.fixture(scope="module")
def srv():
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()

nowb = lambda u: None

def chk(url):
    c = core.db(); i = core.add(url, None, c); return i, core.check(i, c, nowb)[0], c

def test_available_and_searchable(srv):
    i, st, c = chk(srv + "/ok"); assert st == "AVAILABLE"
    assert core.search("loops functions", c)[0][1].endswith("/ok")

def test_broken(srv): assert chk(srv + "/gone")[1] == "BROKEN"
def test_soft404(srv): assert chk(srv + "/soft")[1] == "BROKEN"
def test_moved(srv): assert chk(srv + "/moved")[1] == "CONTENT MOVED"
def test_blocked_is_not_broken(srv): assert chk(srv + "/blocked")[1] == "BLOCKED"
def test_dead_host(): assert chk("http://127.0.0.1:1/x")[1] == "ERROR"

def test_changed_keeps_copy_and_diff(srv):
    i, st, c = chk(srv + "/paper"); assert st == "AVAILABLE"
    PAGES["/paper"] = "<title>Research Paper</title><p>Correction: the model achieved only seventy one percent accuracy after the authors fixed a data leak in the evaluation.</p>"
    assert core.check(i, c, nowb)[0] == "PAGE CHANGED"
    assert core.search("ninety", c)           # old text still searchable
    assert any("seventy" in l for l in core.diff(i, c))

def test_wayback_used_for_broken(srv):
    c = core.db(); i = core.add(srv + "/gone2", None, c)
    st, d = core.check(i, c, lambda u: "https://web.archive.org/web/1/x")
    assert st == "BROKEN" and "web.archive.org" in d

def test_import_html(tmp_path):
    p = tmp_path / "b.html"; p.write_text('<a href="https://a.example/x">A page</a><a href="https://b.example/">B</a>')
    c = core.db(); assert core.import_file(str(p), c) == 2


def test_class_on_html_tag_does_not_hide_the_page():
    from linkrescue import core
    t, x = core.extract('<html class="vector-toc-pinned client-nojs"><head><title>T</title></head><body class="menu"><p>Real article text here.</p></body></html>')
    assert t == "T" and "Real article text" in x


def test_bad_urls_rejected():
    import pytest
    from linkrescue import core
    for bad in ("", "javascript:alert(1)", "ftp://x.org", "not a url"):
        with pytest.raises(ValueError): core.normalize_url(bad)
    assert core.normalize_url("example.com/a") == "https://example.com/a"
