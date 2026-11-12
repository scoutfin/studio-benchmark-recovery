# benchmark-recovery

The United States keeps a record of roughly 900,000 brass survey marks, and it is
written entirely in the language of observation: it can say a mark **was not found**
but it has no way to say the mark **is gone**. This is the working behind
[the post](https://scoutfin.net/posts/2026-11-12-the-bottle-of-ashes/).

## What is here

| file | what it does |
|---|---|
| `fetch_all.sh` | pulls the NGS bulk datasheet archive for the 50 states + DC, one state at a time, parses each and deletes the zip so peak disk is one state rather than 600MB |
| `ngs_parse.py` | one compact record per mark: the dated HISTORY series, stability class, marker/setting codes, and the recovery-note bylines |
| `annexc.py` | parses Annex C of the FGCS Bluebook, the authoritative register of contributors, into code to (name, category) |
| `analyse.py` | every table in the post |
| `notes_vs_history.py` | the measurement I abandoned, kept because the reason it failed is the useful part |
| `analysis.txt` | the output of `analyse.py` on the 2026-11-12 archive, so the numbers are checkable without the download |
| `fetch.log` | per-state status code, byte count and record count for that run |

```
./fetch_all.sh                                   # ~600MB, sequential, ~20 min
python3 annexc.py data/annexc.pdf data/annexc.json
python3 analyse.py data/marks.jsonl data/nonpub.jsonl data/annexc.json
```

## The results, in one place

- **791,486** published marks across 51 jurisdictions, plus **778,996** rows in the
  withheld listing. **121,405** marks carry a destroyed code (X, Y or Z) and **not one
  of them** also has a published datasheet.
- The published condition vocabulary is six values over **2,150,309** rows, and none
  of them is *destroyed*.
- **177,328** marks have been reported MARK NOT FOUND. Only **59,580 (33.6%)** were
  ever searched again, and of those **15,801 (26.5%)** were later reported GOOD.
- Of the 400,110 marks whose latest report says GOOD, the median one was last seen
  **25 years** ago; 61% are over 20 years old and 38% over 40.
- The national-agency share of recovery reports fell from **99.0%** in the 1900s to
  **2.0%** in the 2020s. In the 1990s and 2000s the single busiest recoverer in the
  country was **USPSQD**, the United States Power Squadron, with 82,449 and 80,980
  reports.

## Four things that went wrong, three of them mine

**The 500-record cap that does not announce itself.** My first approach was the NGS
Data Explorer bounds API. A 0.5 degree box, a 1 degree box and a 2 degree box all
returned exactly 500 records with byte counts within 500 of each other. The cap is
silent, so any box big enough to be interesting returns a truncated, order-biased
sample that looks like an answer. That is why this uses the bulk archive instead.

**The agency legend that is not published as data.** The datasheet documentation says
only "Refer to the bluebook for recovery agency acronyms", and I could not find that
list as a machine-readable file. So `ngs_parse.py` derives it: every recovery note is
headed by a byline naming the agency in words, dated to the same year as its HISTORY
row, so matching the two within a station block votes on the mapping. 2,505 codes, and
on the 1,184 that also appear in Annex C the two records agree on every one once the
43 abbreviation-vs-spelled-out pairs are read by hand. Worth keeping: `LAWPC` is "LA
WTR AND PWR COMM" and the LA is **Los Angeles**.

**`| head` ate the analysis.** I ran `analyse.py ... | tee analysis.txt | head -80`,
read the 80 lines, and the file on disk stopped at 135 of 162 lines because `head`
exiting SIGPIPEd the writer mid-run. My own schedule file contains a warning about
this exact habit, written after `caught --shapes` died for three days behind a `head`.
Knowing it did not stop me doing it.

**The measurement I threw away.** JD2619's HISTORY row for 1935 says GOOD while its
own 1935 recovery note ends "STATION WAS NOT RECOVERED." A summary row contradicting
the narrative it summarises is the defect I most wanted to count, so I wrote
`notes_vs_history.py` and got 0.82% across six states. Hand-reading twelve hits killed
it: most were notes saying the station was fine but a *reference mark* or the *azimuth
mark* could not be found, and the pattern could not tell which mark a sentence was
about. A sentence-scoped version gave a different number, and the remaining hits were
still mostly that same confusion plus years in which two parties filed opposite
reports, which is a disagreement between people and not a document contradicting
itself. So the post reports one verified instance and no rate. The script is kept
going red on purpose, because a check whose false positives live in its extractor is
worth more as a worked example than as a number.

## Scope

50 states and the District of Columbia, downloaded 12 November 2026; all 51 returned
HTTP 200 and none was skipped. Territories and the archive's non-state codes are not
included, so these totals are smaller than any figure that counts them.
