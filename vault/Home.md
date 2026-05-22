# Home

[[sessions/coach-memory|Coach Memory]] · [[personal/goals|Goals]] · [[personal/values|Values]] · [[personal/profile|Profile]] · [[personal/net-worth|Net Worth]] · [[personal/knowledge|Knowledge]]

---

## Today

[[personal/journal/2026/05/2026-05-22|Open today's journal →]]

---

## Net Worth

> Open [[personal/net-worth|net-worth.md]] and update the table weekly.

```dataview
TABLE net-worth AS "Net Worth", change AS "Change", notes AS "Notes"
FROM "personal"
WHERE file.name = "net-worth"
```

---

## Last 7 Journal Entries

```dataview
LIST
FROM "personal/journal"
WHERE file.name != "template" AND file.name != "_template" AND file.name != "weekly-template"
SORT file.name DESC
LIMIT 7
```

---

## Recent Weekly Reviews

```dataview
LIST
FROM "personal/journal/weekly"
SORT file.name DESC
LIMIT 4
```

---

## Vault

| | |
|---|---|
| [[personal/goals\|Goals]] | [[personal/values\|Values]] |
| [[personal/profile\|Profile]] | [[personal/knowledge\|Knowledge]] |
| [[personal/net-worth\|Net Worth]] | [[sessions/coach-memory\|Coach Memory]] |
