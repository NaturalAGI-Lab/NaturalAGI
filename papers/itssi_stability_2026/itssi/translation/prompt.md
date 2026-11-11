You are translating a scientific article from English into Ukrainian for the journal "Сучасний стан наукових досліджень та технологій в промисловості".

Input: `to_translate.json` in the current directory, a list of objects {"id", "en"}. Glossary: `glossary.md`.
Output: write `translation_uk.json` in the current directory: the same list, in the same order, each object {"id", "en", "uk"}. Keep "id" and "en" unchanged.

Rules. The author asked for an EXACT translation of his own words.
1. Translate sentence by sentence. Keep the number and order of sentences in every item. Do not merge or split sentences.
2. Do not add, drop, explain, soften or strengthen anything. Do not "improve" style, do not invent new turns of phrase. Change word order only where Ukrainian grammar needs it.
3. Use the glossary terms exactly. If an English term is missing from the glossary, pick one Ukrainian term and use it everywhere.
4. Keep unchanged: placeholders like ⟦M12⟧ (exact characters, same position in the sentence), citation brackets [4], [9–12], concept ids (2_2, 7_1), image ids (mnist_test_2_00766, 4_00755), software names and versions (NetworkX 3.6, scikit-image 0.26, optimize_graph_edit_distance), URLs, abbreviations GED, GNG, MNIST, SVM, DLQ, ComAN, E/C/I, and tab characters.
5. Numbers: decimal comma (90,05 %), a space as thousands separator (8 683), a space before % ; ranges with an en dash (1–37). "pp" (percentage points) -> "п. п.".
6. Quotes: only straight double quotes " ". Replace « » and curly quotes with " ".
7. Figure/table captions: "Fig. 3." -> "Рис. 3.", "Table 1." -> "Таблиця 1."; in-text "Figure 3"/"Fig. 3" -> "рис. 3", "Table 1" -> "табл. 1", "Section 1.2" -> "підрозділ 1.2".
8. Use impersonal academic voice only where the English already is impersonal; translate "we" as the first person plural ("ми", "провели") — do not change the author's voice.
9. Ukrainian orthography 2019, apostrophe ’ is fine.

When finished, print a short summary: number of items written, and any English term you had to choose a Ukrainian equivalent for (term -> choice).
