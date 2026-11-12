"""Does the HISTORY summary row agree with the recovery note it summarises?

JD2619's table says 1935 GOOD. Its own 1935 recovery note says the surveyor spent
a day and a half digging with the county surveyor and old residents and ends
"STATION WAS NOT RECOVERED." One instance is an anecdote, so this counts the
disagreement on a named sample of states.

Two records of one event, inside one document, which is the only check shape that
reliably catches anything: the narrative and the row that stands in for it.
"""
import re, sys, zipfile, collections

PID = r"[A-Z]{2}\d{4}"
SPLIT = re.compile(r"\n(?=\s" + PID + r" \*{20,})")
# First version matched any negative phrase anywhere in the note and called 0.82%
# disagreement. Hand-reading twelve examples killed it: most were notes saying the
# STATION was fine but a REFERENCE MARK or the AZIMUTH MARK could not be found,
# which is not a disagreement about the thing the row describes. So the test is now
# per sentence, and a sentence that mentions another mark is not evidence about the
# station. A checker's false positives live in its extractor.
NEG = re.compile(r"NOT RECOVERED|NOT FOUND|NOT BE (?:FOUND|RECOVERED)"
                 r"|NO SIGN OF|COULD NOT (?:BE )?(?:FOUND|LOCATE[DS]?)|NOT LOCATED")
POS = re.compile(r"RECOVERED IN GOOD|FOUND IN GOOD|IN GOOD CONDITION"
                 r"|RECOVERED AS DESCRIBED|WAS RECOVERED|STATION FOUND"
                 r"|STATION (?:WAS )?RECOVERED")
OTHER = re.compile(r"REFERENCE MARK|AZIMUTH|\bRM\b|R\.M\.|BENCH MARK|\bBM\b"
                   r"|WITNESS POST|UNDERGROUND MARK")


def judge(text):
    """Return (negative_about_the_station, positive_about_the_station)."""
    neg = pos = False
    for sent in re.split(r"(?<=[.;])\s+", text):
        if OTHER.search(sent):
            continue
        if "STATION" not in sent and "MARK" not in sent:
            continue
        if NEG.search(sent):
            neg = True
        elif POS.search(sent):
            pos = True
    return neg, pos

tot = collections.Counter()
examples = []
for path in sys.argv[1:]:
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".txt")][0]
    txt = z.read(name).decode("latin-1")
    for b in SPLIT.split(txt):
        m = re.match(r"\s(" + PID + r")", b)
        if not m:
            continue
        pid = m.group(1)
        hist = {}
        for hm in re.finditer(r"^\s" + PID + r"  HISTORY     - (\S+)\s+(.+?)\s*$",
                              b, re.M):
            y, rest = hm.group(1)[:4], hm.group(2)
            cond = re.split(r"\s{2,}", rest)[0].strip()
            if y.isdigit():
                hist.setdefault(y, set()).add(cond)
        # recovery note text, split by its own STATION RECOVERY (YYYY) headings
        notes = {}
        parts = re.split(r"STATION RECOVERY \((\d{4})\)", b)
        for i in range(1, len(parts) - 1, 2):
            notes.setdefault(parts[i], "")
            notes[parts[i]] += " " + re.sub(r"\s+", " ", parts[i + 1])
        for y, text in notes.items():
            if y not in hist:
                tot["note year not in history"] += 1
                continue
            conds = hist[y]
            neg, pos = judge(text)
            if "GOOD" in conds and neg and not pos:
                tot["row GOOD, note says not recovered"] += 1
                if len(examples) < 12:
                    examples.append((pid, y, text.strip()[:150]))
            elif "MARK NOT FOUND" in conds and pos and not neg:
                tot["row NOT FOUND, note says recovered"] += 1
            elif neg or pos:
                tot["agree"] += 1
            else:
                tot["note says neither"] += 1
print(f"states: {len(sys.argv)-1}")
for k, v in tot.most_common():
    print(f"  {k:<36} {v:>8,}")
scored = tot["agree"] + tot["row GOOD, note says not recovered"] \
         + tot["row NOT FOUND, note says recovered"]
if scored:
    bad = tot["row GOOD, note says not recovered"] \
          + tot["row NOT FOUND, note says recovered"]
    print(f"  scorable note/row pairs: {scored:,}; disagreements {bad:,} "
          f"({100*bad/scored:.2f}%)")
print("\n  examples where the row says GOOD and the note says otherwise:")
for pid, y, t in examples:
    print(f"    {pid} {y}: {t}")
