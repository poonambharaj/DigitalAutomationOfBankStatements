#!/usr/bin/env python3
"""
generate_script.py — Analyse a PDF and generate MySQL INSERT statements for
digitalpdf$script and digitalpdf$documentidentification using Claude.

Usage:
  python generate_script.py <path_to_pdf>
  python generate_script.py <path_to_pdf> --next-script-id 100 --next-def-id 200

Requirements:
  pip install -r requirements.txt
  Copy .env.example to .env and set ANTHROPIC_API_KEY
"""

import argparse
import base64
import sys
from pathlib import Path

# Load .env if present (requires python-dotenv, installed via requirements.txt)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # Falls back to environment variable set in the shell

import anthropic

REPO_ROOT = Path(__file__).parent
PLAN_MD = REPO_ROOT / "Plan.md"
SCRIPTS_SQL = REPO_ROOT / "DigitalScriptSample" / "DigitalScripts.sql"
DEFS_SQL = REPO_ROOT / "DigitalScriptSample" / "DigitalDocDefination.sql"

# ~20k tokens per sample — enough to cover invoice and bank-statement examples
SAMPLE_BYTES = 80_000


def read_sample(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > SAMPLE_BYTES:
        text = text[:SAMPLE_BYTES] + "\n-- [truncated — representative sample above] --"
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse a PDF and generate MySQL INSERT statements for OCRex DigitalPdf"
    )
    parser.add_argument("pdf", help="Path to the PDF file to analyse")
    parser.add_argument(
        "--next-script-id",
        type=int,
        default=9999,
        help="Next available Id for digitalpdf$script (default: 9999)",
    )
    parser.add_argument(
        "--next-def-id",
        type=int,
        default=9999,
        help="Next available Id for digitalpdf$documentidentification (default: 9999)",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    plan = PLAN_MD.read_text(encoding="utf-8")
    scripts_sample = read_sample(SCRIPTS_SQL)
    defs_sample = read_sample(DEFS_SQL)
    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode()

    client = anthropic.Anthropic()
    print(f"Analysing {pdf_path.name} ...\n", file=sys.stderr)

    with client.messages.stream(
        model="global.anthropic.claude-sonnet-4-6",
        max_tokens=8192,
        system=[
            # Stable reference context — cached across repeated calls
            {
                "type": "text",
                "text": plan,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": "## Sample scripts (digitalpdf$script)\n\n" + scripts_sample,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": (
                    "## Sample document definitions (digitalpdf$documentidentification)\n\n"
                    + defs_sample
                ),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"""Analyse the PDF above and produce MySQL INSERT statements to register it in the OCRex DigitalPdf system.

Use these next available IDs:
- digitalpdf$script Id: {args.next_script_id}
- digitalpdf$documentidentification Id: {args.next_def_id}

Follow the Plan.md guide exactly. Model the output on the sample SQL provided in the system context.

Steps:
1. Read the PDF metadata: Creator, Producer, Author, Title, PDF version integer, page count.
2. Choose ContainsText phrases (unique to this layout) and ExcludesText phrases (to disambiguate from similar layouts).
3. Determine document type — invoice/credit note (VerificationRuleSetId 2 or 3) or bank statement (4).
4. Write a complete, working DSL script in the Commands field:
   - Use \\n for line breaks and \\' to escape single quotes inside the SQL string value.
   - Extract all required output $variables for the document type (see Plan.md Step 2).
   - For bank statements: handle repeating page headers/footers, carry-forward rows, and multi-page tables.
   - For invoices: extract $invoiceType, $name, $currency, $vatNumber, $invoiceNumber, $invoiceDate, $net, $tax, $total, and $lineItems.
5. If the same layout might be produced by different PDF creators/producers (e.g. printed from different browsers or OS), generate one digitalpdf$documentidentification row per variant, all pointing to the same ScriptId.
6. Output ONLY valid MySQL INSERT statements — no prose, no markdown code fences.""",
                    },
                ],
            }
        ],
    ) as stream:
        sql = stream.get_final_text()

    out_path = pdf_path.with_suffix(".sql")
    out_path.write_text(sql, encoding="utf-8")
    print(sql)
    print(f"\nSaved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
