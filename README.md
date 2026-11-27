# LinkRescue

[![tests](https://github.com/Hamasa-ElShamy/linkrescue/actions/workflows/tests.yml/badge.svg)](https://github.com/Hamasa-ElShamy/linkrescue/actions/workflows/tests.yml) ![tests: 11 passing](https://img.shields.io/badge/tests-11%20passing-brightgreen) ![license: MIT](https://img.shields.io/badge/license-MIT-blue)

Save the links you collect. LinkRescue checks them, tells you which ones died, moved or changed, keeps a text copy on your computer, and points you to an Internet Archive copy when one exists.


## Worked example

Real run, with internet access (see [`demo/demo-output.txt`](demo/demo-output.txt)):

```
$ linkrescue add https://example.com/ https://docs.python.org/3/tutorial/ http://www.geocities.com/SiliconValley/ https://docs.python.org/3/no-such-page.html
1. AVAILABLE  https://example.com/
2. AVAILABLE  https://docs.python.org/3/tutorial/
3. CONTENT MOVED  http://www.geocities.com/SiliconValley/
   redirects to the home page https://www.yahoo.com/; archived copy: http://web.archive.org/web/19991009015113/http://www6.geocities.com:80/SiliconValley/
4. BROKEN  https://docs.python.org/3/no-such-page.html
   HTTP 404; no archived copy found

$ linkrescue find "classes modules"
2. The Python Tutorial ... [AVAILABLE]
   ...More on [Modules]  6.1.1. Executing [modules] as scripts ...
```

The old GeoCities link now sends you to the Yahoo home page. LinkRescue says "moved", does not save Yahoo's page as your copy, and finds the 1999 archived copy.

## Install and use

```
git clone https://github.com/Hamasa-ElShamy/linkrescue && cd linkrescue
pip install .
linkrescue add https://some.site/article     # save and check one or more links
linkrescue import bookmarks.html             # browser bookmarks export, a .txt of URLs, or a JSON list
linkrescue check                             # re-check everything (run it from cron / Task Scheduler)
linkrescue list
linkrescue find "gradient descent"           # search inside your saved copies
linkrescue diff 3                            # what changed on a PAGE CHANGED link
linkrescue accept 3                          # make the new version your reference copy
```

Statuses: `AVAILABLE`, `PAGE CHANGED` (under 90% of the text matches your saved copy), `CONTENT MOVED` (redirect), `BROKEN` (404/410, or a "not found" page returned with HTTP 200), `BLOCKED` (the site refused the check, 401/403/429: this does not mean the page is gone), `ERROR` (network, DNS, 5xx).

| System | Status |
|---|---|
| Linux | Tested (Python 3.10). Python standard library only, nothing else to install. |
| Windows / macOS | Should work, not tested. |
| Android / browser extension | Not available. |

## Limitations

- Pages that need JavaScript to show their text are saved as the (nearly empty) HTML they send. There is no browser rendering yet, so those links may show "AVAILABLE" with little or no searchable text. Pages behind a login are not reachable.
- The "main text" extraction is a simple rule (it drops navigation, sidebar, header, footer by tag and class name). It is not Trafilatura. Some sites will keep menu text or lose content.
- Only the text is saved, not images, styles or the original page. If a page dies, you have the words, not the layout.
- "PAGE CHANGED" is a text similarity number. It cannot tell a typo fix from a rewrite; use `diff`.
- Archived copies come from the Internet Archive availability lookup and need internet access to archive.org. It does not submit pages to the archive.
- It is a command line only: no extension, no window, no built-in scheduler. Use cron or Task Scheduler.
- Some sites answer automated checks with 403/429 and get `BLOCKED`.
- Existing tools do parts of this (for example ArchiveBox, Linkwarden, Wayback Machine). LinkRescue is a small local tool with no server; it is not a replacement for them.

## Related tools

[Linkwarden](https://github.com/linkwarden/linkwarden) and ArchiveBox are fuller bookmark managers and archivers (self-hosted, with page archives). LinkRescue is a small command-line tool for link health with no server, plus an archive lookup. Use those if you want full-page archives.

## Technical notes

[ARCHITECTURE.md](ARCHITECTURE.md), Arabic and English. 9 pytest tests against a local test server (`pytest`): available, 404, soft 404, redirect, blocked, dead host, changed page with kept copy, archive lookup, bookmark import. Output in [`demo/test-output.txt`](demo/test-output.txt).

## How it works

You add a link (or import a bookmarks file). LinkRescue opens the page, extracts the main text without menus and footers, and stores it in a SQLite database on your computer with FTS5 search. Each `check` opens the link again and compares it: a 404 or a "not found" page is BROKEN, and LinkRescue looks for an Internet Archive copy; a redirect to the home page is CONTENT MOVED; text that differs from your saved copy by more than 10% is PAGE CHANGED, and your older copy is kept so you can see the difference with `diff`. If a site refuses the check, the link is marked BLOCKED, not BROKEN, so you are not misled. Pages that depend on JavaScript are not read well.
