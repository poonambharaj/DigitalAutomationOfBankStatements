import re
import os

raw = open("References/NewBanksIdentified/ZEMPLER/Car_Claim_Specialists.sql",
           encoding="utf-8").read()

# 4a. Override CreatorPattern and ProducerPattern to .*
def override_patterns(sql):
    def replacer(m):
        vals = m.group(1)
        # Split into individual field values carefully
        # The INSERT INTO digitalpdf$documentidentification has:
        # Id, Name, TitlePattern, AuthorPattern, CreatorPattern, ProducerPattern, Version, PageCount, ...
        # We need to identify and replace the 5th (CreatorPattern) and 6th (ProducerPattern) values

        # Use a more robust approach: find the entire VALUES clause and parse it
        # We need to handle NULL values and quoted strings

        parts = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", vals)
        # parts[0] = Id (9999)
        # parts[1] = Name ('ZemplerBank')
        # parts[2] = TitlePattern (NULL)
        # parts[3] = AuthorPattern (NULL)
        # parts[4] = CreatorPattern (NULL) -> replace with '.*'
        # parts[5] = ProducerPattern (NULL) -> replace with '.*'

        if len(parts) >= 6:
            parts[4] = "'.*'"   # CreatorPattern (0-indexed: index 4)
            parts[5] = "'.*'"   # ProducerPattern (0-indexed: index 5)

        return "VALUES (" + ",".join(parts) + ")"

    return re.sub(r"VALUES \((.+?)\)(?=;)", replacer, sql, flags=re.DOTALL)

# 4b. Convert \n escape sequences inside the Commands field to real newlines.
def convert_commands_newlines(sql):
    # The Commands field is in the digitalpdf$script INSERT
    # Pattern: VALUES (9999,'ZemplerBank','<commands>',...
    # We need to find the Commands string (3rd value) and replace \n with real newlines

    def replace_newlines_in_commands(m):
        prefix = m.group(1)   # everything up to and including opening quote of Commands
        commands = m.group(2) # the Commands value (between the quotes)
        suffix = m.group(3)   # closing quote and rest
        # Replace \n with real newline, but keep \' as-is
        commands_expanded = commands.replace("\\n", "\n")
        return prefix + commands_expanded + suffix

    # Pattern for digitalpdf$script: VALUES (id,'name','commands',rest)
    pattern = r"(VALUES \(\d+,'[^']*',')((?:[^'\\]|\\.)*)('.*?\);)"
    return re.sub(pattern, replace_newlines_in_commands, sql, flags=re.DOTALL)

processed = override_patterns(raw)
processed = convert_commands_newlines(processed)

os.makedirs("output/digital_scripts", exist_ok=True)
open("output/digital_scripts/ZEMPLER_.sql", "w", encoding="utf-8").write(processed)
print("Done. Written to output/digital_scripts/ZEMPLER_.sql")
