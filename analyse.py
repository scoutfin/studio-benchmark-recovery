"""Measure the NGS mark-recovery record: who looked, when, and what they found.

Inputs are the two jsonl files produced by ngs_parse.py over the 50 states + DC
bulk datasheet archives. Every number printed here is derived from those files;
nothing is quoted from a secondary source.
"""
import json, re, sys, collections, statistics

MARKS, NONPUB = sys.argv[1], sys.argv[2]
THIS_YEAR = 2026

def key(d):
    """Sortable date key, or None when the datasheet says UNK."""
    if not d or not d[:4].isdigit():
        return None
    if len(d) >= 8 and d[:8].isdigit():
        return int(d[:8])
    return int(d[:4]) * 10000

def year(d):
    k = key(d)
    return None if k is None else k // 10000

rows = [json.loads(l) for l in open(MARKS)]
non = [json.loads(l) for l in open(NONPUB)]
print(f"published marks parsed: {len(rows):,}")
print(f"nonpub listing rows:    {len(non):,}")

# ---- 1. the only place the record can say a mark is gone --------------------
DESTROYED = set("XYZ")
dpids = {r["pid"] for r in non if r["h"] in DESTROYED or r["v"] in DESTROYED}
ppids = {r["pid"] for r in rows}
print(f"nonpub marks coded destroyed (X/Y/Z): {len(dpids):,}")
print(f"  of those, ALSO published with a datasheet: {len(dpids & ppids):,}")
only_d = dpids - ppids
print(f"  withheld entirely:                       {len(only_d):,}")
print(f"  destroyed-coded share of all marks seen: "
      f"{100*len(dpids)/len(ppids | dpids):.1f}% of {len(ppids | dpids):,}")
codes = collections.Counter()
for r in non:
    for c in (r["h"], r["v"]):
        if c in DESTROYED:
            codes[c] += 1
print(f"  code counts (H+v columns): {dict(codes)}")

# ---- 2. the published condition vocabulary ---------------------------------
vocab = collections.Counter(h[1] for r in rows for h in r["hist"])
print("\ncondition vocabulary across every HISTORY row in the published set:")
for k, v in vocab.most_common():
    print(f"  {k:<18} {v:>9,}")

# ---- 3. a 'not found' is a statement about a search ------------------------
FOUND = {"GOOD", "POOR"}
ever_nf = searched_again = found_again = again_good = 0
nf_then_only_nf = 0
good_then_nf = 0
for r in rows:
    h = [(key(d), c) for d, c, _ in r["hist"] if key(d) is not None]
    h.sort()
    nf = [i for i, (k, c) in enumerate(h) if c == "MARK NOT FOUND"]
    if nf:
        ever_nf += 1
        first = nf[0]
        later = h[first + 1:]
        if later:
            searched_again += 1
            if any(c in FOUND for _, c in later):
                found_again += 1
            if any(c == "GOOD" for _, c in later):
                again_good += 1
            if all(c == "MARK NOT FOUND" for _, c in later):
                nf_then_only_nf += 1
    g = [i for i, (k, c) in enumerate(h) if c == "GOOD"]
    if g and any(c == "MARK NOT FOUND" for _, c in h[g[0] + 1:]):
        good_then_nf += 1
print(f"\nmarks ever reported MARK NOT FOUND:        {ever_nf:,}")
print(f"  someone filed a later report (exposure): {searched_again:,}"
      f"  ({100*searched_again/ever_nf:.1f}%)")
print(f"  of THOSE, later reported GOOD or POOR:   {found_again:,}"
      f"  ({100*found_again/searched_again:.1f}%)")
print(f"  of THOSE, later reported GOOD:           {again_good:,}"
      f"  ({100*again_good/searched_again:.1f}%)")
print(f"  of THOSE, every later report NOT FOUND:  {nf_then_only_nf:,}"
      f"  ({100*nf_then_only_nf/searched_again:.1f}%)")
print(f"marks reported GOOD and later NOT FOUND:   {good_then_nf:,}")

# ---- 4. how old is the evidence behind a condition -------------------------
ages = collections.defaultdict(list)
for r in rows:
    h = [(key(d), c) for d, c, _ in r["hist"] if key(d) is not None]
    if not h:
        continue
    h.sort()
    k, c = h[-1]
    ages[c].append(THIS_YEAR - k // 10000)
print("\nage in years of the LAST report on a mark, by what that report said:")
for c, a in sorted(ages.items(), key=lambda x: -len(x[1])):
    a.sort()
    print(f"  {c:<18} n={len(a):>8,}  median {statistics.median(a):>5.0f}"
          f"  p25 {a[len(a)//4]:>3}  p75 {a[3*len(a)//4]:>3}"
          f"  >=20y {100*sum(1 for x in a if x >= 20)/len(a):>4.0f}%"
          f"  >=40y {100*sum(1 for x in a if x >= 40)/len(a):>4.0f}%")

# ---- 5. who looked, derived from the datasheets' own bylines ---------------
votes = collections.defaultdict(collections.Counter)
for r in rows:
    hy = collections.defaultdict(list)
    for d, c, by in r["hist"]:
        y = year(d)
        if y and by:
            hy[y].append(by)
    byy = collections.defaultdict(list)
    for y, name in r["bylines"]:
        byy[int(y)].append(name)
    for y in set(hy) & set(byy):
        if len(hy[y]) == 1 and len(byy[y]) == 1:
            votes[hy[y][0]][byy[y][0]] += 1
legend = {}
for code, c in votes.items():
    name, n = c.most_common(1)[0]
    legend[code] = (name, n, sum(c.values()), n / sum(c.values()))
print(f"\nagency code -> name, derived by matching HISTORY years to recovery-note"
      f" bylines: {len(legend):,} codes")
agents = collections.Counter(by for r in rows for _, _, by in r["hist"] if by)
print("  top agencies by number of condition reports filed:")
for code, n in agents.most_common(18):
    nm, v, tot, frac = legend.get(code, ("(no byline ever matched)", 0, 0, 0))
    print(f"    {code:<8} {n:>8,}  {nm[:42]:<42} "
          f"{'' if not tot else f'{100*frac:.0f}% of {tot} votes'}")

dec = collections.defaultdict(collections.Counter)
for r in rows:
    for d, c, by in r["hist"]:
        y = year(d)
        if y and by and y >= 1900:
            dec[(y // 10) * 10][by] += 1
PUBLIC = {"USPSQD", "GEOCAC", "INDIV"}
print("\n  condition reports by decade, and the share filed by the three codes whose"
      "\n  derived names are US POWER SQUADRON, GEOCACHING and INDIVIDUAL CONTRIBUTORS:")
for d in sorted(dec):
    tot = sum(dec[d].values())
    pub = sum(v for k, v in dec[d].items() if k in PUBLIC)
    top = dec[d].most_common(1)[0]
    print(f"    {d}s  reports {tot:>8,}   public {pub:>7,} ({100*pub/tot:>4.1f}%)"
          f"   busiest: {top[0]} {top[1]:,}")

# ---- 5b. the same, counting only reports that are a SEARCH ----------------
# MONUMENTED and FIRST OBSERVED are the mark being created or first used, not
# somebody going to look for one that already exists. The question "who keeps this
# record current" is about the second thing, so it gets its own denominator.
SEARCH = {"GOOD", "POOR", "MARK NOT FOUND", "SEE DESCRIPTION"}
dec2 = collections.defaultdict(collections.Counter)
for r in rows:
    for d, c, by in r["hist"]:
        y = year(d)
        if y and by and y >= 1900 and c in SEARCH:
            dec2[(y // 10) * 10][by] += 1
print("\n  recovery reports only (GOOD / POOR / NOT FOUND / SEE DESCRIPTION),"
      "\n  which is the count of times somebody went looking:")
for d in sorted(dec2):
    tot = sum(dec2[d].values())
    pub = sum(v for k, v in dec2[d].items() if k in PUBLIC)
    top3 = ", ".join(f"{k} {v:,}" for k, v in dec2[d].most_common(3))
    print(f"    {d}s  searches {tot:>8,}   public {pub:>7,} ({100*pub/tot:>4.1f}%)"
          f"   top: {top3}")

# ---- 5c. the network's own age profile ------------------------------------
first = collections.Counter()
for r in rows:
    ys = [year(d) for d, _, _ in r["hist"] if year(d)]
    if ys:
        first[(min(ys) // 10) * 10] += 1
print("\n  earliest dated report per mark, by decade (the honest age profile; the"
      "\n  datasheet's MONUMENTED row is often dated UNK so this is a lower bound"
      "\n  on each mark's age):")
for d in sorted(first):
    print(f"    {d}s {first[d]:>8,}")

# ---- 5d. two records of the code-to-name map, and NGS's own grouping -------
# Annex C of the FGCS Bluebook is what the datasheet documentation tells you to
# consult for "recovery agency acronyms". Parsing it gives a second, independent
# record of the map derived above from the datasheets' own bylines, and it gives
# NGS's thirteen contributor categories, which beats any grouping I would invent.
annex = {}
try:
    annex = {k: tuple(v) for k, v in json.load(open(sys.argv[3])).items()}
except Exception as e:
    print(f"\n  (annex C not loaded: {e})")
if annex:
    def toks(x):
        x = re.sub(r"[^A-Z ]", " ", x.upper())
        return {w for w in x.split() if len(w) > 2 and w not in
                {"THE", "AND", "OF", "US", "USA", "NOW", "DEPT", "DEPARTMENT"}}
    both = [c for c in legend if c in annex]
    agree = [c for c in both if toks(legend[c][0]) & toks(annex[c][0])]
    print(f"\n  code->name map, two independent records:")
    print(f"    codes with a byline-derived name:      {len(legend):,}")
    print(f"    codes listed in Annex C:               {len(annex):,}")
    print(f"    in both (the only ones that can differ): {len(both):,}")
    print(f"    sharing at least one content word:     {len(agree):,}"
          f"  ({100*len(agree)/len(both):.1f}%)")
    for c in [c for c in both if c not in agree][:8]:
        print(f"      ?! {c}: byline {legend[c][0][:34]!r} vs annex {annex[c][0][:34]!r}")

    print("\n  recovery reports by Annex C category, by decade:")
    cats = sorted({v[1] for v in annex.values()}) + ["(not in Annex C)"]
    hdr = "    decade   total   " + "  ".join(f"{c.split()[0]:>5}" for c in cats)
    print(hdr)
    for d in sorted(dec2):
        tot = sum(dec2[d].values())
        row = []
        for c in cats:
            n = sum(v for k, v in dec2[d].items()
                    if (annex.get(k, (None, "(not in Annex C)"))[1] == c))
            row.append(f"{100*n/tot:>5.1f}")
        print(f"    {d}s {tot:>8,}   " + "  ".join(row))
    print("    (columns are percentages of that decade's recovery reports)")

    print("\n  the codes filing the most recovery reports that Annex C does not list:")
    missing = collections.Counter()
    for d in dec2:
        for k, v in dec2[d].items():
            if k not in annex:
                missing[k] += v
    for k, v in missing.most_common(8):
        nm = legend.get(k, ("(no byline matched)",))[0]
        print(f"      {k:<8} {v:>8,}  {nm[:44]}")

# ---- 6. stability class as a prediction -----------------------------------
print("\nlatest condition by STABILITY class (the class is the datasheet's own"
      "\nexpectation of how well the mark will hold):")
cross = collections.defaultdict(collections.Counter)
for r in rows:
    h = [(key(d), c) for d, c, _ in r["hist"] if key(d) is not None]
    if not h or not r["stab"]:
        continue
    h.sort()
    cross[r["stab"]][h[-1][1]] += 1
for s in sorted(cross):
    t = sum(cross[s].values())
    nf = cross[s]["MARK NOT FOUND"]
    print(f"  stability {s}  n={t:>8,}   last report NOT FOUND {100*nf/t:>5.1f}%"
          f"   GOOD {100*cross[s]['GOOD']/t:>5.1f}%")
