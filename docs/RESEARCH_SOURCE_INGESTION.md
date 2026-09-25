# GrandMother Research Source Ingestion Policy

## arXiv HTML reliability

arXiv states that HTML papers are generated through LaTeXML and that HTML papers can display errors when LaTeXML cannot translate a TeX or LaTeX construct. These errors are a conversion-layer issue, not evidence that the underlying research content is incorrect.

## Source precedence

For GrandMother research extraction, use this precedence:

1. Paper TeX/source files for exact equations, tables, macros, labels, and machine-reproducible structure.
2. Paper PDF for visual verification of figures, tables, page layout, and rendered mathematics.
3. arXiv HTML for searchable navigation, section discovery, and text extraction when the relevant passage converts cleanly.

When HTML contains an arXiv conversion error, do not infer or repair the missing research content from the malformed HTML alone. Cross-check the TeX/source or PDF.

## Error handling

Record:

- paper identifier and version, for example 2507.13023v3
- source format used
- section or appendix
- affected HTML location
- LaTeXML or rendering error when visible
- replacement source used for verification
- extraction timestamp
- GrandMother code commit

## GrandMother replication rule

Published quantities, equations, filtering rules, table values, and methodological definitions must be traceable to a source artifact. HTML extraction may be used to locate the content, but the final replication record should preserve enough provenance to distinguish:

- source text
- HTML conversion
- GrandMother interpretation
- GrandMother implementation

## Current target paper

Paper: Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest

arXiv: 2507.13023v3

HTML:
https://arxiv.org/html/2507.13023v3

Accessibility / HTML error guidance:
https://info.arxiv.org/about/accessibility_html_error_messages.html
