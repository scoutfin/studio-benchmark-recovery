#!/bin/bash
# Pull the NGS bulk datasheet archive state by state, parse each one, then delete the
# zip so peak disk stays at one state rather than 600MB. Sequential with a pause:
# this is a public bulk-download directory and bulk is what it is for, but one
# connection at a time is how a person would use it.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${NGSDIR:-$HERE/data}
mkdir -p "$OUT"
cd "$OUT" || exit 1
UA='scout/1.0 (+https://scoutfin.net/about/)'
STATES="AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
: > marks.jsonl
: > nonpub.jsonl
: > fetch.log
for st in $STATES; do
  code=$(curl -sS -A "$UA" --max-time 600 -o "$st.ZIP" \
    -w '%{http_code}' "https://geodesy.noaa.gov/pub/DS_ARCHIVE/DataSheets/$st.ZIP")
  if [ "$code" != "200" ]; then
    echo "$st HTTP $code SKIPPED" >> fetch.log
    rm -f "$st.ZIP"
    continue
  fi
  echo -n "$st http=$code size=$(stat -c%s "$st.ZIP") " >> fetch.log
  python3 -I "$HERE"/ngs_parse.py "$st.ZIP" marks.jsonl nonpub.jsonl "$st" >> fetch.log 2>&1
  rm -f "$st.ZIP"
  sleep 2
done
echo "DONE $(wc -l < marks.jsonl) marks, $(wc -l < nonpub.jsonl) nonpub" >> fetch.log
