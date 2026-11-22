import json, re, sys, pymupdf
d = pymupdf.open(sys.argv[1]); K = json.load(open("keys.json"))
txt = [re.sub(r"\s+", " ", p.get_text()) for p in d]
start = next(i for i, t in enumerate(txt) if "Abbreviation Full Form" in t) + 1
pages, missing = {}, []
for k in K["front"]:
    i = next((i for i, t in enumerate(txt[:start]) if t.strip().startswith(k) or (" " + k + " ") in (" " + t)), None)
    if i is not None: pages[k] = i + 1
for k in K["heads"] + K["figs"] + K["tabs"]:
    i = next((i for i in range(start, len(txt)) if k in txt[i]), None)
    if i is None: missing.append(k)
    else: pages[k] = i + 1
json.dump(pages, open("pages.json", "w"), indent=0)
print("found", len(pages), "missing", missing[:10])
