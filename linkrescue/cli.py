import argparse, sys, time
from . import core


def main(argv=None):
    ap = argparse.ArgumentParser(prog="linkrescue", description="Save links, watch their health, keep a local copy.")
    s = ap.add_subparsers(dest="cmd", required=True)
    a = s.add_parser("add"); a.add_argument("urls", nargs="+")
    i = s.add_parser("import"); i.add_argument("file")
    s.add_parser("check")
    s.add_parser("list")
    f = s.add_parser("find"); f.add_argument("query", nargs="+")
    d = s.add_parser("diff"); d.add_argument("id", type=int)
    k = s.add_parser("accept"); k.add_argument("id", type=int)
    o = ap.parse_args(argv)
    c = core.db()
    if o.cmd == "add":
        for u in o.urls:
            try: u = core.normalize_url(u)
            except ValueError as e:
                print(f"skipped: {e}"); continue
            lid = core.add(u, None, c)
            st, dt = core.check(lid, c)
            print(f"{lid}. {st}  {u}\n   {dt}")
    elif o.cmd == "import":
        try: print(f"added {core.import_file(o.file, c)} new links (run `linkrescue check`)")
        except ValueError as e: sys.exit(f"linkrescue: {e}")
    elif o.cmd == "check":
        rows = c.execute("SELECT id FROM links ORDER BY id").fetchall()
        for (lid,) in rows:
            st, dt = core.check(lid, c)
            u, t = c.execute("SELECT url,title FROM links WHERE id=?", (lid,)).fetchone()
            print(f"{lid}. {t or u}\n   Status: {st}\n   {dt}")
    elif o.cmd == "list":
        for lid, u, t, st, lc in c.execute("SELECT id,url,title,status,last_checked FROM links ORDER BY id"):
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(lc)) if lc else "never"
            print(f"{lid}. [{st}] {t or u}  (checked {when})")
    elif o.cmd == "find":
        r = core.search(" ".join(o.query), c)
        if not r:
            print("No match in your saved copies.")
        for lid, u, st, t, sn in r:
            print(f"{lid}. {t or u}  [{st}]\n   {u}\n   {sn}")
    elif o.cmd == "diff":
        try: print("\n".join(core.diff(o.id, c)) or "no difference")
        except ValueError as e: sys.exit(f"linkrescue: {e}")
    elif o.cmd == "accept":
        print("accepted" if core.accept(o.id, c) else "nothing to accept")


if __name__ == "__main__":
    main()
