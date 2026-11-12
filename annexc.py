"""Parse Annex C of the FGCS Bluebook: the authoritative register of who contributes
geodetic control data, and the only place the datasheet documentation points for the
six-character agency codes in the HISTORY table. Thirteen categories, listed in the
document's own index.

The point of parsing it is to have a SECOND record of the code-to-name map that
ngs_parse.py derives from the datasheets' recovery bylines, and to use NGS's own
grouping instead of a grouping I invent.
"""
import re, sys, zlib, json

CATS = {
 "NATIONAL AGENCIES": "A national",
 "INTER-STATE OR INTER-PROVINCE AGENCIES": "B inter-state",
 "STATE, PROVINCE, COMMONWEALTH, AND TERRITORIAL AGENCIES": "C state",
 "COUNTY AGENCIES": "D county",
 "MUNICIPAL AGENCIES": "E municipal",
 "INTER-CITY AND INTER-COUNTY AGENCIES": "F inter-city",
 "RAILROADS": "G railroads",
 "UTILITY AND NATURAL RESOURCE COMPANIES": "H utility",
 "SURVEYING, ENGINEERING, AND CONSTRUCTION INDUSTRY": "I industry",
 "EDUCATIONAL INSTITUTIONS": "J educational",
 "PROFESSIONAL AND AMATEUR ASSOCIATIONS": "K associations",
 "MISCELLANEOUS COMMERCIAL ORGANIZATIONS AND PRIVATE FIRMS": "L private firms",
 "NON-SPECIFIC DESIGNATORS": "M non-specific",
}


def text(path):
    d = open(path, "rb").read()
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", d, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except Exception:
            pass
    t = b"\n".join(out).decode("latin-1")
    return [x.replace("\\(", "(").replace("\\)", ")")
            for x in re.findall(r"\((.*?)\)\s*Tj", t)]


def parse(path):
    lines = text(path)
    cat = None
    seen_index = False
    out = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("CATEGORIES OF CONTRIBUTORS"):
            seen_index = True
            continue
        hit = next((v for k, v in CATS.items() if s.upper().startswith(k)), None)
        # The index at the front repeats every category name followed by dot
        # leaders; only the body headings count.
        if hit and ". . ." not in s:
            cat = hit
            continue
        if cat is None or not seen_index:
            continue
        if s.startswith("*") or s.startswith("SYMBOL") or s.startswith("C-"):
            continue
        m = re.match(r"^([A-Z0-9][A-Z0-9+\-]{0,5})\s{2,}(\S.*)$", s)
        if m:
            out[m.group(1)] = (m.group(2).strip(), cat)
            continue
        m = re.match(r"^([A-Z0-9][A-Z0-9+\-]{2,5})$", s)
        if m and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not re.match(r"^([A-Z0-9][A-Z0-9+\-]{0,5})\s{2,}", nxt) \
               and not nxt.startswith("*") and len(nxt) > 6:
                out[m.group(1)] = (nxt, cat)
    return out


if __name__ == "__main__":
    d = parse(sys.argv[1])
    print(f"annex C entries parsed: {len(d):,}")
    import collections
    print(collections.Counter(c for _, c in d.values()).most_common())
    for probe in ("CGS", "NGS", "USPSQD", "GEOCAC", "PROFLN", "LOCSUR", "INDIV",
                  "BSA", "USGS"):
        print(f"  {probe:<8} {d.get(probe)}")
    if len(sys.argv) > 2:
        json.dump(d, open(sys.argv[2], "w"))
