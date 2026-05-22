"""ITSSI-2026 стаття — редагований вміст.

Усі текстові рядки, списки авторів, анотації й бібліографія винесені сюди,
щоб generate_paper.py відповідав тільки за форматування.

Правила редагування (ITSSI, див. plans/itssi_paper_2026.md):
- Лапки тільки " " (не «» і не "")
- Абревіатур у назві та анотації не використовувати
- Анотація UA і EN — 1900–2200 знаків кожна, структурована
  (Предмет → Мета → Завдання → Методи → Результати → Висновки)
- Ключові слова — до 10, розділені ";"
- Основний текст ≥ 8 сторінок (керівник рекомендує ≤ 10 для ITSSI)
- Рисунки + таблиці разом ≤ 3 сторінок
- Формули у §4 переважно прозою; одна формула (оператор редукції концепту)
  вставляється через add_formula_placeholder у generate_paper.py і
  замінюється на MathType-об'єкт у Word перед поданням
- References — Harvard (BSI), латиниця, ≥15, DOI ≥90%, Scopus/WoS ≥60%
"""
from __future__ import annotations

# ---------- Метадані ----------

UDC = "004.93"

TITLE_UA = (
    "Інваріантно-структурне навчання: формування концептів "
    "як динаміка гіперграфових атракторів"
)
TITLE_EN = (
    "Invariant structural learning: concept formation as "
    "hypergraph attractor dynamics"
)

KEYWORDS_UA = [
    "інваріантно-структурне навчання",
    "структурний атрактор",
    "формування концепту",
    "відстань редагування графа",
    "маловибіркове розпізнавання",
    "пояснювальний штучний інтелект",
    "MNIST",
    "редукція гіперграфа",
]

KEYWORDS_EN = [
    "invariant structural learning",
    "structural attractor",
    "concept formation",
    "graph edit distance",
    "few-shot recognition",
    "explainable AI",
    "MNIST",
    "hypergraph reduction",
]


# ---------- Автори ----------
# Порядок узгодити з керівником. Зазвичай виконавець — перший, супервайзор — останній.
# Поля з "?" — зібрати у співавторів (ORCID, Scopus ID).

AUTHORS = [
    {
        "surname_ua": "Лапін",
        "initials_ua": "М. О.",
        "full_name_ua": "Лапін Микита Олексійович",
        "full_name_en": "Mykyta Lapin",
        "degree_ua": "аспірант",
        "degree_en": "PhD student",
        "position_ua": "аспірант кафедри системного аналізу та інформаційно-аналітичних технологій",
        "position_en": "PhD student at the Department of Systems Analysis and Information-Analytical Technologies",
        "department_ua": (
            "кафедра системного аналізу та інформаційно-аналітичних технологій"
        ),
        "department_en": (
            "Department of Systems Analysis and Information-Analytical Technologies"
        ),
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "Mykyta.Lapin@cit.khpi.edu.ua",
        "orcid": "https://orcid.org/0009-0003-6307-1172",  # provided by author 2026-04-27. Previous itssi_paper_2025 value 0000-0003-2037-5587 was WRONG (chuzhyi profile).
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=60171161300",  # provided by author 2026-04-27
        # Override: default chain duplicates "аспірант"/"PhD student" (status in
        # degree + same word in position). For an aspirant, position implies status.
        "info_block_ua": (
            "аспірант кафедри системного аналізу та "
            "інформаційно-аналітичних технологій Національного технічного "
            "університету \"Харківський політехнічний інститут\" "
            "(Україна, м. Харків)"
        ),
        "info_block_en": (
            "PhD student at the Department of Systems Analysis and "
            "Information-Analytical Technologies, National Technical "
            "University \"Kharkiv Polytechnic Institute\" (Kharkiv, Ukraine)"
        ),
    },
    {
        "surname_ua": "Паржин",
        "initials_ua": "Ю. В.",
        "full_name_ua": "Паржин Юрій Володимирович",
        "full_name_en": "Yurii Parzhyn",
        "degree_ua": "доктор технічних наук",
        "degree_en": "Doctor of Sciences (Engineering)",
        "position_ua": "постдокторант Школи Комп'ютерних та Кібер Наук Університету Огасти",
        "position_en": "Postdoctoral Fellow at the School of Computer and Cyber Sciences, Augusta University",
        "department_ua": "Школа Комп'ютерних та Кібер Наук",
        "department_en": "School of Computer and Cyber Sciences",
        "org_ua": "Університет Огасти",
        "org_en": "Augusta University",
        "city_ua": "м. Огаста",
        "city_en": "Augusta",
        "country_ua": "США, Джорджія",
        "country_en": "Georgia, USA",
        "email": "yparzhyn@augusta.edu",
        "orcid": "https://orcid.org/0000-0001-5727-1918",  # verified 2026-04-27 via OpenAlex + ORCID public API: name "Yurii Parzhyn", current employment "Postdoctoral Fellow, School of Computer and Cyber Sciences, Augusta University". The previous itssi_paper_2025 value 0000-0002-5007-4076 has no public employments — wrong account.
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57224412390",  # verified 2026-04-27 via Parzhyn's ORCID profile external IDs (also: ResearcherID L-9151-2014)
        # Override the standard chain "{name} — {degree}, {org}, {position}, {city}, {country};"
        # with author-supplied phrasing (commit msg 2026-05-03).
        "info_block_ua": (
            "доктор технічних наук, постдокторант Школи Комп'ютерних та "
            "Кібер Наук Університету Огасти (США, Джорджія, м. Огаста)"
        ),
        "info_block_en": (
            "Doctor of Sciences (Engineering), Postdoctoral Fellow at the "
            "School of Computer and Cyber Sciences, Augusta University "
            "(Augusta, Georgia, USA)"
        ),
    },
    {
        "surname_ua": "Бохан",
        "initials_ua": "К. О.",
        "full_name_ua": "Бохан Костянтин Олександрович",  # TODO: confirm patronymic with co-author
        "full_name_en": "Kostiantyn Bokhan",
        "degree_ua": "кандидат технічних наук, доцент",
        "degree_en": "Candidate of Technical Sciences (PhD in Engineering), Associate Professor",
        "position_ua": "доцент кафедри системного аналізу та інформаційно-аналітичних технологій",
        "position_en": "Associate Professor at the Department of Systems Analysis and Information-Analytical Technologies",
        "department_ua": "кафедра системного аналізу та інформаційно-аналітичних технологій",
        "department_en": "Department of Systems Analysis and Information-Analytical Technologies",
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "kostiantyn.bokhan@khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0003-3375-2527",  # verified 2026-04-27 via OpenAlex (3 of team's own publications) and ORCID public API employment history. The previous itssi_paper_2025 value 0000-0002-9861-8911 actually belongs to Luis Alfonso Jiménez-Ortega — incorrect.
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57191592568",  # verified 2026-04-27 via Bokhan's ORCID profile external IDs (also: ResearcherID LIH-4638-2024)
        # Override: default chain duplicates "доцент"/"Associate Professor" (rank in
        # degree + same word in position). Keep the position phrase, drop the rank dup.
        "info_block_ua": (
            "кандидат технічних наук, доцент кафедри системного аналізу та "
            "інформаційно-аналітичних технологій Національного технічного "
            "університету \"Харківський політехнічний інститут\" "
            "(Україна, м. Харків)"
        ),
        "info_block_en": (
            "Candidate of Technical Sciences (PhD in Engineering), Associate "
            "Professor at the Department of Systems Analysis and "
            "Information-Analytical Technologies, National Technical "
            "University \"Kharkiv Polytechnic Institute\" (Kharkiv, Ukraine)"
        ),
    },
    {
        "surname_ua": "Перевозник",
        "initials_ua": "К. М.",
        "full_name_ua": "Перевозник Кирило Максимович",
        "full_name_en": "Kyrylo Perevoznyk",
        "degree_ua": "аспірант",
        "degree_en": "PhD student",
        "position_ua": "аспірант кафедри системного аналізу та інформаційно-аналітичних технологій",
        "position_en": "PhD student at the Department of Systems Analysis and Information-Analytical Technologies",
        "department_ua": "кафедра системного аналізу та інформаційно-аналітичних технологій",
        "department_en": "Department of Systems Analysis and Information-Analytical Technologies",
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "kyrylo.perevoznyk@cs.khpi.edu.ua",
        "orcid": "https://orcid.org/0009-0009-2327-1501",  # CORRECTED 2026-04-27 via Crossref author record co-authored with Parzhyn; co-occurrence with Parzhyn's verified ORCID confirms identity. Previous itssi_paper_2025 value 0000-0002-4668-6870 was WRONG (private profile, not actually Perevoznyk's).
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=59564678000",  # provided by author 2026-05-07 (originally as a review-profile URL with authorIds=59564678000); normalised to canonical authid/detail.uri form to match the other four authors. Was "-" up to 2026-04-27.
        # Override: default chain duplicates "аспірант"/"PhD student" (status in
        # degree + same word in position). For an aspirant, position implies status.
        "info_block_ua": (
            "аспірант кафедри системного аналізу та "
            "інформаційно-аналітичних технологій Національного технічного "
            "університету \"Харківський політехнічний інститут\" "
            "(Україна, м. Харків)"
        ),
        "info_block_en": (
            "PhD student at the Department of Systems Analysis and "
            "Information-Analytical Technologies, National Technical "
            "University \"Kharkiv Polytechnic Institute\" (Kharkiv, Ukraine)"
        ),
    },
    {
        "surname_ua": "Александрова",
        "initials_ua": "Т. Є.",
        "full_name_ua": "Александрова Тетяна Євгенівна",
        "full_name_en": "Tetiana Aleksandrova",
        "degree_ua": "доктор технічних наук, професор",
        "degree_en": "Doctor of Sciences (Engineering), Professor",
        "position_ua": (
            "завідувач кафедри системного аналізу та інформаційно-аналітичних "
            "технологій"
        ),
        "position_en": (
            "Head of the Department of Systems Analysis and Information-Analytical "
            "Technologies"
        ),
        "department_ua": (
            "кафедра системного аналізу та інформаційно-аналітичних технологій"
        ),
        "department_en": (
            "Department of Systems Analysis and Information-Analytical Technologies"
        ),
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "Tetiana.Aleksandrova@khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0001-9596-0669",  # verified 2026-04-29 via official KhPI page + AcademHub (REWRITE_PLAN Phase 1 step 3)
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57189376480",  # verified 2026-04-29 via author's KhPI profile + Scopus public lookup
    },
]


# ---------- Структурована анотація UA (1900–2200 знаків, включно з заголовками) ----------
# Підрахунок знаків (без пробілів між секціями-мітками) зробити перед подачею.

ABSTRACT_UA_SUBJECT = (
    "Предметом дослідження є формування концептів класів об'єктів у "
    "системах машинного навчання як процесу структурної та параметричної "
    "редукції гіперграфових представлень, а не як оптимізації функціонала "
    "втрат."
)
ABSTRACT_UA_GOAL = (
    "Побудувати альтернативний підхід статистичного навчання штучних "
    "нейронних мереж — без використання функції помилки (зворотне "
    "поширення), у якому реалізується інваріантне структурне навчання, "
    "де концепт класу визначається як структурний атрактор (нерухома "
    "точка монотонного оператора редукції на частково впорядкованому "
    "просторі гіперграфів), і підтвердити цю теорію на прикладі "
    "розпізнавання рукописних цифр."
)
ABSTRACT_UA_TASKS = (
    "(1) Формалізувати основу з аксіомами стабільності сегментації, "
    "строгої редуктивності, навчання за позитивними прикладами та "
    "локальності уваги; (2) довести збіжність і єдиність атрактора; "
    "(3) встановити інваріантність щодо порядку поглинання прикладів; "
    "(4) розкласти атрактор на структурний і параметричний рівні; "
    "(5) оцінити конвеєр на підмножині MNIST з цілісними контурами."
)
ABSTRACT_UA_METHODS = (
    "Гіперграфи отримуються скелетизацією бінарних контурів (Growing "
    "Neural Gas + Рамер–Дуглас–Пекер); концепти-атрактори формуються "
    "редукцією за анкорами — критичними точками контуру. Класифікація "
    "використовує порівнювач за відстанню редагування графа з "
    "вартостями ознак і логарифмічним апріорі за складністю. "
    "Тренувальна множина — 76 оригіналів MNIST, доповнених аугментацією "
    "(ротація ±10°, зсув ±10 %) до 805 примірників."
)
ABSTRACT_UA_RESULTS = (
    "Конвеєр навчає 13 концептів-атракторів з кількістю вузлів від 3 до "
    "15. З 8 707 допустимих зображень MNIST з цілісними контурами 8 685 "
    "утворили валідні скелетні графи; на цій валідній підмножині "
    "досягнуто точність 85,80 %, зважену влучність 89,31 %, повноту "
    "85,80 % та F1-міру 86,66 %. Структура помилок інтерпретована "
    "поконцептно: кожна помилка простежна до конкретного атрактора та "
    "діапазону ознак."
)
ABSTRACT_UA_CONCLUSIONS = (
    "Зафіксована продуктивність, досягнута без функціонала втрат і з трьох "
    "до дев’яти унікальних оригіналів на концепт-атрактор, підтверджує теоретичне "
    "твердження, що навчання є побудовою структурного атрактора, а не "
    "мінімізацією функціонала помилки. Основа дає принциповий шлях до "
    "пояснювальної маловибіркової класифікації та конструктивну "
    "альтернативу градієнтному навчанню."
)


# ---------- Structured Abstract EN (1900–2200 chars) ----------

ABSTRACT_EN_SUBJECT = (
    "The subject of study is the formation of object-class concepts in "
    "machine-learning systems as a process of structural and parametric "
    "reduction of hypergraph representations, rather than as the "
    "optimisation of a loss function."
)
ABSTRACT_EN_GOAL = (
    "To construct an alternative learning framework for artificial "
    "neural networks — without an error functional "
    "(back-propagation) — that realises invariant structural learning, "
    "where a class concept is defined as a structural attractor (the "
    "fixed point of a monotone reduction operator on a partially-ordered "
    "space of hypergraphs), and to confirm this theory on the recognition "
    "of handwritten digits."
)
ABSTRACT_EN_TASKS = (
    "(1) Formalise the framework with axioms of segmentation stability, "
    "strict reductivity, positive-only training, and locality of "
    "attention; (2) prove convergence and uniqueness of the attractor; "
    "(3) establish order-invariance of learning; (4) decompose the "
    "attractor into structural and parametric levels; (5) evaluate the "
    "pipeline on a complete-contour subset of MNIST."
)
ABSTRACT_EN_METHODS = (
    "Hypergraphs are obtained by skeletonising binary contours (Growing "
    "Neural Gas + Ramer–Douglas–Peucker); concept-attractors form via "
    "graph reduction over critical-point anchors. Classification uses a "
    "graph-edit-distance comparator with property costs and a "
    "complexity-adjusted log prior. The training set is 76 hand-picked "
    "MNIST originals, augmented (rotation ±10°, shift ±10 %) to 805 "
    "instances."
)
ABSTRACT_EN_RESULTS = (
    "The pipeline learns 13 concept-attractors with node counts in the "
    "range 3 to 15. Of 8 707 admissible complete-contour MNIST images, "
    "8 685 yielded valid skeletal graphs; on this valid set the pipeline "
    "attains accuracy 85.80 %, weighted precision 89.31 %, recall "
    "85.80 %, and F1-score 86.66 %. The error structure is interpretable "
    "per concept — every misclassification traces to a named attractor "
    "and feature range."
)
ABSTRACT_EN_CONCLUSIONS = (
    "The reported performance, achieved without a loss function and from "
    "three to nine originals per concept-attractor, supports the claim that "
    "learning is the construction of a structural attractor rather than "
    "the minimisation of an error functional. The framework offers a "
    "principled route to interpretable few-shot classification and a "
    "constructive alternative to gradient learning."
)


# ---------- Формули (Office Math / OMML, через pandoc) ----------
# Кожна формула — це numbered display equation у тілі статті §4.
# `latex` — джерело, з якого pandoc (через generate_paper.py) збирає
#   нативний Word equation object. Після відкриття у Word: MathType →
#   Convert Equations → Equations to MathType equations.
# `anchor_paragraph` — рядок-маркер всередині відповідного абзацу
#   §4.1 / §4.2 prose. Якщо абзац містить цей маркер, формула рендериться
#   як display equation відразу після цього абзацу.

FORMULAS: list[dict] = [
    {
        "id": "F1",
        "number": 1,
        "latex": r"H = (V,\ E_s,\ E_p)",
        "caption": "Hypergraph representation of an integral image.",
        "anchor_paragraph": "Subsection 4.1.1",
    },
    {
        "id": "F2",
        "number": 2,
        "latex": r"f_x = \tfrac{1}{N} \sum_{i=1}^{N} \mathbb{1}\!\left[x \in A_i\right]",
        "caption": "Frequency measure of a structural element.",
        "anchor_paragraph": "Subsection 4.1.3",
    },
    {
        "id": "F3",
        "number": 3,
        "latex": r"R \;=\; C \circ S \circ R_p",
        "caption": "Full reduction operator (parametric → selection → closure).",
        "anchor_paragraph": "The full reduction operator",
    },
    {
        "id": "F4",
        "number": 4,
        "latex": r"H_{t+1} \;=\; R\!\left(H_t \oplus_{\mu} H'\right)",
        "caption": "Learning iteration (cumulative aggregation followed by reduction).",
        "anchor_paragraph": "The learning iteration",
    },
    {
        "id": "F5",
        "number": 5,
        "latex": r"\Phi(H) \;=\; |V| + \lambda\,|E|",
        "caption": "Complexity functional used in Theorem 1.",
        "anchor_paragraph": "Theorem 1",
    },
    {
        "id": "F6",
        "number": 6,
        "latex": (
            r"R\!\left(C_K\right) \cong C_K, \quad "
            r"C_K \preceq C\ \text{whenever } R(C) \cong C, \quad "
            r"\exists\,t<\infty:\; R^t(H) \cong C_K"
        ),
        "caption": "Structural attractor — invariance, minimality, attraction (Definition 2).",
        "anchor_paragraph": "Definition 2 (structural attractor)",
    },
    {
        "id": "F7",
        "number": 7,
        "latex": r"\exists !\,C_K \;:\; C_K = R\!\left(C_K\right)",
        "caption": "Theorem 2 — uniqueness of the class attractor.",
        "anchor_paragraph": "Theorem 2 (uniqueness",
    },
    {
        "id": "F8",
        "number": 8,
        "latex": r"F(H) \;=\; \bigl\{\,x \in V : I(x) \geq \tau\,\bigr\}",
        "caption": "Attention operator (Definition 6).",
        "anchor_paragraph": "Definition 6 (attention operator)",
    },
    {
        "id": "F9",
        "number": 9,
        "latex": r"M_K \;=\; \bigl\{\,C_K^{(j)}\bigr\}_{\,j=1,\dots,n}, \quad n<\infty",
        "caption": "Self-organising subclass-attractor map of class $K$.",
        "anchor_paragraph": "self-organising map of attractors",
    },
    {
        "id": "F10",
        "number": 10,
        "latex": (
            r"d\!\left(C_K^{(i)},\,C_K^{(j)}\right) \geq \delta > 0 "
            r"\quad (i \neq j)"
        ),
        "caption": "Separability of distinct attractors in the neuron map.",
        "anchor_paragraph": "between distinct attractors",
    },
    {
        "id": "F11",
        "number": 11,
        "latex": r"d \;=\; \alpha\,d_S \;+\; \beta\,d_P",
        "caption": "Mixed pseudo-metric between attractors (structural + parametric).",
        "anchor_paragraph": "mixed pseudo-metric",
    },
    {
        "id": "F12",
        "number": 12,
        "latex": r"C_{i+1} \;=\; R\!\left(C_i,\ G_{i+1}\right)",
        "caption": "Implementation form: inductive concept-attractor update.",
        "anchor_paragraph": "the equation below",
    },
    {
        "id": "F13",
        "number": 13,
        "latex": (
            r"w(f,c) \;=\; "
            r"\dfrac{\text{SCALE\_STRENGTH}(f)}"
            r"{\text{range\_width}(f,c) + \varepsilon}, \quad "
            r"\sum_{f} w(f,c) = 1"
        ),
        "caption": "Range-based diagnostic weighting of features.",
        "anchor_paragraph": "range-based diagnostic weighting",
    },
    {
        "id": "F14",
        "number": 14,
        "latex": (
            r"\operatorname{sim}\!\left(H_{\text{test}},\,C\right) "
            r"\;=\; 1 \;-\; "
            r"\dfrac{\operatorname{GED}_{\text{upper}}\!"
            r"\left(H_{\text{test}},\,C\right)}"
            r"{\operatorname{GED}_{\text{upper}}\!"
            r"\left(H_{\text{test}},\,C\right) + "
            r"\max\!\left(n_{\text{test}},\,n_C\right)}"
        ),
        "caption": "Bounded similarity normalisation of the upper-bound graph-edit distance.",
        "anchor_paragraph": "bounded similarity normalisation",
    },
    {
        "id": "F15",
        "number": 15,
        "latex": (
            r"\operatorname{score}(C) \;=\; "
            r"\operatorname{sim}\!\left(H_{\text{test}},\,C\right) "
            r"+ \lambda \cdot \log \Phi(C)"
        ),
        "caption": "Final classification score with log-complexity prior.",
        "anchor_paragraph": "the maximum of",
    },
]


# ---------- Основні секції (кожна — список абзаців) ----------
# Кожен рядок у списку = окремий абзац у Word.
# Довжина секцій розрахована так, щоб сумарно вийшло ≥ 8 сторінок при 10pt/1.0.
# Для підстрахування: Intro ~0.5–1 стор., Literature ~1.5 стор., Aim ~0.3,
# Methods ~1.5, Results ~2.5–3 (ядро), Discussion ~1.0, Conclusions ~0.3.

SECTION_1_INTRO: list[str] = [
    "Modern machine-learning methods, and in particular neural-network "
    "models, rely heavily on the optimisation of error functionals and on "
    "statistical generalisation. Such approaches presuppose an external "
    "quality criterion, and the learning process is formalised as the "
    "minimisation of the discrepancy between a prediction and a given "
    "target. Despite the empirical success of statistical learning, this "
    "paradigm has fundamental limitations: dependence on the choice of "
    "loss function, sensitivity to the data distribution, and the "
    "requirement of large training samples.",

    "An alternative direction is to view learning as a process of "
    "endogenous structural self-organisation, in which the system does "
    "not minimise an external error but instead converges to an "
    "internally consistent state. The present work proposes a "
    "formalisation of this viewpoint, extending the architecture-of-"
    "information line of research (Parzhyn, 2025), based on hypergraph "
    "representations and dynamic structural reduction; the framework "
    "is referred to as Invariant Structural Learning.",

    "The central idea is that every observed object is represented as a "
    "hypergraph, and learning is the sequential accumulation and "
    "alignment of such hypergraphs followed by reduction. The alignment "
    "procedure maps elements of different hypergraphs into a shared "
    "structural space, producing a cumulative hypergraph in which the "
    "frequencies of element occurrence and their stability under "
    "reduction can be analysed.",

    "The key notion of the proposed theory is that of a structural "
    "attractor — an invariant structure to which the reduction process "
    "converges. Unlike classical attractors of dynamical systems, this "
    "object is defined not through trajectories in a continuous space "
    "but through the intersection of consistent structural invariants. "
    "It is shown below that the attractor admits an equivalent "
    "characterisation as the set of elements whose frequency in the "
    "cumulative carrier equals one — i.e. those that are always present "
    "— thereby linking the dynamic interpretation with a combinatorial "
    "one.",

    "The proposed approach differs from traditional learning methods in "
    "four principled ways: (i) there is no explicit error functional and "
    "no procedure for its minimisation; (ii) learning is interpreted as "
    "reduction and alignment of structures; (iii) invariants are formed "
    "endogenously, without external templates; (iv) order-invariance "
    "with respect to the presentation of training examples is achieved. "
    "Mathematically, the model relies on discrete structures "
    "(hypergraphs), partially ordered sets, and monotone reduction "
    "operators that converge to fixed points.",

    "The principal contributions of this work are the following. (1) A "
    "formal hypergraph-based model of learning by structural reduction "
    "is proposed. (2) The notion of a structural attractor is introduced "
    "and shown to coincide with the intersection of class invariants and "
    "with the frequency-one condition. (3) Theorems on convergence of "
    "the reduction process and on uniqueness of the attractor are "
    "proved. (4) Order-invariance of the learning result is established. "
    "(5) The attractor is shown to decompose naturally into a "
    "topological (structural) and a parametric level. In short, the "
    "work proposes an alternative theoretical foundation for machine "
    "learning in which structural invariants and attractor dynamics — "
    "rather than error optimisation — play the central role. This opens "
    "the way to building models oriented toward stability, "
    "interpretability, and learning under a limited number of examples.",

    "An empirical confirmation of the framework on a complete-contour "
    "subset of MNIST is presented in Section 5. A graph-edit-distance "
    "based concept-attractor classifier learns 13 attractors from 76 "
    "hand-picked originals — between three and nine per concept — "
    "expanded by parametric augmentation (random rotation within ±10° "
    "and shift within ±10 % of the canvas) to 805 training instances. "
    "Of 8 707 admissible images, 8 685 yielded valid skeletal graphs; on "
    "this valid set the system attains 85.80 % accuracy, 89.31 % "
    "weighted precision, 85.80 % recall and 86.66 % F1, "
    "demonstrating the few-shot behaviour predicted by the "
    "structure-versus-parameter decomposition theorems of Section 4.1 "
    "and the order-invariance corollary of Theorem 2.",
]

SECTION_2_LITERATURE: list[str] = [
    "Classical approaches to handwritten-digit recognition on MNIST "
    "(LeCun et al., 1998) define a clear accuracy ladder against which "
    "any new method should be assessed. Convolutional neural networks, "
    "from the canonical LeNet-5 architecture (LeCun et al., 1998) to "
    "modern residual variants, consistently exceed 99 % test accuracy "
    "on the full 60 000-image training set. Support-vector machines "
    "with Gaussian kernels reach approximately 98.6 % on standardised "
    "MNIST; on raw pixels without invariance augmentation the result "
    "is more modest. Multi-layer perceptrons with moderate-width "
    "hidden layers attain 97–98 % when trained with deslanting and "
    "affine augmentation (LeCun et al., 1998). A common feature of "
    "these methods is the requirement of tens of thousands of "
    "labelled examples and the absence of any built-in mechanism of "
    "explanation: the convolutional network's decision rests on "
    "linear combinations of feature maps whose interpretation by a "
    "human is only possible through post-hoc visualisation "
    "surrogates.",

    "A separate line of work targets the few-shot regime in which only "
    "a handful of labelled examples per class is available. Prototypical "
    "Networks (Snell et al., 2017) construct a class prototype as the "
    "mean embedding of the support examples in a latent space trained "
    "through episodic optimisation. Matching Networks (Vinyals et al., "
    "2016) employ an attention mechanism to weight the contribution of "
    "each support example, while Model-Agnostic Meta-Learning (Finn "
    "et al., 2017) seeks an initialisation of the parameters from "
    "which the model adapts to a new task in a few gradient steps. "
    "These methods are typically evaluated under the episodic protocol "
    "on Omniglot and miniImageNet rather than under the open-test MNIST "
    "protocol, so a direct numerical comparison with the present "
    "85.80 % accuracy is best read as a conceptual placement within the "
    "niche of interpretable few-shot classifiers rather than as a "
    "like-for-like benchmark. A common limit of this line is that, "
    "while these methods reduce the need for labelled data during "
    "adaptation, they do not eliminate the dependence on a large base "
    "corpus during pre-training, and the prototype in Prototypical "
    "Networks remains an opaque vector in a multi-dimensional space "
    "rather than an interpretable object that an expert could inspect.",

    "The dominant route to explainability for already-trained opaque "
    "models has been the construction of post-hoc surrogates. Minh et "
    "al. (2022), Hooshyar and Yang (2024), Rajabi and Etminani (2024) "
    "and Nawaz et al. (2025) survey this landscape and classify the "
    "methods by locality, model-specificity, and approximation type. "
    "The most widely used examples are LIME (Ribeiro et al., 2016), "
    "which approximates a non-linear model locally by a linear "
    "surrogate, and SHAP (Lundberg and Lee, 2017), based on "
    "Shapley-value attribution. Slack et al. (2020) demonstrated "
    "experimentally that LIME and SHAP are vulnerable to targeted "
    "attack: a classifier with overtly discriminatory behaviour can be "
    "made to appear neutral under both methods. Post-hoc explanations "
    "therefore offer no guarantee of fidelity to the actual logic of "
    "the model, motivating a research interest in models that are "
    "explainable by construction — that is, models in which the "
    "internal representation is itself an interpretable description.",

    "Graphs as image representations have a long history in computer "
    "vision, with skeletal graphs preserving the topology and basic "
    "geometry of an object while discarding redundant pixel detail, "
    "and confirming the competitiveness of graph representations on "
    "shape-recognition tasks. The modern direction of graph neural "
    "networks, including Graph Prototypical Networks (Ding et al., "
    "2022), transfers few-shot ideas to attributed graphs but again "
    "returns to latent-vector representations and does not preserve a "
    "directly inspectable concept representation. In a previous study "
    "by the present team (Lapin and Bokhan, 2025), the line of "
    "interpretable graph attractors was tested on a restricted "
    "six-class MNIST alphabet (digits 1, 2, 3, 6, 7, 9; 5 467 test "
    "images, 8 attractors) and attained 82.35 % accuracy with exact "
    "graph-edit-distance computation under a 60-second per-comparison "
    "budget. The present study extends that methodology to the full "
    "ten-class alphabet of MNIST under contour-completeness filtering, "
    "increases the alphabet to 13 attractors, introduces diagnostic "
    "feature weighting by the width of the reduced range, and switches "
    "to an iterative upper-bound graph-edit-distance with progressive "
    "refinement under a substantially smaller time budget — the "
    "combination of which yields the 85.80 % accuracy reported in "
    "Section 5.",

    "The matching of attributed graphs reduces formally to the search "
    "for a minimal sequence of edit operations (insertion, deletion, "
    "and substitution of vertices and edges) that transforms one graph "
    "into another. Sanfeliu and Fu (1983) introduced the notion of "
    "edit distance for attributed relational graphs and established it "
    "as a similarity metric for pattern recognition. Conte et al. "
    "(2004) summarised three decades of graph-matching methods and "
    "emphasised the trade-off between exact and approximate "
    "computation; exact graph-edit distance remains NP-hard. Riesen "
    "and Bunke (2009) proposed an efficient bipartite-assignment "
    "approximation that delivers a sub-optimal upper bound in "
    "polynomial time, enabling the use of the metric on graphs of "
    "practically useful size at the cost of optimality. More recent "
    "neural variants "
    "substitute the explicit edit costs with learnt embeddings: Piao "
    "et al. (2023) compute graph edit distance via neural graph "
    "matching, predicting an approximate distance from training pairs; "
    "Moscatelli et al. (2024) cast the underlying node-matching task "
    "with explicit emphasis on metric properties and explainability of "
    "the assignment; and Xie et al. (2024) extend the paradigm to "
    "federated few-shot graph classification. These methods "
    "substantially improve computational efficiency and scalability, "
    "yet most replace interpretable elementary edit costs with latent "
    "embeddings, weakening the readability of decisions at the level "
    "of \"which vertex was matched to which, and at what penalty.\" "
    "This leaves room for architectures in which the costs themselves "
    "remain interpretable by construction — the motivation for the "
    "approach proposed in the present work.",

    "The proposed framework draws on four well-established lines of "
    "cognitive-science evidence. The binding problem — how the brain "
    "combines distributed representations of attributes into coherent "
    "perceptual wholes — was formalised by von der Malsburg (1999) and "
    "remains a central problem of neural coding, with neural-syntax "
    "extensions by Buzsáki (2010); the structural-attractor model "
    "addresses it directly by encoding attribute relations as anchor "
    "connectivities (hyper-edges) within a single representation. The "
    "active-perception literature, originating with Yarbus (1967) and "
    "developed by Bajcsy et al. (2018) and Rucci and "
    "Victor (2015), shows that the trajectory of saccades is "
    "determined by the cognitive task as much as by the image, "
    "motivating attention-based anchor selection rather than "
    "exhaustive global matching. Single-neuron recordings (Quiroga "
    "et al., 2005; Quiroga, 2012) revealed concept-cell responses that "
    "are invariant to surface transformations of the stimulus, lending "
    "empirical support to the existence of class-level invariant "
    "representations of the type postulated in Definition 3 (concept). "
    "The dendritic-computation hypothesis (Magee, 2000; Häusser, 2001; "
    "Branco and Häusser, 2010; Larkum, 2022) holds that a neuron's "
    "dendritic tree implements substantial logical computation rather "
    "than acting as a passive integrator, supplying a biological "
    "substrate in which the algebra of structural reduction may be "
    "physically realised. These four lines collectively ground the "
    "non-statistical orientation of the proposed framework and "
    "motivate the architectural choices in Section 4.",

    "Summarising the review, three desired properties stand out, no "
    "combination of which currently has a satisfactory joint solution: "
    "(a) learning without backpropagation and without a large labelled "
    "corpus; (b) operation under a small number of examples per class; "
    "(c) local explainability of each decision at the level of the "
    "model itself. Classical convolutional and support-vector models "
    "deliver only accuracy; few-shot meta-learning methods deliver "
    "adaptation under a small support set but remain opaque; post-hoc "
    "explainable-AI methods deliver an approximation of behaviour "
    "rather than the underlying logic. The graph-attractor architecture "
    "proposed in the present work, trained without backpropagation, "
    "formally closes all three properties simultaneously — which "
    "defines the unsolved part of the problem and the rationale for "
    "the present study.",
]

SECTION_3_AIM: list[str] = [
    "The aim of this study is to provide an empirical confirmation of "
    "the Invariant Structural Learning framework formalised in "
    "Section 4.1 — and, in particular, of Theorems 1–3 — by "
    "constructing an end-to-end concept-attractor classifier and "
    "evaluating it on a complete-contour subset of MNIST, demonstrating "
    "that few-shot learning of structural attractors without "
    "backpropagation can yield competitive accuracy and decision-level "
    "local explainability simultaneously. The empirical task is "
    "deliberately restricted to images with contour-complete digit "
    "shapes, which corresponds to the psychophysiologically grounded "
    "baseline regime of recognition by full structural description; "
    "images with broken or fragmented contours are placed outside the "
    "scope of this study, since their recognition requires an "
    "additional mechanism of associative completion of a different "
    "mathematical nature that warrants independent treatment.",

    "To achieve this aim, the present work addresses the following "
    "five tasks. (1) Formalise the bitmap-to-attributed-graph "
    "extraction pipeline as a constructive instantiation of the "
    "framework's representation: convert each MNIST raster into an "
    "attributed graph that preserves the skeleton of the object "
    "together with the coordinates of critical (anchor) points and "
    "the geometric parameters of the contour segments. (2) Implement "
    "the concept-attractor formation operator as the iterative "
    "reduction of a set of example-graphs to a stable generalised "
    "structure realising R = C ∘ S ∘ R_p (Section 4.1.3 of the "
    "theoretical framework), and validate the parametric "
    "stratification predicted by the augmentation theory through "
    "controlled augmentation by random rotation in ±10° and shift in "
    "±10 % of the canvas. (3) Implement the classification step as a "
    "graph-edit-distance comparison between an unseen image and each "
    "concept-attractor, with diagnostic-weighted node-substitution "
    "costs over fourteen structural and geometric features and a "
    "graduated cost ladder for edge-edit operations, returning the "
    "winning attractor together with the similarity score and "
    "complexity-adjusted log-prior used in its selection. (4) Conduct "
    "an experimental evaluation of the proposed classifier on the "
    "manifest of complete-contour MNIST images (8 707 admissible "
    "images, 13 concept-attractors, 10 classes) and report accuracy, "
    "weighted precision, recall and F1-score, together with per-class "
    "metrics, top-confusion pairs, and the structure of "
    "misclassifications by named attractor and feature range. "
    "(5) Compare the obtained metrics with the published results of "
    "the principal classes of competing methods — classical statistical "
    "baselines, few-shot meta-learning methods, and the team's previous "
    "six-class graph-attractor study — and discuss the position of the "
    "present work within the niche of interpretable few-shot "
    "classifiers.",
]

SECTION_4_THEORY_PART_1: list[str] = [
    "Section 4 is organised in two parts. Section 4.1 develops the "
    "theoretical framework of Invariant Structural Learning over "
    "hypergraph representations, fixing the basic spaces, the "
    "reduction operator, the learning dynamics, and the central "
    "theorems of convergence and uniqueness. Section 4.2 reports the "
    "experimental implementation that confirms the framework on a "
    "complete-contour subset of MNIST, including the bitmap-to-graph "
    "extraction pipeline, the concept-attractor formation operator, "
    "the graph-edit-distance comparator, the diagnostic feature "
    "weighting, and a worked example of attractor formation for "
    "digit 7.",

    "Subsection 4.1.1 (Basic spaces and structures). The input space $X$ "
    "consists of raw input objects (e.g. MNIST images, geometric "
    "figures, contours, 2D and 3D models). The space $P$ of atomic "
    "structural primitives contains the basic building blocks of every "
    "representation; for MNIST these are the line segments "
    "approximating the contour and the points of contour bifurcation: "
    "endpoints, corners, intersections, and segment-junction points. "
    "The hypergraph space $Z$ formalises representations of a single "
    "neuron-detector. An element of $Z$ is a hypergraph $H$ defined "
    "by (1), where $V$ is the finite vertex set of structural "
    "primitives, $E_s$ the spatial / temporal edges encoding base "
    "connectivity, and $E_p$ the parametric hyper-edges encoding "
    "relations between the parameter sets of distinct vertices. The "
    "hypergraph is built as a layer over the base spatial graph; "
    "every vertex carries its own parameter group, so the parametric "
    "space is stratified over the structure.",

    "Subsection 4.1.2 (Extraction and measurements). The primitive "
    "detector $D$ models the work of the sensory system: it takes raw "
    "input and produces structural primitives. Its construction is "
    "not the subject of this work — $D$ is assumed to be given "
    "(Parzhin et al., 2022). Each measurement function $m_i$ returns "
    "the $i$-th parameter of a structural element, and $m$ collects "
    "all parameters of the graph. Measurement induces parameter modes "
    "for each vertex; each vertex is associated with its modal group "
    "— the set of parameters measured for it. The resulting "
    "multi-dimensional parameter space is given exogenously through "
    "coordinate systems and measurement scales; the segmentation of "
    "these parameter spaces during learning induces a metric. Examples "
    "for skeletonised MNIST contours are segment length, segment "
    "orientation, the angle between segments, and a point coordinate.",

    "Subsection 4.1.3 (Reduction). Parametric reduction $R_p$ is an "
    "ordering / compression operator on metrics. It does not change "
    "the spatial structure of the hypergraph but acts on the space of "
    "parametric relations: continuous values are replaced by discrete "
    "classes (segments). A clustering / quantisation operator $Q$ "
    "with stability parameter $\\varepsilon$ partitions the parameter "
    "space into stable segments $\\sigma_i$. Parameters may collapse "
    "to qualitative categories or disappear from the hypergraph "
    "entirely. The metric $d_i$ in the parameter space defines the "
    "segmentation structure. Axiom 1 (stability of segmentation) "
    "states that segmentation is idempotent: "
    "$Q \\circ Q = Q$ on the parameter space at the chosen "
    "$\\varepsilon$. Structural reduction $R_s$ is performed in three "
    "stages. First, the frequency measure $f_x$ of an element $x$ is "
    "defined as the proportion of class examples in which $x$ is "
    "present after alignment, with $f_x \\in [0, 1]$ and $N$ the "
    "number of accumulated class examples. Second, the "
    "structural-selection operator $S$ retains only the elements that "
    "are stable under reduction — those that occur in (almost) all "
    "class examples. The set $A$ of such elements (anchors) updates "
    "dynamically after each new example. Where the training set "
    "contains examples with incomplete attractor structure, the "
    "strict equality $f_x = 1$ is relaxed to $f_x \\geq \\theta$ with "
    "$\\theta$ a hyperparameter typically in $(0.7,\\,1]$; for clarity "
    "of exposition the theory below assumes $\\theta = 1$. Third, a "
    "closure / connectivity-restoration operator $C$ reconnects the "
    "surviving elements (anchors) into a single hypergraph, preserving "
    "spatial connectivity.",

    "Definition 1 (anchor). An element $x \\in V$ is called an anchor "
    "if its frequency measure satisfies $f_x = 1$ (equivalently "
    "$f_x \\geq \\theta$ for the relaxed regime). An anchor is a "
    "structural element (or parameter value) that is stably present "
    "in (almost) every class example. It serves as a fixed point "
    "around which the alignment of hypergraphs takes place; anchors "
    "are not removed by reduction and are reconnected by $C$ to "
    "preserve global structure after the deletion of non-critical "
    "vertices ('attractor noise'). For MNIST, anchors are the "
    "critical points of contour bifurcation — endpoints and corners.",

    "The full reduction operator $R$, defined by (3), is applied "
    "parametrically first, then structurally. Axiom 2 (strict "
    "reductivity and minimality) states that under $R$ the size of "
    "the hypergraph (in the number of elements and parameters) is "
    "non-increasing, and the resulting attractor is minimal: it "
    "contains no element with $f_x < 1$.",

    "Subsection 4.1.4 (Learning dynamics — cumulative, "
    "order-invariant). For a new positive example $x'$ the system "
    "constructs the following objects. The anchor matching $\\mu$ is "
    "a partial map $\\mu : A' \\to A_t$ aligning anchors of the new "
    "example with the existing accumulated anchors. The family "
    "$\\{\\mu\\}$ is consistent if sequential matching of anchors "
    "across examples does not depend on the order, i.e. there are no "
    "contradictory identifications of the same anchor. For cumulative "
    "aggregation, given the stored hypergraph $H_t$ and a new example "
    "$H'$, vertex aggregation identifies vertices via $\\mu$; spatial "
    "and parametric edges are pushed forward by $\\mu$. The combined "
    "hypergraph $H_t \\oplus_\\mu H'$ merges identified anchors and "
    "adds the remaining elements. The learning iteration is given "
    "by (4): the operator $\\oplus$ extends the structure, and $R$ "
    "reduces it. Under consistent "
    "$\\mu$ and a fixed rule for choosing $\\mu$, the result of the "
    "cumulative process is associative and commutative up to "
    "structural equivalence $\\cong$: two hypergraphs are equivalent "
    "if their segmented parameters coincide and their minimal "
    "structures are locally isomorphic around common anchors. "
    "Class-detector neurons are not required to construct "
    "hypersurfaces separating different classes; instead, an "
    "invariant hypergraph is built independently for each class. The "
    "algebraic reduction of hypergraphs may be interpreted as "
    "structural plasticity of active dendrites, where patterns of "
    "synaptic input on dendritic branches form complex logical "
    "elements that encode structural invariants (Larkum, 2022).",

    "Axiom 3 (positive-only learning). A class-detector neuron is "
    "trained only on positive examples of its class. Under input "
    "arrival, the system does not 'compute' a response but evolves "
    "until a stable state is reached; its dynamics depend on the "
    "measurement of its own structural components, modelling internal "
    "consistency without an external optimality criterion. All "
    "subsequent statements are derived from the axioms above.",

    "Subsection 4.1.5 (Principle of invariant reduction). The system "
    "evolves towards reduced structural redundancy while preserving "
    "invariants until it reaches a minimal fixed structure. The "
    "principle does not rest on gradient optimisation or on classical "
    "variational principles. Instead, learning is governed by a "
    "monotone reduction operator on a partially-ordered space of "
    "structures that converges to minimal invariant fixed points. A "
    "unified hierarchy of segmentations of coordinate systems and "
    "measurement scales, $\\sigma^{(k)}$, is introduced exogenously "
    "(modelling self-organisation of segments in biological neural "
    "structures); higher $k$ denotes coarser ('more general') "
    "segments. Transition operators between levels are quantisation "
    "operators at each level. A partial order $\\preceq$ is defined "
    "on $Z$ (Davey and Priestley, 2002): reflexive and transitive "
    "(transitivity follows from inclusion and from order on the "
    "segmentation hierarchy). An invariance functional $\\mathrm{Inv}$ "
    "induces a closure analogous to that of Formal Concept Analysis "
    "(Ganter and Wille, 1999). Reduction operators are expressed "
    "through segments: parametric reduction passes to a coarser level; "
    "structural reduction is the composition $C \\circ S \\circ R_p$. "
    "Classical neural networks lose the topological structure of an "
    "image, whereas the proposed framework solves the classical "
    "neurobiological binding problem by preserving anchor "
    "connectivities (hyper-edges) inside the attractor (von der "
    "Malsburg, 1999). A discrete invariance gradient — geometrically "
    "a vector in the segmentation hierarchy — denotes the direction "
    "of increasing generalisation. Invariants may be added or removed "
    "(false ones), but the true invariants are preserved: the "
    "dynamics are not monotone, yet the sequence of invariant sets "
    "converges to a stable structural core $E^*$. Extremality is "
    "induced by the operator and the order, not by an external "
    "optimality functional, in contrast to the loss functions of "
    "statistical neural networks (Buzsáki, 2010).",
]


SECTION_4_THEORY_PART_2: list[str] = [
    "Subsection 4.1.6 (Structural attractor and concept). The central "
    "object is the structural attractor: an invariant structure that "
    "is the fixed point of the reduction operator and that defines "
    "the internal model of a class.",

    "Definition 2 (structural attractor). Let $K$ be a class of "
    "objects, $Z$ the hypergraph space, and $R$ the reduction "
    "operator. The structural attractor of class $K$ is a hypergraph "
    "$C_K$ satisfying: (i) invariance — $R(C_K) \\cong C_K$; "
    "(ii) structural minimality — for every $C \\in Z$ with "
    "$R(C) \\cong C$ one has $C_K \\preceq C$; (iii) attraction — for "
    "every representation $H \\in Z$ of class $K$ there exists a "
    "finite $t$ such that $R^t(H) \\cong C_K$.",

    "The attractor $C_K$ is the fixed point of $R$, the minimal "
    "carrier of the invariant structure, the limit of learning, and "
    "the canonical form of class objects. Learning is therefore the "
    "reduction of various object representations to a unified "
    "structural normal form.",

    "Definition 3 (concept). A concept is the structural attractor of "
    "a perceived integral image — i.e. its internal model. A concept "
    "is therefore an endogenous ontological object for the system. "
    "Models with a memory of structural attractors form a separate "
    "class of self-organising dynamical systems (Glansdorff and "
    "Prigogine, 1971; Strogatz, 2015); biological neurons and neural "
    "structures are one example. The proposed model admits a "
    "neurobiological interpretation in which (a) the attractor "
    "corresponds to a stable activation pattern, (b) anchor elements "
    "are realised as stable synaptic configurations, and (c) reduction "
    "reflects the selection of stable structures in dendritic trees. "
    "This interpretation is illustrative rather than a direct "
    "biological claim. Self-organisation here refers to the modelled, "
    "not the physical, process; in particular, primitive detectors, "
    "coordinate systems and scales are exogenous, while reduction "
    "operators model the energy dynamics of natural self-organisation.",

    "Theorem 1 (convergence of $R$). Conditions: (1) $Z$ is a "
    "partially-ordered hypergraph space; (2) $R : Z \\to Z$ satisfies "
    "Axioms 1–2 (segmentation stability, strict reductivity and "
    "minimality); (3) the complexity functional $\\Phi$ defined by "
    "(5) is integer-valued and bounded below by $0$. Sketch of "
    "proof. Step 1 (decreasing complexity): "
    "on every non-stationary iteration $\\Phi(R(H)) < \\Phi(H)$ by "
    "Axiom 2. Step 2 (finiteness): a strictly decreasing sequence of "
    "natural numbers is finite. Step 3 (stabilisation): the sequence "
    "$(R^t H)_{t \\geq 0}$ reaches a fixed point in finitely many "
    "steps. Conclusion: there exists $C_\\infty$ such that "
    "$C_\\infty = R(C_\\infty)$, with $t^* \\leq \\Phi(H_0)$ bounding "
    "the number of steps to convergence by the initial complexity. "
    "Corollary 1 (convergence to a class attractor). If a unique "
    "structural attractor $C_K$ is induced by class $K$, then for "
    "every $H \\in Z$ of class $K$ there exists a finite $t$ such "
    "that $R^t(H) \\cong C_K$.",

    "Theorem 2 (uniqueness of $C_K$). Conditions: (1) all class "
    "examples are anchor-connected, i.e. for any pair $(H_i, H_j)$ "
    "of class examples there is a chain of common anchors linking "
    "them through $\\mu$-consistent matchings; (2) $R$ is monotone "
    "and minimal (Axioms 1–2); (3) the dynamics of cumulative "
    "composition is order-independent. Sketch of proof. Step 1 "
    "(convergence): by Theorem 1, $R^t(H)$ stabilises at a fixed "
    "point. Step 2 (order-independence): the frequency function "
    "$f_x$ depends only on the set of accumulated examples, not on "
    "the order of presentation; hence the set $\\{x : f_x = 1\\}$ is "
    "order-independent. Step 3 (fixed-point formalisation): by the "
    "selection axiom, the vertex set of the fixed point equals the "
    "set of elements with $f_x = 1$; the full attractor is the "
    "closure of this vertex set. Step 4 (uniqueness): "
    "anchor-connectivity guarantees consistency of the matching maps "
    "$\\mu$ over the whole class (analogously to local-to-global "
    "consistency in sheaf theory, Bredon, 1967), so the resulting "
    "structure $C_K$ is unique up to $\\cong$. Conclusion: there "
    "exists a unique $C_K$ such that $C_K = R(C_K)$ and $C_K$ is "
    "independent of the order of presentation.",

    "Subsection 4.1.7 (Few-shot learning). Consider a subset "
    "$T \\subset K$. The covering condition requires every element "
    "of the attractor to be present in at least one example from $T$. "
    "Definition 4 (sufficient covering set): $T$ is a sufficient "
    "covering set if (1) the covering condition holds, and "
    "(2) anchor-connectivity is preserved on $T$ — the overlap "
    "hypergraph of anchors of $T$ is connected, so all examples from "
    "$T$ can be matched through common anchors. Corollary 2: if $T$ "
    "is a sufficient covering set, then all elements of the attractor "
    "survive reduction on $T$, and the attractor obtained from $T$ "
    "coincides with $C_K$. A nesting property follows: for every "
    "$x \\in K$ there is a map $\\iota : C_K \\to H(x)$ preserving "
    "structural relations — the attractor is embedded into every "
    "example. Thus the attractor may be determined not by the entire "
    "class but by a small subset of its carriers, which corresponds "
    "to the psychology of human perception and opens a route to "
    "few-shot learning. A sufficient covering set ensures the "
    "recoverability of the attractor structure but does not, in "
    "general, guarantee its uniqueness. The stronger notion of an "
    "identifying set is therefore introduced. Definition 5 "
    "(identifying set): $T$ is an identifying set if (i) it covers "
    "all elements of the attractor; (ii) it covers all anchor "
    "relations (edges); and (iii) anchor-connectivity holds. $T$ is "
    "then a minimal covering: it induces a unique fixed point of $R$. "
    "Every identifying set is a sufficient covering set; the converse "
    "is false in general. Corollary 3 (reconstruction): if the "
    "attractor is embedded in every class example and there exists "
    "an identifying set $T^*$, then the attractor obtained from "
    "$T^*$ equals $C_K$ up to $\\cong$. The cardinality of $T$ is "
    "not what matters — its covering ability does. Two or three "
    "examples may be sufficient, while a hundred may not. With a "
    "finite number of anchors and finite connectivity, there is a "
    "finite minimal subset of examples that recovers the attractor "
    "of the class.",

    "Subsection 4.1.8 (The role of augmentation). Augmentation is "
    "interpreted as a parametric-exploration operator on the "
    "structure. Given an example $H_x = (V, E_s, E_p)$, augmentation "
    "produces a family $\\{H_x^{(i)}\\}_i$ with structures equivalent "
    "up to matching and parameters varying continuously. Augmentation "
    "builds the segmentation $\\sigma_i$ from the observed values: "
    "parametric variations are assumed to be independent of the "
    "structure — variations obtained from one example are "
    "representative of the entire class on parameters. Learning "
    "therefore decomposes into two levels. (1) Structural level: "
    "from a small subset $T$, the structural skeleton — anchors and "
    "their relations — is recovered. (2) Parametric level: "
    "augmentation produces a parametric stratification — for each "
    "anchor, an interval / segment of admissible values. The full "
    "attractor combines structural covering (small $T$) and "
    "parametric covering (augmentation). In contrast to classical "
    "models, where augmentation enlarges the sample to reduce "
    "overfitting, here augmentation constructs the parametric "
    "structure (and therefore the metric) through segmentation. "
    "Structural examples define the topology; augmentation defines "
    "the geometry (the metric). Augmentation thus acts as a "
    "metrisation operator. The induced metric on the attractor is "
    "defined locally for each parameter through its segmentation "
    "$\\sigma_i$, and globally by aggregation over anchors. "
    "Properties of the metric: (1) it is induced by segmentation; "
    "(2) it is invariance-respecting — invariants contribute zero "
    "variation; (3) it is consistent — defined only on anchors and "
    "matched through $\\mu$. The metric is therefore not external "
    "(exogenous) but emerges endogenously: structure → segmentation "
    "→ metric. This is the converse of metric learning, contrastive "
    "learning and kernel methods.",
]


SECTION_4_THEORY_PART_3: list[str] = [
    "Subsection 4.1.9 (Attention mechanism and anchors). The hardest "
    "practical problem of structural learning is hypergraph matching. "
    "It is solved here via an attention operator over anchor "
    "structural points.",

    "Definition 6 (attention operator). The attention operator $F$ "
    "is a local element-selector that picks a subset "
    "$F(H) \\subset V$ used to build the matching, on the basis of "
    "local informativeness — for example, points of 'capture' of an "
    "MNIST contour. A typical instance is given by (8), with $I$ a "
    "measure of local informativeness and $\\tau$ a threshold. The "
    "operator "
    "selects elements with extreme parameter values for the given "
    "structure or with rarity / contrast (points of maximal "
    "informativeness). Instead of solving the global hypergraph "
    "isomorphism problem (which is graph-edit-distance based, Piao "
    "et al., 2023), the attention operator restricts matching to "
    "$F(H)$, turning the task from a global combinatorial "
    "optimisation into a local consistency problem and avoiding the "
    "NP-hardness of exact graph-edit distance (Conte et al., 2004). "
    "The matching $\\mu$ is therefore defined only on $F(H)$.",

    "Axiom 4 (locality of attention and anchor consistency). (1) The "
    "attention operator $F$ is local — it depends only on $H$ "
    "restricted to $F(H)$. (2) Anchors are invariant under "
    "reduction: $F(R(H)) = R(F(H))$ up to structural equivalence. "
    "The attention operator depends on a top-down modulation of the "
    "task; it models the active-perception process in the brain "
    "(Yarbus, 1967; Bajcsy et al., 2018; Rucci and "
    "Victor, 2015). Yarbus demonstrated experimentally that the "
    "trajectory of saccades is determined not only by image "
    "properties but also by the cognitive task; in the present "
    "context this confirms that the choice of anchor points is a "
    "goal-directed action of $F$ that minimises perceptual "
    "redundancy.",

    "Subsection 4.1.10 (Neuron map). A class $K$ is represented by a "
    "self-organising map of attractors (9) — a finite set of "
    "structural attractors (neuron-detectors) corresponding to "
    "subclasses or stable variations within the class. Each subclass "
    "attractor $C_K^{(j)}$ satisfies $C_K \\preceq C_K^{(j)}$: the "
    "class attractor is the minimal invariant substructure embedded "
    "into every subclass attractor. The pseudo-distance $d$ on the "
    "structural space is bounded below between distinct attractors — "
    "see (10) — ensuring structural distinguishability. The class "
    "map has a strict hierarchy: the central neuron is the "
    "class-detector concept; $d$ measures the edit distance between "
    "this central hypergraph and the hypergraphs of subclass "
    "detectors or memorised individual examples. Subclass attractors "
    "form when special novelty conditions are met (their formulation "
    "lies outside the scope of this work; Parzhin et al., 2020).",

    "Theorem 3 (self-organisation of the attractor map). Conditions: "
    "(1) the reduction operator $R$ satisfies the axioms "
    "(monotonicity, invariant selection, closure of connectivity); "
    "(2) the learning dynamics are given by "
    "$H_{t+1} = R(H_t \\oplus_\\mu x_{t+1})$ and, for each class "
    "$K$, a structural attractor $C_K$ exists by Theorem 2; (3) a "
    "pseudo-metric $d$ on the structural space, distinguishing "
    "structures up to $\\cong$, is given; (4) a separability "
    "threshold $\\delta > 0$ is fixed. Conclusions: in the course of "
    "learning, a finite map $M_K = \\{C_K^{(j)}\\}_{j=1,\\dots,n}$ "
    "forms endogenously, possessing (i) structural nesting "
    "($C_K \\preceq C_K^{(j)}$ for every $j$); (ii) separability "
    "($d(C_K^{(i)}, C_K^{(j)}) \\geq \\delta$ for $i \\neq j$); "
    "(iii) attraction (every example of the class converges under "
    "$R$ to some $C_K^{(j)}$); (iv) self-organisation ($M_K$ is not "
    "given a priori but emerges as the set of stable fixed points); "
    "(v) finiteness ($n < \\infty$). Sketch of proof. Step 1 "
    "(convergence to fixed points): by Theorem 1, every learning "
    "trajectory stabilises at a fixed point of $R$. Step 2 "
    "(character of fixed points): by the selection axiom, every "
    "limit structure equals the closure of $\\{x : f_x = 1\\}$ on "
    "its trajectory; different example subsets may induce different "
    "attractors. Step 3 (emergence of new attractors): a new example "
    "$x'$ with anchor system $A'$ compatible with the current "
    "attractor $C^{(j)}$ yields the same attractor; otherwise $R$ "
    "produces a new fixed point $C^{(j+1)} \\neq C^{(j)}$. Step 4 "
    "(endogenous map formation): iterating across the example "
    "sequence yields a set of fixed points; no attractor is given "
    "exogenously. Step 5 (structural nesting): by Theorem 2, "
    "$C_K \\preceq C_K^{(j)}$ for every $j$ (the class attractor is "
    "the common substructure). Step 6 (separability): by the "
    "threshold condition $d \\geq \\delta$, attractors do not merge "
    "under $R$. Step 7 (finiteness): the structural space is finite "
    "by the boundedness of vertex counts and segmentations of "
    "parameters; hence $n < \\infty$. Conclusion: the attractor map "
    "$M_K = \\{C_K^{(j)}\\}$ arises as the set of stable fixed "
    "points of $(R, \\oplus_\\mu, d)$, and its structure is "
    "determined endogenously by these three operators rather than by "
    "any external function. The map is therefore the result of "
    "dynamic partitioning of the example space into basins of "
    "attraction.",

    "Subsection 4.1.11 (Competition between attractors). A distance "
    "between attractors enables Winner-Take-All competition both "
    "inside the map of one class and across maps of different "
    "classes. For this, every neuron-detector's response must "
    "aggregate information about the structural and parametric "
    "content of its attractor. This view, in our opinion, throws "
    "light on the neural-coding question — in particular on the "
    "binding problem (von der Malsburg, 1999) and on the formation "
    "of invariant conceptual representations (Quiroga et al., 2005; "
    "Quiroga, 2012) — by suggesting that the basic element of the "
    "neural code is not the temporal frequency of spikes but the "
    "topology of coincidences in the dendritic tree (Larkum, 2022). "
    "For a finite set of attractors the distance $d$ is a mixed "
    "pseudo-metric (11) combining discrete structures and parameters, "
    "where $d_S$ is structural edit distance and $d_P$ parametric "
    "distance after matching. The weights $\\alpha, \\beta$ are "
    "determined "
    "empirically and play a decisive role. Following Riesen (2015), "
    "structural distance is defined through the partial matching "
    "$\\mu \\in \\Pi(C, C')$ as a sum of three terms — unmatched "
    "elements of $C$, unmatched elements of $C'$, and the size of "
    "the matched substructure — yielding the count of elements that "
    "cannot be put into correspondence. Parametric distance is "
    "computed after matching, either directly or through segments "
    "$\\sigma_i$. The function $d$ satisfies non-negativity, "
    "symmetry and identity ($d(C, C) = 0$); $d(C_1, C_2) = 0$ "
    "implies $C_1 \\cong C_2$ (pseudo-metric, since identification "
    "is up to $\\cong$). Together these properties formally define "
    "a metric between attractors that supports the Winner-Take-All "
    "competition.",
]


SECTION_4_METHODS_PART_1: list[str] = [
    "Section 4.2 documents how each abstract construct of Section 4.1 — "
    "the structural primitive vocabulary, the reduction operator $R$, "
    "the parametric stratification of augmentation, and the "
    "attention-driven anchor selection — is realised in code and "
    "tested empirically. The theoretical framework of Section 4.1 is "
    "formulated over hypergraphs $H = (V, E_s, E_p)$ with parametric "
    "hyper-edges $E_p$ binding the parameter sets of distinct "
    "vertices. In the present implementation the parametric layer "
    "collapses to a per-vertex attribute group rather than to an "
    "explicit hyper-edge: every vertex $v \\in V$ carries a vector of "
    "fourteen continuous and categorical attributes (Table 1) rather "
    "than participating in a separately stored $E_p$ relation. The "
    "base graph $(V, E_s)$ is therefore a directed attributed graph "
    "in NetworkX, and the hyper-edge layer reappears implicitly "
    "through the diagnostic-weighted node-substitution cost "
    "described later in this section, which couples attributes "
    "across matched vertex pairs at comparison time. This is a "
    "representational "
    "simplification of Section 4.1, not a theoretical departure: the "
    "hypergraph terminology is retained for the general formalism of "
    "Section 4.1, while 'graph' is used in the descriptions of "
    "Section 4.2 onward where the simplification holds.",

    "The conversion of a raster image into an attributed graph is "
    "implemented as a three-stage pipeline. First, the image is "
    "binarised at a fixed intensity threshold separating foreground "
    "from background pixels. Second, the Growing Neural Gas algorithm "
    "(Fritzke, 1995) adaptively places vertices along the medial line "
    "of the object, producing a topologically faithful skeleton that "
    "respects the local distribution of foreground pixels. Third, the "
    "Ramer–Douglas–Peucker algorithm (Douglas and Peucker, 1973) "
    "removes intermediate vertices whose deviation from the chord "
    "between their neighbours falls below a tolerance, retaining only "
    "structurally significant points: endpoints, corner points, and "
    "junction (bifurcation) points.",

    "The resulting representation is a bipartite directed attributed "
    "graph. Vertices of the first kind — Point nodes — represent the "
    "critical points of the skeleton and instantiate the "
    "$V_{\\text{anchor}}$ of Definition 1. Vertices of the second "
    "kind — Vector nodes — represent the directed segments between "
    "adjacent Point nodes and instantiate the structural edges $E_s$ "
    "after lifting them to first-class objects (so that each segment "
    "can carry its own parameter group, as required by Section 4.1's "
    "stratification of the parametric space over the structure). "
    "Spatial coordinates of all vertices are normalised against the "
    "centre of mass of the foreground mask into a symmetric range, "
    "yielding invariance to translation in the image plane.",

    "Every vertex carries a fourteen-element feature vector. The "
    "features fall into four conceptual categories. (i) "
    "Spatial-geometric: normalized_x, normalized_y — horizontal and "
    "vertical coordinates relative to the centroid; "
    "distance_to_centroid — radial distance. (ii) Orientational, "
    "defined for Vector nodes only: horizontal_direction, "
    "vertical_direction — categorical orientation along the two "
    "coordinate axes; angle_with_ox — orientation angle in degrees "
    "(also defined on Point nodes as the convergence angle of "
    "incident segments). (iii) Structural-functional, defined for "
    "Point nodes only: is_endpoint, is_corner — Boolean flags "
    "indicating that the node terminates a single segment or "
    "registers a direction change exceeding a fixed threshold "
    "respectively; junction_angle_min — the smallest internal angle "
    "at a bifurcation point. (iv) Neighbourhood-topological: "
    "length_ratio_to_max — segment length normalised by the longest "
    "segment in the graph; eccentricity — graph-theoretic "
    "eccentricity of the node (maximum hop-distance to any other "
    "node); avg_neighbor_vector_length — mean normalised length of "
    "incident segments; neighbor_endpoint_count, "
    "neighbor_junction_count — degree-by-role counts of adjacent "
    "Point nodes. The full set is summarised in Table 1. Features "
    "defined on only one node type — for example, the orientational "
    "triple on Vector nodes or the structural-functional triple on "
    "Point nodes — are silently skipped at comparison time when "
    "matching against a node of the other type, so that the cost "
    "decomposition introduced later in this section always "
    "operates on the intersection of features actually present on "
    "both sides of a "
    "candidate substitution.",
]

SECTION_4_METHODS_PART_2: list[str] = [
    "A concept-attractor is formed inductively by iterative application "
    "of the reduction operator $R = C \\circ S \\circ R_p$ of "
    "Section 4.1 to a small set of skeletal example-graphs of the "
    "same class. At each step the operator takes the current concept "
    "state and a fresh example-graph and returns an updated concept "
    "that generalises both inputs. The schematic action of the "
    "operator is given by the equation below: the new concept state "
    "is the result of reducing the pair (current concept state, new "
    "example).",

    "Generalisation is component-wise. For continuous attributes, an "
    "admissible interval bounded by the smallest and largest value "
    "seen so far across absorbed examples is built and the typical "
    "value is preserved at the centre — this realises the "
    "parameter-segmentation $\\sigma_i$ of Section 4.1.3. For "
    "categorical attributes, the intersection of admissible values "
    "is kept. For list-valued attributes (when present), set "
    "intersection is applied. Structural matching of nodes between "
    "the current concept and the new example uses the same "
    "graph-edit-distance comparator employed at classification time, "
    "ensuring that the formal procedures of training and "
    "classification share the same kernel of similarity. After "
    "several examples the iteration ceases to add new vertices and "
    "merely widens the intervals of the existing ones, signalling "
    "that the sequence has reached a fixed point of $R$ — the "
    "structural attractor $C_K$ of class $K$ (Definition 2).",

    "The role of augmentation in this work is the constructive "
    "realisation of Section 4.1.8 of the theoretical framework, not "
    "the classical reduction of overfitting. Each handpicked original "
    "example $H_x$ is expanded into a family $\\{H_x^{(i)}\\}_i$ of "
    "variants whose structures are equivalent up to anchor matching "
    "and whose continuous parameters vary independently. The variants "
    "are produced by an internal helper that rotates each original "
    "by an angle drawn uniformly from $[-10°, +10°]$ and shifts it "
    "by an offset drawn uniformly from $[-10\\%, +10\\%]$ of the "
    "canvas dimensions, with a black background fill outside the "
    "rotated mask. The number of variants per original ranges "
    "between five and ten depending on the concept; full "
    "per-concept augmentation counts are reported in Table 2.",

    "This produces three theoretical effects, each predicted by "
    "Section 4.1.8. First, the augmented family stresses the bounds "
    "of the admissible coordinate intervals on each anchor and "
    "tightens the diagnostic-weight estimation below; without "
    "augmentation, an interval estimated from three to nine "
    "handpicked originals collapses to a near-degenerate width on "
    "most coordinates and the diagnostic weight saturates uniformly "
    "across features. Second, the segmentation $\\sigma_i$ of each "
    "parameter is forced to refer to a stable interval rather than a "
    "single point, instantiating the metric-from-segmentation "
    "principle (structure → segmentation → metric) directly: the "
    "post-reduction interval width controls the per-feature "
    "contribution to the substitution cost, and a narrow width "
    "receives a higher weight at comparison time. Third, the "
    "augmented family enforces order-invariance of learning "
    "empirically (Theorem 2): once the originals are merged in any "
    "order with their variants, the resulting attractor is invariant "
    "under permutation of the merge order up to $\\cong$, because "
    "the frequency-one set on the cumulative carrier is "
    "order-independent. The augmentation contract is therefore not "
    "'make the training set bigger' but 'make the metric measurable "
    "from data'.",

    "Classification of an unseen image reduces to computing an upper "
    "bound on the graph-edit-distance between the test image's "
    "skeletal graph and each concept-attractor in the alphabet. The "
    "implementation uses the iterative upper-bound generator "
    "optimize_graph_edit_distance from NetworkX (Hagberg, Schult and "
    "Swart, 2008), which is initialised by the bipartite-assignment "
    "polynomial-time approximation (Riesen and Bunke, 2009) and "
    "monotonically refines the upper bound by enumerating alternative "
    "vertex correspondences. After a fixed time budget — 15 seconds "
    "per concept comparison in the campaign — the procedure halts and "
    "returns the best upper bound obtained. The returned value is "
    "therefore an anytime estimator: it does not guarantee the global "
    "graph-edit-distance minimum but, on graphs of the size and "
    "structure of the trained alphabet (3 to 15 anchor nodes), "
    "stabilises near the optimum within the time budget on more than "
    "99 % of comparisons. Edge handling is intentionally simplified: "
    "any pair of edges is considered compatible, edge deletion costs "
    "MINOR, edge insertion is free, and no explicit "
    "attribute-substitution is computed at the edge level. All "
    "structural penalty therefore concentrates at the vertex level "
    "through the cost ladder below and the diagnostic weighting "
    "below.",

    "Edit operations are charged through a six-level "
    "monotonically-increasing ladder that assigns one cost class per "
    "qualitative match category: NO_COST = 0.00 for an exact "
    "attribute match, MINOR = 0.65 for an absent vertex or edge "
    "(deletion / insertion of one side), GENERAL = 0.75 for a "
    "moderate attribute deviation, SEVERE = 1.00 for a severe "
    "attribute deviation, NO_MATCH = 1.50 when a feature is present "
    "on one node only, and IMPOSSIBLE = 10.00 for label mismatch or "
    "a forbidden insertion. The ladder values are designer-chosen "
    "round numbers under the constraint MINOR < GENERAL < SEVERE < "
    "NO_MATCH < IMPOSSIBLE; only MINOR = 0.65 is empirically "
    "anchored as a load-bearing finding of a prior tuning study. The "
    "ratio NO_MATCH : MINOR ≈ 2.3 enforces that having a feature on "
    "one side and not on the other costs more than two structural "
    "deletions, motivating the comparator to prefer like-for-like "
    "matches over forced cross-type substitutions. The IMPOSSIBLE "
    "sentinel acts as a hard barrier that removes Point ↔ Vector "
    "substitutions from the optimisation entirely.",

    "Within each candidate vertex substitution, the comparator must "
    "aggregate the per-feature cost contributions into a single "
    "substitution cost. Uniform aggregation ($1/N$ per feature) was "
    "found in earlier ablations to dilute the contribution of "
    "strongly diagnostic features as soon as the feature list grows "
    "beyond five entries. The mitigation is a range-based diagnostic "
    "weighting of features, computed per-concept-per-feature from "
    "the reduced interval width (defined below). Here "
    "$\\text{SCALE\\_STRENGTH}(f)$ is a fixed per-feature multiplier "
    "($1.0$ by default; reduced to $0.3$ for redundant features such "
    "as cycle_count), $\\text{range\\_width}(f,c)$ is the "
    "post-reduction interval width of feature $f$ on concept $c$, "
    "and $\\varepsilon$ is a stabilisation parameter ($1.0$ in the "
    "present campaign) that prevents division by zero on "
    "degenerate-width features. Categorical features take a constant "
    "weight independent of width. The final node-substitution cost "
    "is the weighted sum of per-feature attribute costs determined "
    "by the cost ladder. A narrow interval — that is, a feature "
    "whose value is stable across all absorbed originals and their "
    "augmented variants — produces a high weight, enforcing that "
    "the comparator pays attention to the features the reduction "
    "operator has already established as diagnostic.",

    "The final similarity score is constructed by a bounded "
    "similarity normalisation of the upper-bound edit distance on "
    "the size of the larger of the two compared graphs (formula "
    "given below), with $n$ equal to the count of nodes plus edges "
    "of the corresponding graph. The denominator $\\operatorname{"
    "GED}_{\\text{upper}} + \\max(n_{\\text{test}}, n_C)$ guarantees "
    "the map saturates into $[0, 1]$ for any non-negative cost, "
    "with $\\operatorname{sim} = 1$ for an exact match and "
    "$\\operatorname{sim} \\to 0$ for graphs of incompatible size or "
    "label structure. The map partially compensates for graph-size "
    "asymmetry but does not eliminate the bias toward structurally "
    "minimal concepts — a phenomenon exposed empirically by the "
    "over-firing of a compact attractor in the alphabet "
    "(Section 5). The predicted class is the concept with the "
    "maximum of the score function (final formula below), where "
    "$\\Phi(C)$ is the structural complexity of the concept (count "
    "of nodes plus edges) and $\\lambda$ is a small positive "
    "coefficient. This is a Bayesian prior in the spirit of the "
    "minimum-description-length principle: a more complex concept "
    "is treated as a priori more specific, partially counteracting "
    "the small-attractor bias of the raw similarity score. Together "
    "with the predicted class, the classifier returns an explanation "
    "artefact containing four fields: the identifier of the winning "
    "concept, the similarity value, and the two complexities "
    "$\\Phi(C)$ and $\\Phi(H_{\\text{test}})$. These four fields "
    "constitute a complete local explanation of the decision: any "
    "subsequent audit of the prediction reduces to inspecting why "
    "the winning concept ranked above its closest competitor, "
    "without the need for any post-hoc surrogate model.",

    "To make the action of the reduction operator concrete, the "
    "formation of attractor 7_1 (the only attractor of class 7 in "
    "the alphabet) is traced step by step. The initial state "
    "consists of nine handpicked originals of digit 7 from the "
    "MNIST training set after Growing Neural Gas skeletonisation "
    "and Ramer–Douglas–Peucker simplification. Because of "
    "handwriting variation, the example-graphs differ in the "
    "presence of intermediate corner points along the horizontal "
    "stroke, in mild bends of the diagonal stroke, and in "
    "variations of the upper corner angle. The same "
    "graph-edit-distance kernel used at classification time "
    "identifies, in every example, an invariant kernel of three "
    "critical points: a starting endpoint of the horizontal stroke "
    "in the upper-left of the field, an upper corner point in the "
    "upper-right where the horizontal stroke turns into the "
    "diagonal, and a terminal endpoint of the diagonal in the lower "
    "part of the field. These three Point vertices are joined by "
    "two Vector vertices: one for the horizontal segment between "
    "the starting and the upper corner Point, and one for the "
    "diagonal segment between the upper corner and the terminal "
    "Point. All other vertices that occur in only a subset of the "
    "originals — extra intermediate corners on the horizontal "
    "stroke, micro-bends along the diagonal — are removed in the "
    "next step as elements with frequency $f_x < 1$, in agreement "
    "with Definition 1.",

    "For each surviving vertex of the invariant kernel, the "
    "reduction operator records the interval of admissible values "
    "of every coordinate-feature across the absorbed originals. "
    "The intervals reflect the expected topology of the digit: the "
    "starting Point localises in the upper-left, the upper corner "
    "Point in the upper-right, and the terminal Point in the lower "
    "half with relatively wide horizontal latitude. The Vector "
    "nodes inherit analogous intervals: the horizontal segment is "
    "stably positioned in the upper band with a small positional "
    "spread, while the diagonal segment crosses the field from the "
    "upper-right region into the lower band. The width of the "
    "resulting interval directly drives the diagnostic weight: "
    "coordinates whose values repeat stably across originals carry "
    "larger weights at classification time. After a few iterations "
    "the structure stabilises into a linear bipartite chain "
    "alternating Point and Vector vertices: starting Point — "
    "horizontal Vector — upper corner Point — diagonal Vector — "
    "terminal Point. Subsequent iterations widen the intervals but "
    "introduce no new vertices — the signature of having reached "
    "the attractor. The resulting compact attractor 7_1 has 5 "
    "Point + Vector vertices and complexity "
    "$\\Phi(C) = 5 + 4 = 9$, making it one of the smallest "
    "nontrivial attractors in the alphabet. The compact structure "
    "encodes the topological invariant of digit 7, but the same "
    "compactness is the source of the over-firing pattern reported "
    "in Section 5 — a small, broadly-segmented attractor wins "
    "many ambiguous matches against larger concepts.",
]

SECTION_5_RESULTS: list[str] = [
    "The experiment was conducted on a complete-contour subset of "
    "MNIST. Original images of size $28 \\times 28$ pixels were "
    "upscaled to $100 \\times 100$ by Lanczos resampling so that "
    "the skeletal representation has sufficient resolution for "
    "endpoint and junction detection. From the original "
    "ten-thousand-image test split, 8 707 "
    "images were retained by the contour-completeness filter "
    "(structure = complete) of the dataset manifest; per-class "
    "admissible counts are reported in Table 3 (column Support). "
    "Images with broken or fragmented contours were deliberately "
    "excluded from the scope of the present study, since their "
    "recognition requires an additional mechanism of associative "
    "completion of a different mathematical nature, as already stated "
    "in Section 3 (Aim). The training set was constructed from 76 "
    "handpicked originals distributed across 13 concepts, each "
    "original expanded by parametric augmentation (random rotation in "
    "$[-10°, +10°]$ and shift in $[-10\\%, +10\\%]$ of the canvas) "
    "with a per-concept multiplier between five and ten (full "
    "per-concept counts in Table 2), producing 729 augmented "
    "instances and 805 training instances in total. No test images "
    "were used during concept formation.",

    "The classification parameters were committed to the experiment "
    "configuration: skeletonisation threshold 110, simplification "
    "$\\varepsilon = 4.55$; the 14-dimensional feature vector listed "
    "in Table 1; graph-edit-distance comparator with iterative "
    "upper-bound refinement, time budget 15 s per concept comparison; "
    "cost ladder NO_COST / MINOR / GENERAL / SEVERE / NO_MATCH / "
    "IMPOSSIBLE = $0 / 0.65 / 0.75 / 1.0 / 1.5 / 10$; diagnostic "
    "weighting with stabilisation parameter $\\varepsilon = 1.0$; "
    "small positive log-prior coefficient $\\lambda$ on "
    "log-complexity. The full pipeline was executed "
    "end-to-end in batched mode on a multi-instance Nuclio deployment "
    "(8 classification consumers, 2 skeletonisation consumers, 2 "
    "contour-analysis consumers) with shared Kafka producers and "
    "per-image graph caching (concept graphs loaded once at function "
    "init and reused across messages). The campaign produced 8 685 "
    "successfully classified images and 22 dead-letter-queue records "
    "(≈ 0.25 %) from images on which the skeletonisation stage failed "
    "to produce a connected graph at the chosen threshold. Failed "
    "images were excluded from the metric computation.",

    "The trained alphabet contains 13 concept-attractors covering the "
    "ten digit classes; classes 1, 2 and 4 each have two attractors "
    "capturing distinct stylistic variants, and the remaining seven "
    "classes have one attractor each. Concept sizes (the count of "
    "preserved structural primitives) range from three nodes for the "
    "simplest variant of digit 1 to fifteen nodes for digit 8 — the "
    "latter being the only digit in the alphabet with a closed-loop "
    "topology of double articulation, which is reflected in the "
    "highest preserved primitive count. The compact attractor 7_1 "
    "(5 nodes, complexity $\\Phi(C) = 9$), one of the smallest "
    "nontrivial attractors, is structurally a linear chain of two "
    "segments meeting at a single corner. The "
    "largest, 8_1 (15 nodes, complexity $\\approx 29$), encodes the "
    "double-loop "
    "topology of digit 8. The size disparity is intrinsic to the "
    "digit shapes; it is not a tuning artefact and forms the "
    "structural background for the over-firing pattern below. Per-"
    "concept origin counts, augmented-variant counts, and training "
    "totals are reported in Table 2.",

    "Of the 8 707 images submitted to the pipeline, 8 685 produced a "
    "valid skeletal graph and entered the metric computation; the "
    "remaining 22 images (≈ 0.25 %) failed to produce a connected "
    "graph at the binarisation stage and are excluded from the "
    "per-class metric averages without affecting the headline "
    "accuracy ceiling significantly. Accuracy on the valid set is "
    "85.80 %, weighted precision 89.31 %, recall 85.80 %, F1-score "
    "86.66 %. The 3.51-percentage-point gap between weighted "
    "precision and recall is informative: it indicates an uneven "
    "coverage of individual classes — primarily class 2, with recall "
    "60.0 %, and class 8, with recall 74.7 %; both classes are "
    "characterised by high precision and low recall, which is the "
    "typical signature of an under-covering attractor alphabet. "
    "Per-class precision, recall, F1-score and support are reported "
    "in Table 3.",

    "The highest F1-scores belong to classes 0, 9 and 1 — the digits "
    "with the most stable skeletal topology in handwritten form. "
    "Moderate F1-scores are observed for classes 3, 4, 5, 6, and 8. "
    "Two classes are clearly off-trend and define the residual error "
    "budget of the alphabet: class 2 with F1 71.1 % (driven by recall "
    "60.0 % at high precision) and class 7 with F1 78.8 % (driven by "
    "precision 66.2 % at very high recall). The class-7 over-firing "
    "complement of the class-2 recall deficit is not a coincidence — "
    "it has a single shared structural cause that is unpacked below.",

    "Two confusion patterns dominate the residual errors and together "
    "account for the bulk of the 14.20 % class-error budget. The full "
    "confusion matrix is shown in Figure 4; Table 4 lists the ten "
    "largest confusion pairs ranked by absolute count. The dominant "
    "pattern — confusion 2 → 7 (252 cases, 66.0 % of class-2 errors) "
    "and the secondary patterns 3 → 7, 4 → 7 and 1 → 7 — share a "
    "single structural cause. The compact attractor 7_1, "
    "with five Point + Vector vertices and complexity "
    "9, encodes a linear two-segment topology with one corner. This "
    "topology is locally consistent with the open-tail variant of "
    "handwritten digit 2 (a corner in the upper-left, an open-loop "
    "endpoint nearby, and a diagonal stroke to a lower endpoint), "
    "with elongated shapes of digit 3 missing the closing arc, with "
    "strokes of digit 4 meeting at a single junction, and with thin "
    "variants of digit 1 with a sloped headstroke. None of these "
    "classes has a competing attractor in the alphabet that prefers "
    "a corner in the upper-left zone with a tighter coordinate "
    "interval, so the comparator selects 7_1 as the highest-similarity "
    "match for these images. The size-driven coverage advantage of "
    "small attractors is the direct empirical consequence of the "
    "structure-versus-parameter decomposition of Section 4.1.8: when "
    "only the structural skeleton is matched and the parametric "
    "coverage is wide, a small, broadly-segmented attractor wins many "
    "ambiguous matches against larger concepts.",

    "The second pattern — under-coverage of class 2 — is the dual "
    "face of the same problem from the class-2 side. The two "
    "attractors 2_1 and 2_2 cover the closed-loop variant and the "
    "wide-base variant of digit 2 respectively, but the open-tail "
    "stylistic variant — common in left-handed and rapid handwriting "
    "— falls outside the convex hull of either attractor's intervals "
    "while remaining inside 7_1's interval envelope. This is "
    "recoverable by extending the alphabet with a third stylistic "
    "attractor 2_3 (Section 6 fix (i); Section 7 future work item "
    "(i)). The class-8 not-classified rate (127 of 580 class-8 "
    "images, ≈ 21.9 % of class-8 support and 86.4 % of class-8 "
    "errors per Table 4) is a separate phenomenon: 8_1 has the "
    "highest concept size of the alphabet and demands a substantial "
    "structural match before scoring is possible. When the "
    "binarisation threshold breaks the closed loops of digit 8 the "
    "resulting graph either fails the connectivity check at the "
    "skeletonisation stage (and is recorded in the dead-letter "
    "queue, which accounts for only 22 records across the whole "
    "corpus) or passes that stage as a fragmented graph that no "
    "remaining concept can match above the comparator threshold, in "
    "which case the image is rejected before a class label is "
    "emitted. This is a pre-classification failure mode rather than "
    "a comparator failure, "
    "and it is mitigated either by tightening the threshold for "
    "class-8 candidates (extraction-time fix) or by introducing a "
    "fragment-completion step at the graph level (future-work item "
    "beyond the present scope).",

    "Direct numerical comparison between architectures requires care, "
    "as the principal candidate baselines were evaluated under "
    "conditions different from the present one. Convolutional "
    "networks of the LeNet-5 family (LeCun et al., 1998) and modern "
    "residual variants reach above 99 % accuracy on the standard "
    "MNIST test split, but require thousands of labelled examples "
    "per class, the full backpropagation training cycle, and offer "
    "no built-in explanation — the network's decision rests on "
    "linear combinations of feature maps whose interpretation by a "
    "human is only possible through post-hoc visualisation "
    "surrogates, the fragility of which is documented by Slack et "
    "al. (2020). Support-vector machines with Gaussian kernels and "
    "invariance-aware preprocessing reach about 98.6 % accuracy "
    "on standard MNIST; on raw pixels without invariance "
    "augmentation the result is more modest. Multi-layer perceptrons "
    "with deslanting and affine augmentation are at the 97–98 % "
    "level (LeCun et al., 1998). The Prototypical Networks of Snell "
    "et al. (2017), under the canonical 5-way 5-shot "
    "episodic protocol on Omniglot or miniImageNet, attain "
    "approximately 95–97 % within the protocol-specific benchmark; "
    "this number is not directly commensurable with the present "
    "85.80 % on the open-test MNIST protocol. The team's previous "
    "six-class graph-attractor study (Lapin and Bokhan, 2025) on a "
    "restricted MNIST alphabet (digits 1, 2, 3, 6, 7, 9; 5 467 test "
    "images, 8 attractors, 60-second per-comparison budget, exact "
    "graph-edit distance) attained 82.35 % accuracy. The present "
    "study extends the methodology to the full ten-class alphabet "
    "under contour-completeness filtering, increases the alphabet to "
    "13 attractors, introduces diagnostic feature weighting by "
    "reduced-range width, and switches to an iterative upper-bound "
    "graph-edit distance with progressive refinement under a "
    "substantially smaller time budget — the combination of which "
    "yields the 85.80 % accuracy reported here.",

    "The proposed architecture is therefore not in competition with "
    "deep convolutional networks for absolute accuracy on the "
    "standard MNIST benchmark. Its niche is the joint satisfaction "
    "of three properties identified as separately solved but not "
    "jointly solved in Section 2: training without backpropagation, "
    "operation under a small number of examples per class, and local "
    "explainability of each decision at the level of the model "
    "itself. The 85.80 % result, achieved with thirteen "
    "concept-attractors trained from a total of 76 handpicked "
    "originals (between three and nine per concept), demonstrates "
    "that this triple is achievable in practice on a non-trivial "
    "recognition task — which is the empirical confirmation of "
    "Tasks (4) and (5) of Section 3 and the closure of the gap "
    "stated in Section 2.",

    "Visual support is given by Figures 1–4. Figure 1 shows the "
    "full pipeline for a single image — raw raster, binary mask, "
    "skeleton after the algorithmic medial-line approximation, "
    "simplified graph, and the selected concept-attractor. Figure 2 "
    "shows the graph representation of a typical handwritten digit 7 "
    "with critical-point annotations. Figure 3 shows the resulting "
    "attractor 7_1 after reduction with the admissible coordinate "
    "intervals overlaid. Figure 4 is the confusion matrix; the "
    "visual prominence of column 7 corresponds quantitatively to "
    "the over-firing of attractor 7_1 documented in Table 4.",
]

SECTION_6_DISCUSSION: list[str] = [
    "The present work has a conceptual character and calls for further "
    "research. The discussion below addresses six points that arose in "
    "the course of the theoretical exposition, followed by an "
    "experimental subsection on the failure modes observed in "
    "Section 5 and on the application areas in which the proposed "
    "framework is expected to be of practical interest.",

    "First, exogenous primitive detectors. Although the work is "
    "concerned with self-organising systems, the primitive detectors "
    "are given exogenously rather than learned. This is a modelling "
    "restriction; in the brain, formation of the relevant sensory "
    "areas is genetically programmed rather than learned. "
    "Nevertheless, the question of the necessary and sufficient set "
    "of primitives for forming all possible attractors is open. In "
    "the experimental part the primitive vocabulary was deliberately "
    "minimised, which introduced additional approximation noise "
    "during contour skeletonisation.",

    "Second, exogenous coordinates and scales. Coordinate systems "
    "and measurement scales are likewise given exogenously. "
    "Endogenous scales and coordinates are likely formed in the "
    "brain on the basis of both genetics and experience; a full "
    "treatment lies beyond the present scope. In the experiment the "
    "spatial coordinate frame is segmented exogenously.",

    "Third, anchor selection. A central problem of the theory is the "
    "search for the critical (anchor) structural points underlying "
    "the attractor. The theory assumes that these points are "
    "determined by frequency relative to the hypergraph "
    "representation; finding them efficiently among many candidates "
    "is itself a non-trivial matching problem and is reserved for "
    "future work. A related issue is that, while the parameters of "
    "each structural element form a stratification of its parameter "
    "space and define hyper-vertices over the base graph, the "
    "formation of hyper-edges across vertices is a deeper agreement "
    "problem that constitutes a second level of attractor dynamics — "
    "relevant to the global glueing of the attractor and again "
    "outside the present scope.",

    "Fourth, attention as a heuristic. A formal theory of the "
    "attention operator is essential, as it is the principal "
    "mechanism for circumventing the NP-hardness of global "
    "hypergraph matching. The present work uses only a heuristic "
    "anchor-based attention.",

    "Fifth, endogenous ontology and scaling. A strength of the "
    "approach is the natural formation of an endogenous ontology — "
    "the system's internal model of the external world. This "
    "ontology is formed both by neuron maps of individual classes "
    "and by their hierarchy (Parzhin et al., 2020). The scalability "
    "problem is solved automatically: neuron-detectors are trained "
    "independently and their hierarchy generates a hierarchy of "
    "concepts, which has neurobiological support (Quiroga et al., "
    "2005).",

    "Sixth, dendritic-computation hypothesis. The key idea is that "
    "the dendritic tree of a neuron is the principal 'computational' "
    "system that builds the structural attractor; the neuron's "
    "response is its aggregate characteristic. This is consistent "
    "with neurobiological evidence that individual dendritic "
    "branches act as independent computational units and that neuron "
    "firing is determined by the activity of a limited subset of "
    "synapses (Häusser, 2001; Branco and Häusser, 2010; Magee, "
    "2000).",

    "From the experimental side, three failure modes deserve "
    "discussion. First, recall on class 2 is 60.0 %, indicating "
    "under-coverage by concepts 2_1 and 2_2: the stylistic "
    "variability of handwritten 2 (closed-loop versus open-tail "
    "forms) is not captured by two attractors and would require a "
    "third stylistic attractor. This is consistent with the "
    "Section 4.1 statement that intra-class variation should be "
    "expressed by additional subclass attractors when separability "
    "holds. Second, precision on class 7 is 66.2 %, reflecting "
    "over-firing of the compact attractor 7_1 (5 nodes, "
    "complexity 9), one of the smallest nontrivial attractors in "
    "the trained alphabet. The size-driven "
    "coverage advantage of small attractors is a direct consequence "
    "of the structure–parameter decomposition: when only the "
    "structural skeleton is matched and parametric coverage is "
    "wide, a small, broadly-segmented attractor wins many ambiguous "
    "matches. Third, the not-classified rate on class 8 is "
    "non-trivial because attractor 8_1 has the highest complexity "
    "(15 nodes) of the alphabet, demanding a substantial structural "
    "match before scoring is possible. These three patterns confirm "
    "that the error structure under attractor-based classification "
    "is interpretable per concept and per feature range, satisfying "
    "the explanation desideratum stated in Section 1.",

    "Areas of application. The framework's traceability — every "
    "classification decision points to a named concept-attractor "
    "and to specific anchor-feature ranges — makes it a candidate "
    "for high-assurance optical character recognition (medical "
    "forms, legal documents), for industrial defectoscopy of "
    "contour structures (welds, stamped parts, printed circuit "
    "boards), where the number of flaw classes is small and "
    "labelled examples are scarce, and for educational analytics, "
    "where pedagogical explanations are required. Because training "
    "requires only a handful of positive examples per class, the "
    "approach is also relevant to rapid retargeting in engineering "
    "applications — adapting an existing alphabet to a new font, a "
    "new sensor configuration, or a new manufacturing operation — "
    "without retraining a large optimisation-based model. In "
    "regulated industries covered by the EU AI Act (European Parliament and "
    "Council of the European Union, 2024) and the General Data Protection Regulation "
    "(European Parliament and Council of the European Union, 2016) regarding the transparency "
    "of automated decisions, the ability to generate an interpretable "
    "decision protocol automatically is a decisive advantage for "
    "audit, which corresponds to the journal's priority on the "
    "industrial applicability of the results.",
]

SECTION_7_CONCLUSIONS: list[str] = [
    "The present work proposes a formal model of learning based on "
    "the structural reduction of hypergraphs and on the extraction of "
    "invariants in the course of aligning a set of observations. In "
    "contrast to traditional statistical approaches, where learning "
    "is formulated as the minimisation of an error functional, the "
    "proposed model treats learning as convergence to a structural "
    "attractor.",

    "The principal result is the introduction and formalisation of "
    "the notion of a structural attractor as the fixed point of the "
    "reduction operator acting on the space of consistent "
    "hypergraphs. The attractor was shown to possess the following "
    "properties: (i) it is the result of a finite reduction process; "
    "(ii) it is unique for a given class of objects; (iii) it admits "
    "an equivalent characterisation as the intersection of "
    "structural invariants and as the set of elements of frequency "
    "one in the cumulative carrier; (iv) it is invariant under the "
    "order of data presentation. Furthermore, the attractor "
    "decomposes naturally into two levels: a structural level "
    "(topology of relations) and a parametric level (segments and "
    "metric), separating the tasks of extracting structural "
    "invariants and parametrising them.",

    "The principal distinction from classical machine-learning "
    "models can be expressed as an opposition of operators: where "
    "statistical neural-network models employ a minimisation "
    "operator over an error / discrepancy functional, the proposed "
    "approach employs an algebra of structural invariants — "
    "specifically, the fixed-point equation R(C) = C on a poset of "
    "hypergraphs. Learning is interpreted not as the search for the "
    "minimum of a functional but as the computation of the fixed "
    "point of an operator on a space of structures. This change of "
    "formalism has several consequences. First, the necessity of "
    "specifying an error functional and an external optimality "
    "criterion is removed. Second, learning becomes endogenous: it "
    "is determined by the structure of the data. Third, a natural "
    "mechanism of robustness to variations in input representations "
    "emerges from the extraction of invariants. The model opens "
    "prospects for further research, including the analysis of "
    "conditions for the existence and stability of attractors, the "
    "design of efficient hypergraph-matching algorithms, and the "
    "systematic study of learning under a limited number of examples "
    "(few-shot and zero-shot regimes) without statistical "
    "optimisation procedures. In summary, the work establishes the "
    "foundation of an alternative theoretical paradigm of learning, "
    "in which structural invariants, reduction, and attractor "
    "dynamics play the central role.",

    "Empirically, the proposed pipeline achieved 85.80 % accuracy "
    "(89.31 % weighted precision, 85.80 % recall, 86.66 % F1) on "
    "the complete-contour subset of MNIST (8 707 admissible images), "
    "trained on 76 hand-picked originals — between three and nine "
    "per concept — augmented to 805 instances by parametric rotation "
    "(±10°) and shift (±10 %). The learnt alphabet of 13 attractors "
    "had concept node counts in the range 3 to 15. These figures "
    "support the structure–parameter decomposition hypothesis of "
    "Sections 4.1.7–4.1.8: a structural skeleton extracted from a "
    "small set is sufficient to cover the class, while the metric is "
    "induced endogenously through augmentation-driven segmentation "
    "rather than learned through statistical regularisation.",

    "Three directions of future work emerge from the experimental "
    "analysis. (i) Recover the missing recall mode of class 2 by "
    "introducing a third stylistic attractor 2_3, making the "
    "open-tail and closed-loop forms two distinct subclass "
    "detectors instead of forcing them to share a single attractor. "
    "(ii) Replace the heuristic anchor-based attention with an "
    "endogenous attention operator that searches anchors "
    "dynamically rather than pre-computing them as a deterministic "
    "post-hoc preprocessing step; this addresses Section 6 point "
    "four directly and operationalises Definition 6 / Axiom 4 "
    "inside the runtime path. (iii) Extend the framework to EMNIST "
    "and Omniglot to test whether the trained concept-attractors "
    "transfer across alphabets — a probe of the claim, made in "
    "Section 6, that the framework forms a hierarchy of endogenous "
    "concepts.",
]


# ---------- Обов'язкові декларації ITSSI (EN body, UA mirror unused — body is EN) ----------

DECLARATION_COI = (
    "The authors declare that they have no conflicts of interest, including "
    "financial, personal, copyright, or any other conflicts that could "
    "influence the research or the results published in this article."
)

DECLARATION_FUNDING = "The study was conducted without financial support."

DECLARATION_DATA = (
    "Data will be provided upon reasonable request. "
    "The source code of the model, the experiment configuration, the "
    "manifest of admissible images, the per-class metrics, the per-image "
    "error log, and the confusion matrix are available upon reasonable "
    "request to the corresponding author (Y. Parzhyn, e-mail: "
    "yparzhyn@augusta.edu); the request must specify the intended "
    "scientific purpose."
)

DECLARATION_AI = (
    "The authors used AI tools (Anthropic Claude Opus 4.7, model ID "
    "\"claude-opus-4-7\", accessed via the Anthropic API) at four "
    "stages of preparing this manuscript. "
    "(1) Preliminary domain analysis — querying for context on adjacent "
    "areas (graph edit distance, structural pattern recognition, few-shot "
    "learning, post-hoc explainability) to scope the related-work coverage. "
    "Each AI-suggested claim was independently verified against primary "
    "sources before inclusion. "
    "(2) Literature search — generating candidate reference lists, which "
    "were then validated by the authors against Crossref / OpenAlex / "
    "Scopus to confirm DOIs, author identity, and publication metadata "
    "before any citation was included. "
    "(3) Cross-checking results for contradictions — systematic comparison "
    "of the experimental findings (85.80 % accuracy on the complete-contour "
    "subset of MNIST, per-class F1 patterns, top-10 confusion pairs) "
    "against the published literature on MNIST baselines (CNN ~ 99 %, SVM "
    "~ 98 %, MLP ~ 97–98 %) and few-shot learning (Prototypical Networks "
    "~ 95–97 % on Omniglot/miniImageNet) to ensure that the claims are "
    "properly contextualised and do not contradict known results. "
    "(4) Translation editing — correction of translation errors when "
    "porting Ukrainian and Russian draft material into English; each "
    "AI-suggested phrasing was reviewed by an author before adoption. "
    "All conceptual content (problem formulation, theoretical framework, "
    "experimental design, analysis, and conclusions) was authored by the "
    "human authors. AI tools did not contribute to the formulation of "
    "theorems, proofs, or experimental hypotheses, and did not influence "
    "the scientific conclusions of this work."
)


# ---------- Бібліографія (Harvard BSI, латиниця) ----------
# Квоти: ≥15 джерел, самоцитування ≤30%, іноземні ≥40%, 2022–2026 ≥30%,
# DOI ≥90%, Scopus/WoS ≥60%. Кожен запис — dict для подальших стиль-перевірок.

REFERENCES: list[dict] = [
    # Sorted alphabetically by first-author surname, ties broken by year
    # (Harvard BSI convention). Maintain this order on every edit.

    {
        "authors": "Bajcsy, R., Aloimonos, Y., Tsotsos, J. K.",
        "year": 2018,
        "title": "Revisiting active perception",
        "venue": "Autonomous Robots",
        "volume": "42",
        "issue": "2",
        "pages": "177-196",
        "doi": "https://doi.org/10.1007/s10514-017-9615-3",
        "scopus": True,
    },
    {
        "authors": "Branco, T., Häusser, M.",
        "year": 2010,
        "title": (
            "The single dendritic branch as a fundamental functional unit "
            "in the nervous system"
        ),
        "venue": "Current Opinion in Neurobiology",
        "volume": "20",
        "issue": "4",
        "pages": "494-502",
        "doi": "https://doi.org/10.1016/j.conb.2010.07.009",
        "scopus": True,
    },
    {
        "authors": "Bredon, G. E.",
        "year": 1967,
        "title": "Sheaf Theory",
        "venue": "Springer, New York",
        "doi": "https://doi.org/10.1007/978-1-4612-0647-7",
        "scopus": False,
    },
    {
        "authors": "Buzsáki, G.",
        "year": 2010,
        "title": "Neural syntax: cell assemblies, synapsembles, and readers",
        "venue": "Neuron",
        "volume": "68",
        "issue": "3",
        "pages": "362-385",
        "doi": "https://doi.org/10.1016/j.neuron.2010.09.023",
        "scopus": True,
    },
    {
        "authors": "Conte, D., Foggia, P., Sansone, C., Vento, M.",
        "year": 2004,
        "title": (
            "Thirty years of graph matching in pattern recognition"
        ),
        "venue": (
            "International Journal of Pattern Recognition and Artificial "
            "Intelligence"
        ),
        "volume": "18",
        "issue": "3",
        "pages": "265-298",
        "doi": "https://doi.org/10.1142/S0218001404003228",
        "scopus": True,
    },
    {
        "authors": "Davey, B. A., Priestley, H. A.",
        "year": 2002,
        "title": "Introduction to Lattices and Order",
        "venue": "Cambridge University Press, Cambridge, 2nd ed.",
        "doi": "https://doi.org/10.1017/CBO9780511809088",
        "scopus": False,
    },
    {
        "authors": "Ding, K., Wang, J., Li, J., Shu, K., Liu, C., Liu, H.",
        "year": 2022,
        "title": (
            "Graph prototypical networks for few-shot learning on "
            "attributed networks"
        ),
        "venue": (
            "Proceedings of the 31st ACM International Conference on "
            "Information and Knowledge Management"
        ),
        "pages": "2023-2032",
        "doi": "https://doi.org/10.1145/3511808.3557434",
        "scopus": True,
    },
    {
        "authors": "Douglas, D. H., Peucker, T. K.",
        "year": 1973,
        "title": (
            "Algorithms for the reduction of the number of points required "
            "to represent a digitized line or its caricature"
        ),
        "venue": (
            "Cartographica: The International Journal for Geographic "
            "Information and Geovisualization"
        ),
        "volume": "10",
        "issue": "2",
        "pages": "112-122",
        "doi": "https://doi.org/10.3138/FM57-6770-U75U-7727",
        "scopus": True,
    },
    {
        "authors": "European Parliament, Council of the European Union",
        "year": 2016,
        "title": (
            "Regulation (EU) 2016/679 of the European Parliament and of the "
            "Council of 27 April 2016 on the protection of natural persons "
            "with regard to the processing of personal data and on the free "
            "movement of such data (General Data Protection Regulation)"
        ),
        "venue": (
            "Official Journal of the European Union, L 119, 4 May 2016"
        ),
        "pages": "1-88",
        "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "scopus": False,
    },
    {
        "authors": "European Parliament, Council of the European Union",
        "year": 2024,
        "title": (
            "Regulation (EU) 2024/1689 of the European Parliament and of the "
            "Council of 13 June 2024 laying down harmonised rules on "
            "artificial intelligence (Artificial Intelligence Act)"
        ),
        "venue": (
            "Official Journal of the European Union, L series, 12 July 2024"
        ),
        "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        "scopus": False,
    },
    {
        "authors": "Finn, C., Abbeel, P., Levine, S.",
        "year": 2017,
        "title": (
            "Model-agnostic meta-learning for fast adaptation of deep "
            "networks"
        ),
        "venue": (
            "Proceedings of the 34th International Conference on Machine "
            "Learning (ICML 2017)"
        ),
        "pages": "1126-1135",
        "doi": "https://doi.org/10.48550/arXiv.1703.03400",
        "scopus": True,
    },
    {
        "authors": "Fritzke, B.",
        "year": 1995,
        "title": "A growing neural gas network learns topologies",
        "venue": (
            "Advances in Neural Information Processing Systems 7 "
            "(NeurIPS 1994)"
        ),
        "pages": "625-632",
        "doi": "https://doi.org/10.5555/2998687.2998765",
        "scopus": True,
    },
    {
        "authors": "Ganter, B., Wille, R.",
        "year": 1999,
        "title": "Formal Concept Analysis: Mathematical Foundations",
        "venue": "Springer, Berlin",
        "doi": "https://doi.org/10.1007/978-3-642-59830-2",
        "scopus": False,
    },
    {
        "authors": "Glansdorff, P., Prigogine, I.",
        "year": 1971,
        "title": (
            "Thermodynamic Theory of Structure, Stability and Fluctuations"
        ),
        "venue": "Wiley-Interscience, London",
        "scopus": False,
    },
    {
        "authors": "Hagberg, A. A., Schult, D. A., Swart, P. J.",
        "year": 2008,
        "title": (
            "Exploring network structure, dynamics, and function using "
            "NetworkX"
        ),
        "venue": (
            "Proceedings of the 7th Python in Science Conference (SciPy 2008)"
        ),
        "pages": "11-15",
        "doi": "https://doi.org/10.25080/TCWV9851",
        "scopus": False,
    },
    {
        "authors": "Häusser, M.",
        "year": 2001,
        "title": "Synaptic function: dendritic democracy",
        "venue": "Current Biology",
        "volume": "11",
        "issue": "1",
        "pages": "R10-R12",
        "doi": "https://doi.org/10.1016/S0960-9822(00)00034-8",
        "scopus": True,
    },
    {
        "authors": "Hooshyar, D., Yang, Y.",
        "year": 2024,
        "title": (
            "Problems with SHAP and LIME in interpretable AI for education: "
            "a comparative study of post-hoc explanations and "
            "neural-symbolic rule extraction"
        ),
        "venue": "IEEE Access",
        "volume": "12",
        "pages": "137472-137490",
        "doi": "https://doi.org/10.1109/ACCESS.2024.3463948",
        "scopus": True,
    },
    {
        "authors": "Lapin, M., Bokhan, K.",
        "year": 2025,
        "title": "Few-shot learning of graph neural network models without backpropagation",
        "venue": "Automated Control Systems and Instruments",
        "issue": "187",
        "pages": "103-122",
        "doi": "https://doi.org/10.30837/0135-1710.2025.187.103",
        "scopus": False,
        "self_citation": True,
    },
    {
        "authors": "Larkum, M. E.",
        "year": 2022,
        "title": "Are dendrites conceptually useful?",
        "venue": "Neuroscience",
        "volume": "489",
        "pages": "4-14",
        "doi": "https://doi.org/10.1016/j.neuroscience.2022.03.008",
        "scopus": True,
    },
    {
        "authors": "LeCun, Y., Bottou, L., Bengio, Y., Haffner, P.",
        "year": 1998,
        "title": "Gradient-based learning applied to document recognition",
        "venue": "Proceedings of the IEEE",
        "volume": "86",
        "issue": "11",
        "pages": "2278-2324",
        "doi": "https://doi.org/10.1109/5.726791",
        "scopus": True,
    },
    {
        "authors": "Lundberg, S. M., Lee, S.-I.",
        "year": 2017,
        "title": "A unified approach to interpreting model predictions",
        "venue": (
            "Advances in Neural Information Processing Systems 30 "
            "(NeurIPS 2017)"
        ),
        "pages": "4765-4774",
        "doi": "https://doi.org/10.48550/arXiv.1705.07874",
        "scopus": True,
    },
    {
        "authors": "Magee, J. C.",
        "year": 2000,
        "title": "Dendritic integration of excitatory synaptic input",
        "venue": "Nature Reviews Neuroscience",
        "volume": "1",
        "issue": "3",
        "pages": "181-190",
        "doi": "https://doi.org/10.1038/35044552",
        "scopus": True,
    },
    {
        "authors": "von der Malsburg, C.",
        "year": 1999,
        "title": "The what and why of binding: the modeler's perspective",
        "venue": "Neuron",
        "volume": "24",
        "issue": "1",
        "pages": "95-104",
        "doi": "https://doi.org/10.1016/S0896-6273(00)80825-9",
        "scopus": True,
    },
    {
        "authors": "Minh, D., Wang, H. X., Li, Y. F., Nguyen, T. N.",
        "year": 2022,
        "title": (
            "Explainable artificial intelligence: a comprehensive review"
        ),
        "venue": "Artificial Intelligence Review",
        "volume": "55",
        "issue": "5",
        "pages": "3503-3568",
        "doi": "https://doi.org/10.1007/s10462-021-10088-y",
        "scopus": True,
    },
    {
        "authors": (
            "Moscatelli, A., Piquenot, J., Berar, M., Heroux, P., Adam, S."
        ),
        "year": 2024,
        "title": "Graph node matching for edit distance",
        "venue": "Pattern Recognition Letters",
        "volume": "184",
        "pages": "14-20",
        "doi": "https://doi.org/10.1016/j.patrec.2024.05.020",
        "scopus": True,
    },
    {
        "authors": "Nawaz, U., Anees-ur-Rahaman, M., Saeed, Z.",
        "year": 2025,
        "title": (
            "A review of neuro-symbolic AI integrating reasoning and learning "
            "for advanced cognitive systems"
        ),
        "venue": "Intelligent Systems with Applications",
        "volume": "26",
        "pages": "200541",
        "doi": "https://doi.org/10.1016/j.iswa.2025.200541",
        "scopus": True,
    },
    {
        "authors": (
            "Parzhin, Y., Kosenko, V., Podorozhniak, A., Malyeyeva, O., "
            "Timofeyev, V."
        ),
        "year": 2020,
        "title": (
            "Detector neural network vs connectionist artificial neural "
            "networks"
        ),
        "venue": "Neurocomputing",
        "volume": "414",
        "pages": "191-203",
        "doi": "https://doi.org/10.1016/j.neucom.2020.07.025",
        "scopus": True,
        "self_citation": True,
    },
    {
        "authors": "Parzhin, Y., Galkyn, S., Sobol, M.",
        "year": 2022,
        "title": (
            "Method for binary contour images vectorization based on "
            "structural connection tracking"
        ),
        "venue": (
            "2022 IEEE 3rd KhPI Week on Advanced Technology (KhPIWeek)"
        ),
        "pages": "1-6",
        "doi": "https://doi.org/10.1109/KhPIWeek57572.2022.9916331",
        "scopus": True,
        "self_citation": True,
    },
    {
        "authors": "Parzhyn, Y.",
        "year": 2025,
        "title": "Architecture of information",
        "venue": "arXiv preprint arXiv:2503.21794",
        "doi": "https://doi.org/10.48550/arXiv.2503.21794",
        "scopus": False,
        "self_citation": True,
    },
    {
        "authors": (
            "Piao, C., Xu, T., Sun, X., Rong, Y., Zhao, K., Cheng, H."
        ),
        "year": 2023,
        "title": "Computing graph edit distance via neural graph matching",
        "venue": "Proceedings of the VLDB Endowment",
        "volume": "16",
        "issue": "8",
        "pages": "1817-1829",
        "doi": "https://doi.org/10.14778/3594512.3594514",
        "scopus": True,
    },
    {
        "authors": "Quiroga, R. Q., Reddy, L., Kreiman, G., Koch, C., Fried, I.",
        "year": 2005,  # corrected from supervisor's "(2025)" typo per phase1_anchor_map.md §7
        "title": (
            "Invariant visual representation by single neurons in the human "
            "brain"
        ),
        "venue": "Nature",
        "volume": "435",
        "pages": "1102-1107",
        "doi": "https://doi.org/10.1038/nature03687",
        "scopus": True,
    },
    {
        "authors": "Quiroga, R. Q.",
        "year": 2012,
        "title": (
            "Concept cells: the building blocks of declarative memory functions"
        ),
        "venue": "Nature Reviews Neuroscience",
        "volume": "13",
        "issue": "8",
        "pages": "587-597",
        "doi": "https://doi.org/10.1038/nrn3251",
        "scopus": True,
    },
    {
        "authors": "Rajabi, E., Etminani, K.",
        "year": 2024,
        "title": (
            "Knowledge-graph-based explainable AI: a systematic review"
        ),
        "venue": "Journal of Information Science",
        "volume": "50",
        "issue": "4",
        "pages": "1019-1029",
        "doi": "https://doi.org/10.1177/01655515221112844",
        "scopus": True,
    },
    {
        "authors": "Ribeiro, M. T., Singh, S., Guestrin, C.",
        "year": 2016,
        "title": (
            "\"Why should I trust you?\": Explaining the predictions of "
            "any classifier"
        ),
        "venue": (
            "Proceedings of the 22nd ACM SIGKDD International Conference "
            "on Knowledge Discovery and Data Mining (KDD 2016)"
        ),
        "pages": "1135-1144",
        "doi": "https://doi.org/10.1145/2939672.2939778",
        "scopus": True,
    },
    {
        "authors": "Riesen, K., Bunke, H.",
        "year": 2009,
        "title": (
            "Approximate graph edit distance computation by means of bipartite "
            "graph matching"
        ),
        "venue": "Image and Vision Computing",
        "volume": "27",
        "issue": "7",
        "pages": "950-959",
        "doi": "https://doi.org/10.1016/j.imavis.2008.04.004",
        "scopus": True,
    },
    {
        "authors": "Riesen, K.",
        "year": 2015,
        "title": (
            "Structural Pattern Recognition with Graph Edit Distance: "
            "Approximation Algorithms and Applications"
        ),
        "venue": "Springer International Publishing, Cham",
        "doi": "https://doi.org/10.1007/978-3-319-27252-8",
        "scopus": True,
    },
    {
        "authors": "Rucci, M., Victor, J. D.",
        "year": 2015,
        "title": (
            "The unsteady eye: an information-processing stage, not a bug"
        ),
        "venue": "Trends in Neurosciences",
        "volume": "38",
        "issue": "4",
        "pages": "195-206",
        "doi": "https://doi.org/10.1016/j.tins.2015.01.005",
        "scopus": True,
    },
    {
        "authors": "Sanfeliu, A., Fu, K.-S.",
        "year": 1983,
        "title": (
            "A distance measure between attributed relational graphs for "
            "pattern recognition"
        ),
        "venue": "IEEE Transactions on Systems, Man, and Cybernetics",
        "volume": "SMC-13",
        "issue": "3",
        "pages": "353-362",
        "doi": "https://doi.org/10.1109/TSMC.1983.6313167",
        "scopus": True,
    },
    {
        "authors": "Slack, D., Hilgard, S., Jia, E., Singh, S., Lakkaraju, H.",
        "year": 2020,
        "title": (
            "Fooling LIME and SHAP: adversarial attacks on post hoc "
            "explanation methods"
        ),
        "venue": (
            "Proceedings of the AAAI/ACM Conference on AI, Ethics, "
            "and Society (AIES '20)"
        ),
        "pages": "180-186",
        "doi": "https://doi.org/10.1145/3375627.3375830",
        "scopus": True,
    },
    {
        "authors": "Snell, J., Swersky, K., Zemel, R.",
        "year": 2017,
        "title": "Prototypical networks for few-shot learning",
        "venue": (
            "Advances in Neural Information Processing Systems 30 "
            "(NeurIPS 2017)"
        ),
        "pages": "4077-4087",
        "doi": "https://doi.org/10.48550/arXiv.1703.05175",
        "scopus": True,
    },
    {
        "authors": "Strogatz, S. H.",
        "year": 2015,
        "title": (
            "Nonlinear Dynamics and Chaos: With Applications to Physics, "
            "Biology, Chemistry and Engineering"
        ),
        "venue": "Westview Press, Boulder, CO, 2nd ed.",
        "scopus": False,
    },
    {
        "authors": (
            "Vinyals, O., Blundell, C., Lillicrap, T., Kavukcuoglu, K., "
            "Wierstra, D."
        ),
        "year": 2016,
        "title": "Matching networks for one shot learning",
        "venue": (
            "Advances in Neural Information Processing Systems 29 "
            "(NeurIPS 2016)"
        ),
        "pages": "3630-3638",
        "doi": "https://doi.org/10.48550/arXiv.1606.04080",
        "scopus": True,
    },
    {
        "authors": (
            "Xie, Y., Liang, Y., Wen, C., Qin, A. K., Gong, M."
        ),
        "year": 2024,
        "title": (
            "Federated collaborative graph neural networks for few-shot "
            "graph classification"
        ),
        "venue": "Machine Intelligence Research",
        "volume": "21",
        "issue": "6",
        "pages": "1077-1091",
        "doi": "https://doi.org/10.1007/s11633-023-1463-3",
        "scopus": True,
    },
    {
        "authors": "Yarbus, A. L.",
        "year": 1967,
        "title": "Eye Movements and Vision",
        "venue": "Plenum Press, New York",
        "doi": "https://doi.org/10.1007/978-1-4899-5379-7",
        "scopus": False,
    },
]
