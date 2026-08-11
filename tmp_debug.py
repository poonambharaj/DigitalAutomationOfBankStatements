import re, sys, json

sql = open("C:/dev/AutomationOfDigitalScripts/output/digital_scripts/JAJA_20260603.sql", encoding="utf-8").read()

# Use the same regex as in the test fixture
pattern = (
    r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,"
    r"\s*'[^']*'\s*,\s*'((?:[^'\\]|\\.)*)'"
)
m = re.search(pattern, sql, re.DOTALL | re.IGNORECASE)
if not m:
    print("NO MATCH")
    sys.exit(1)

raw = m.group(1)

# Show a snippet containing "features" from the raw field
for chunk in raw.split(r"\n"):
    if "features" in chunk:
        print("RAW features chunk:", repr(chunk))
        break

# Unescape \n -> newline, \' -> '  (same as fixture)
unescaped = raw.replace(r"\n", "\n").replace(r"\'", "'")

for ln in unescaped.splitlines():
    if "features" in ln:
        print("UNESCAPED features line:", repr(ln))
        break

# Check quote style in unescaped
bq = chr(92) + chr(34)   # \"
print("Has backslash-dquote in unescaped:", bq in unescaped)
print("Has literal dquote in unescaped:", '"' in unescaped)

# Try regex patterns
m2 = re.search(r'\$features\s*=\s*"([^"]*)"', unescaped)
print("Literal dquote match:", m2.group(1) if m2 else None)

m3 = re.search(r'\$features\s*=\s*\\"([^\\"]*)\\"', unescaped)
print("Escaped dquote match:", m3.group(1) if m3 else None)

# ---- ContainsText in definition INSERT ----
doc_match = re.search(
    r"INSERT INTO `digitalpdf\$documentidentification`.*?;",
    sql, re.DOTALL
)
if doc_match:
    doc_insert = doc_match.group(0)
    ct_match = re.search(r"'(\[.*?\])'", doc_insert, re.DOTALL)
    if ct_match:
        raw_ct = ct_match.group(1)
        print("ContainsText raw:", repr(raw_ct[:120]))
        try:
            parsed = json.loads(raw_ct)
            print("json.loads OK:", parsed)
        except Exception as e:
            print("json.loads FAIL:", e)
        # Unescape \" -> " first
        unescaped_ct = raw_ct.replace('\\"', '"')
        print("ContainsText unescaped:", repr(unescaped_ct[:120]))
        try:
            parsed2 = json.loads(unescaped_ct)
            print("json.loads after unescape OK:", parsed2)
        except Exception as e:
            print("json.loads after unescape FAIL:", e)
