# LinkRescue: technical notes

- `core.py`
  - `extract()`: HTML to text with the standard `html.parser`. A stack tracks open elements; anything inside a skipped tag (`nav`, `footer`, `header`, `aside`, `form`, `script`, `style`) or an element whose class/id/role looks like navigation, sidebar, menu, breadcrumb or cookie banner is dropped.
  - `classify()`: fetches the URL with a User-Agent (15 s timeout, 2 MB cap) and decides the status. 404/410 is BROKEN. 401/403/429 is BLOCKED. Other HTTP errors and network failures are ERROR. A short page with "not found" wording at HTTP 200 is a soft 404. A redirect from a deep path to a site root is CONTENT MOVED. Otherwise the text is compared with the saved copy using `difflib.SequenceMatcher` on the first 6000 characters; below 0.90 similarity is PAGE CHANGED.
  - `check()`: for BROKEN and CONTENT MOVED it asks the Internet Archive availability API for the closest copy. The first good text is the reference copy; later changed versions go to `snaps` and the reference stays until `accept`, so slow drift is still caught.
  - `search()`: SQLite FTS5 (`unicode61`, accent folding) over the reference copy.
- `cli.py`: `add`, `import`, `check`, `list`, `find`, `diff`, `accept`.
- Data: `~/.linkrescue.db` (override with `LINKRESCUE_DB`). Tables `links`, `snaps`, `fts`.

**Decisions**: stdlib only so it installs anywhere; BLOCKED is separate from BROKEN so a bot-hostile site never gets reported as dead; a redirect to a home page is never saved as your copy; no network calls except to the link itself and archive.org.

**Limits**: no JavaScript rendering, simple text extraction, text only, no submission to the archive, no scheduler.
