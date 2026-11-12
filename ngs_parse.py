"""Parse NGS bulk datasheets into one compact record per mark.

Each station block carries a HISTORY table of dated condition reports, which is the
only place the recovery SEQUENCE lives; the JSON API exposes only the last one. The
blocks are keyed by a 6-char PID repeated at the start of every line.
"""
import re, sys, zipfile, json, io

PID = r"[A-Z]{2}\d{4}"
SPLIT = re.compile(r"\n(?=\s" + PID + r" \*{20,})")
HIST = re.compile(r"^\s(" + PID + r")  HISTORY     - (\S+)\s+(.*?)\s{2,}(\S*)\s*$", re.M)
HIST2 = re.compile(r"^\s(" + PID + r")  HISTORY     - (\S+)\s+(.+?)\s*$", re.M)
STAB = re.compile(r"^\s" + PID + r"_STABILITY: ([A-D]) = ", re.M)
MARK = re.compile(r"^\s" + PID + r"_MARKER: (\S+) = (.*?)\s*$", re.M)
SETT = re.compile(r"^\s" + PID + r"_SETTING: (\S+) = ", re.M)
DESCBY = re.compile(r"^\s" + PID + r"'DESCRIBED BY .*?(\d{4})\s*$", re.M)
DESIG = re.compile(r"^\s" + PID + r"  DESIGNATION -  (.*?)\s*$", re.M)
# The agency column in HISTORY is a 6-char code with no published legend I could
# find. But the datasheets self-document: each recovery section carries a byline
# naming the agency in words, with the same year as its HISTORY row. Harvest both
# and the code-to-name map falls out of the data.
BYLINE = re.compile(r"^\s" + PID + r"'(?:RECOVERY NOTE|RECOVERY|DESCRIBED) BY "
                    r"(.+?)\s+(\d{4})\s*(?:\([^)]*\))?\s*$", re.M)
STCO = re.compile(r"^\s" + PID + r"  STATE/COUNTY-  (\S+)\s*$", re.M)


def parse_block(b):
    m = re.match(r"\s(" + PID + r")", b)
    if not m:
        return None
    pid = m.group(1)
    hist = []
    for hm in HIST2.finditer(b):
        if hm.group(1) != pid:
            continue
        date = hm.group(2)
        rest = hm.group(3)
        # condition and reporter are two columns; reporter is the last token when
        # separated by 2+ spaces, otherwise there is no reporter at all.
        parts = re.split(r"\s{2,}", rest)
        cond = parts[0].strip()
        by = parts[-1].strip() if len(parts) > 1 else ""
        if date == "Date" and cond == "Condition":
            continue          # the table's own header row
        hist.append([date, cond, by])
    s = STAB.search(b)
    mk = MARK.search(b)
    st = SETT.search(b)
    db = DESCBY.search(b)
    sc = STCO.search(b)
    bylines = [[bm.group(2), bm.group(1).strip()] for bm in BYLINE.finditer(b)]
    return dict(pid=pid, bylines=bylines, stab=(s.group(1) if s else None),
                marker=(mk.group(1) if mk else None),
                marker_txt=(mk.group(2) if mk else None),
                setting=(st.group(1) if st else None),
                described=(int(db.group(1)) if db else None),
                stco=(sc.group(1) if sc else None),
                hist=hist)


def parse_zip(path, out):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".txt")]
    if not name:
        return 0
    txt = z.read(name[0]).decode("latin-1")
    n = 0
    for b in SPLIT.split(txt):
        r = parse_block(b)
        if r:
            out.write(json.dumps(r) + "\n")
            n += 1
    return n


def parse_nonpub(path, out, state):
    """The withheld listing. Its code legend is the only place the database can say a
    mark is gone, and it says it three ways: X surface mark REPORTED destroyed, Y
    surface and underground REPORTED destroyed, Z PRESUMED destroyed. Fixed-width,
    with the H and v codes in the last two columns."""
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".dat")]
    if not name:
        return 0
    lines = z.read(name[0]).decode("latin-1").splitlines()
    n = 0
    for ln in lines:
        if not ln.startswith(" >") or len(ln) < 75:
            continue
        pid = ln[2:8].strip()
        if not re.fullmatch(PID, pid):
            continue
        out.write(json.dumps(dict(pid=pid, state=state,
                                  h=ln[-2], v=ln[-1])) + "\n")
        n += 1
    return n


if __name__ == "__main__":
    path, marks_out, nonpub_out, state = sys.argv[1:5]
    with open(marks_out, "a") as fh:
        a = parse_zip(path, fh)
    with open(nonpub_out, "a") as fh:
        b = parse_nonpub(path, fh, state)
    print(f"{state} marks={a} nonpub={b}", flush=True)
