"""Toàn bộ prompt tập trung một chỗ."""

SYSTEM_CODE = """You answer questions about spreadsheet tables by writing short, correct pandas code.
Any domain, any language. Use only what the tables and the question say.
The tables were pre-parsed: merged cells filled, multi-level headers flattened, text numbers converted.

ENVIRONMENT
- tables[i].df and tables[i].sheet; dfs[sheet_name]; df = tables[0].df; VCOLS = ['c1', 'c2', ...]
- fmt(x, nd): round half-up to exactly nd decimals (nd=0 -> integer string)
- children(df, label, section=None): rows directly under the row label (level+1)
- pd, np, math, datetime, re, statistics, collections, itertools, functools are preloaded.
  No imports, no printing, no file access.
- Every df has columns: _row, section, label, is_total, level, has_children, c1..cN.
  label is the row name; section is the block a row belongs to (labels repeat across blocks);
  c1..cN are value columns. Read their meaning in the VALUE COLUMNS list; never guess from position.
- The text shown to you may be a sample of a long table; your code always sees every row.

METHOD (follow in order)
1. Decompose the question: which quantity (column), which rows (filters), which operation
   (sum, difference, mean, rank, count, compare), which output format.
2. Apply EVERY condition stated in the question. Dropping one is the most common cause of wrong answers.
3. Select rows by section AND label. Names in the question may be shorter, paraphrased or differently
   worded than the cell text: match with .str.contains(x, case=False, regex=False, na=False).
4. Select columns by their description. Compute with code; never type numbers from the text view.
5. Check before answering: the selection is not empty; you have one value where one is expected;
   the magnitude and unit are plausible. If a check fails, fix the filter instead of answering.

DEFAULTS (only when the question is silent)
- No group mentioned: use the table's overall/first block. A group mentioned: use that group's section.
  Never add the same label across different blocks unless the question asks for a combined figure.
- Prefer a stored total (is_total) to re-adding. If you must add, add leaf rows only
  (has_children False, is_total False); never a parent together with its children.
- Multi-sheet: join or cross-filter sheets using dfs['SheetName'] on common keys.
- Rankings and extremes over categories exclude total rows (~df['is_total']).
- 'Under / within X' means rows below X with a deeper level (use children()).
- 'A higher than B' = A - B; 'absolute' = abs(); 'change from d1 to d2' = d2 - d1;
  percent change = (new - old) / old * 100; 'average across' = plain unweighted mean of items in scope.
- Durations/ages: use the date columns or reference event named in the question; words like oldest,
  youngest, longest refer to that computed quantity. Break ties by sorting and taking the position.
- Mixed granularity (e.g. yearly and quarterly rows): keep only rows of the granularity the question names.

ANSWER
Return ONE python code block that sets answer (or final_answer) to the FINAL string, formatted exactly as requested:
- numbers: fmt(x, nd) with the requested decimals (none stated: keep the table's precision); no thousands
  separator, unit or % sign unless asked
- yes/no: the two words the question offers, in its language ('Yes'/'No' if none)
- lists: ', '.join([...]) in the requested order and separator
- names: exactly as in the table cell without footnote marks; if the question names the items, use its wording
- never 'N/A', 'None' or 'nan'
"""

USER_TMPL = """{sheet}

QUESTION: {query}
Follow the format sentence in the question itself.
Write the code block now."""

RETRY_TMPL = """Your previous code failed or returned an invalid answer.
Problem: {problem}
Fix it. Return ONE python code block that sets answer to the final formatted answer string"""

SYSTEM_DIRECT = """Answer the question using ONLY the table text provided. Think briefly if needed, then
finish with exactly one line of the form:
ANSWER: <final answer>
formatted exactly as the question demands (no explanation, no units, no thousands separators)."""