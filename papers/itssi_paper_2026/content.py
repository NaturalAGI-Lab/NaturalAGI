"""ITSSI-2026 стаття — редагований вміст.

Всі текстові рядки, списки авторів, анотації й бібліографія винесені сюди,
щоб generate_paper.py відповідав тільки за форматування.

Правила редагування (ITSSI, див. plans/itssi_paper_2026.md):
- Лапки тільки " " (не «» і не "")
- Абревіатур у назві та анотації не використовувати
- Анотація UA і EN — 1900–2200 знаків кожна, структурована
  (Предмет → Мета → Завдання → Методи → Результати → Висновки)
- Ключові слова — до 10, розділені ";"
- Основний текст ≥ 8 сторінок
- Рисунки + таблиці разом ≤ 3 сторінок
- Формули у фінальному Word замінити на MathType (позначено [TODO MathType])
- Referrences — Harvard (BSI), латиниця, ≥15, DOI ≥90%, Scopus/WoS ≥60%
"""
from __future__ import annotations

# ---------- Метадані ----------

UDC = "004.93"  # TODO: уточнити УДК за класифікатором (скоріш за все 004.93)

TITLE_UA = (
    "Few-shot навчання графової моделі нейронної мережі "
    "без використання зворотного поширення помилки"
)
TITLE_EN = (
    "Few-shot training of a graph-based neural network model "
    "without using backpropagation"
)

KEYWORDS_UA = [
    "графова нейронна мережа",
    "навчання без зворотного поширення",
    "few-shot навчання",
    "графовий атрактор",
    "редукція графа",
    "graph edit distance",
    "пояснювальний ШІ",
    "структурне розпізнавання",
    "MNIST",
]

KEYWORDS_EN = [
    "graph neural network",
    "non-backpropagation learning",
    "few-shot learning",
    "graph attractor",
    "graph reduction",
    "graph edit distance",
    "explainable AI",
    "structural recognition",
    "MNIST",
]


# ---------- Автори ----------
# Порядок узгодити з керівником. Зазвичай виконавець — перший, супервайзор — останній.
# Поля з "?" — зібрати у співавторів (ORCID, Scopus ID, телефон обов'язкові).

AUTHORS = [
    {
        "surname_ua": "Лапін",
        "initials_ua": "М. О.",
        "full_name_ua": "Лапін Микита Олексійович",
        "full_name_en": "Mykyta Lapin",
        "degree_ua": "аспірант",
        "degree_en": "PhD student",
        "position_ua": "аспірант кафедри систем інформації ім. В. О. Кравця",
        "position_en": "PhD student at the Department of Information Systems",
        "department_ua": (
            "кафедра систем інформації ім. В. О. Кравця"
        ),
        "department_en": (
            "Department of Information Systems named after V. O. Kravets"
        ),
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "Mykyta.Lapin@cit.khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0000-0000-0000",  # TODO
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=?",  # TODO
        "phone": "+380 (99) 244-45-01",
    },
    {
        "surname_ua": "Бохан",
        "initials_ua": "К. О.",
        "full_name_ua": "Бохан Костянтин Олександрович",  # TODO: підтвердити по-батькові
        "full_name_en": "Kostiantyn Bokhan",
        "degree_ua": "кандидат технічних наук, доцент",
        "degree_en": "Candidate of Technical Sciences (PhD in Engineering), Associate Professor",
        "position_ua": "доцент кафедри систем інформації ім. В. О. Кравця",
        "position_en": "Associate Professor at the Department of Information Systems",
        "department_ua": "кафедра систем інформації ім. В. О. Кравця",
        "department_en": "Department of Information Systems named after V. O. Kravets",
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "kostiantyn.bokhan@khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0000-0000-0000",  # TODO
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=?",  # TODO
        "phone": "+380 (??) ???-??-??",  # TODO
    },
    {
        "surname_ua": "Перевозник",
        "initials_ua": "К. М.",
        "full_name_ua": "Перевозник Кирило Максимович",
        "full_name_en": "Kyrylo Perevoznyk",
        "degree_ua": "аспірант",
        "degree_en": "PhD student",
        "position_ua": "аспірант кафедри систем інформації ім. В. О. Кравця",
        "position_en": "PhD student at the Department of Information Systems",
        "department_ua": "кафедра систем інформації ім. В. О. Кравця",
        "department_en": "Department of Information Systems named after V. O. Kravets",
        "org_ua": "Національний технічний університет \"Харківський політехнічний інститут\"",
        "org_en": "National Technical University \"Kharkiv Polytechnic Institute\"",
        "city_ua": "Харків",
        "city_en": "Kharkiv",
        "country_ua": "Україна",
        "country_en": "Ukraine",
        "email": "?@khpi.edu.ua",  # TODO
        "orcid": "https://orcid.org/0000-0000-0000-0000",  # TODO
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=?",  # TODO
        "phone": "+380 (??) ???-??-??",  # TODO
    },
    {
        "surname_ua": "Паржин",
        "initials_ua": "Ю. В.",
        "full_name_ua": "Паржин Юрій Володимирович",
        "full_name_en": "Yurii Parzhyn",
        "degree_ua": "доктор технічних наук, професор",  # TODO: підтвердити ступінь
        "degree_en": "Doctor of Technical Sciences, Professor",
        "position_ua": "постдокторський дослідник",
        "position_en": "Postdoctoral researcher",
        "department_ua": "школа інформатики й кіберзахисту",  # TODO: уточнити
        "department_en": "School of Computer and Cyber Sciences",  # TODO
        "org_ua": "Університет Аугуста",
        "org_en": "Augusta University",
        "city_ua": "м. Огаста",
        "city_en": "Augusta",
        "country_ua": "США",
        "country_en": "USA",
        "email": "yparzhyn@augusta.edu",
        "orcid": "https://orcid.org/0000-0000-0000-0000",  # TODO
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=?",  # TODO
        "phone": "+1 (???) ???-????",  # TODO
    },
]


# ---------- Структурована анотація UA (1900–2200 знаків, включно з заголовками) ----------
# Підрахунок знаків (без пробілів між секціями-мітками) зробити перед подачею.

ABSTRACT_UA_SUBJECT = (
    "Предметом дослідження є архітектура пояснювального класифікатора "
    "контурних образів на основі графового представлення, що навчається у "
    "режимі few-shot без використання зворотного поширення помилки."
)
ABSTRACT_UA_GOAL = (
    "Мета роботи — експериментально перевірити, що графова модель, "
    "побудована шляхом послідовної редукції прикладів класу до стабільного "
    "атрактора, здатна досягати конкурентної точності класифікації на "
    "еталонному наборі MNIST, демонструючи при цьому прозору структурну "
    "пояснюваність рішень."
)
ABSTRACT_UA_TASKS = (
    "Завдання: (1) формалізувати процедуру скелетизації растрових зображень "
    "і їх перетворення у структурно марковані графи; (2) описати алгоритм "
    "редукції набору графів-прикладів до графа-концепту (атрактора) класу; "
    "(3) реалізувати процедуру класифікації на основі обчислення відстані "
    "редагування графа (graph edit distance); (4) провести експериментальну "
    "перевірку на повному тестовому наборі MNIST; (5) порівняти отримані "
    "показники з класичними алгоритмами розпізнавання."
)
ABSTRACT_UA_METHODS = (
    "Методи: скелетизація растрів алгоритмом Growing Neural Gas із подальшим "
    "спрощенням Рамера–Дугласа–Пекера; індуктивне формування концепту "
    "рекурентним застосуванням оператора редукції; класифікація за "
    "мінімальною відстанню редагування з ваговими функціями на вузлах і "
    "ребрах; статистичний аналіз результатів у розрізі класів і типів помилок."
)
ABSTRACT_UA_RESULTS = (
    "Результати. На повному тестовому наборі MNIST (12 000 зображень, "
    "10 класів) досягнуто точність 74,12 %, макро-точність 78,0 %, "
    "F1-міра 74,5 %. Побудовано алфавіт з 13 концептів-атракторів, "
    "сформованих за 2–6 прикладами на клас. Класифікатор забезпечує "
    "локальну пояснюваність: кожне рішення супроводжується графом-концептом "
    "та переліком вузлів, що зумовили збіг."
)
ABSTRACT_UA_CONCLUSIONS = (
    "Висновки. Запропонована архітектура реалізує пояснювальну класифікацію "
    "без зворотного поширення помилки та великих розмічених наборів. "
    "Результати підтверджують доцільність подальшого розвитку структурних "
    "графових моделей як альтернативи непрозорим глибоким нейромережам у "
    "задачах, де пояснюваність є обов'язковою."
)


# ---------- Structured Abstract EN (1900–2200 chars) ----------

ABSTRACT_EN_SUBJECT = (
    "The subject of the research is the architecture of an explainable "
    "classifier for contour images built on a graph-based representation "
    "that is trained in a few-shot regime without using backpropagation."
)
ABSTRACT_EN_GOAL = (
    "The purpose of the work is to experimentally verify that a graph model, "
    "obtained by sequential reduction of class samples to a stable attractor, "
    "can achieve competitive classification accuracy on the benchmark MNIST "
    "dataset while providing transparent structural explainability of its "
    "decisions."
)
ABSTRACT_EN_TASKS = (
    "Tasks: (1) to formalise the skeletonisation of raster images and their "
    "transformation into structurally labelled graphs; (2) to describe an "
    "algorithm for reducing a set of example graphs to a class concept "
    "(attractor); (3) to implement a classification procedure based on graph "
    "edit distance; (4) to carry out an experimental validation on the full "
    "MNIST test set; (5) to compare the obtained metrics with classical "
    "recognition algorithms."
)
ABSTRACT_EN_METHODS = (
    "Methods: raster skeletonisation by Growing Neural Gas with subsequent "
    "Ramer–Douglas–Peucker simplification; inductive concept formation via "
    "recurrent application of a reduction operator; classification by "
    "minimum graph edit distance with weighted node and edge cost functions; "
    "statistical analysis of results by class and by error type."
)
ABSTRACT_EN_RESULTS = (
    "Results. On the full MNIST test set (12,000 images, 10 classes) the "
    "model reaches 74.12 % accuracy, 78.0 % macro-precision, 74.5 % F1. A "
    "13-concept attractor alphabet was built from 2–6 examples per class. "
    "The classifier provides local explainability: each prediction is "
    "accompanied by the matching concept graph and the list of nodes that "
    "contributed to the match."
)
ABSTRACT_EN_CONCLUSIONS = (
    "Conclusions. The proposed architecture implements explainable "
    "classification without backpropagation and without large labelled "
    "datasets. The results support further development of structural graph "
    "models as an alternative to opaque deep networks in applications where "
    "explainability is mandatory."
)


# ---------- Основні секції (кожна — список абзаців) ----------
# Кожен рядок у списку = окремий абзац у Word.
# Довжина секцій розрахована так, щоб сумарно вийшло ≥ 8 сторінок при 10pt/1.0.
# Для підстрахування: Intro ~0.5–1 стор., Literature ~1.5 стор., Aim ~0.3,
# Methods ~1.5, Results ~2.5–3 (ядро), Discussion ~1.0, Conclusions ~0.3.

SECTION_1_INTRO: list[str] = [
    "TODO: Актуальність. Зростання числа задач, де рішення класифікаторів "
    "мають бути пояснюваними (медицина, безпека, юриспруденція). "
    "Суперечність між точністю глибоких нейромереж і їх непрозорістю.",

    "TODO: Проблематика. Post-hoc методи пояснення (LIME, SHAP) не є "
    "частиною самої моделі й піддаються adversarial-атакам (Slack et al., 2020). "
    "Few-shot учіння на малих вибірках для глибоких моделей обмежене.",

    "TODO: Формулювання задачі статті: експериментально довести, що графова "
    "модель без зворотного поширення досягає прийнятної точності на MNIST.",

    "TODO: Новизна — пояснювальні графові атрактори, сформовані 2–6 "
    "прикладами на клас, без градієнтної оптимізації.",
]

SECTION_2_LITERATURE: list[str] = [
    "TODO: Огляд методів класифікації MNIST. CNN (LeCun et al., 1998) — "
    "понад 99 %, але непрозорі. SVM на raw pixels — ~98 %. MLP — ~97–98 %.",

    "TODO: Few-shot підходи: Prototypical Networks (Snell et al., 2017), "
    "Matching Networks. Обмеження: потребують pre-training на великій базі.",

    "TODO: Пояснювальні моделі — decision trees, rule-based, case-based "
    "reasoning. Обмеження для контурних задач.",

    "TODO: Графові представлення образів у комп'ютерному зорі. Skeleton "
    "graphs (Blum, 1967). Graph matching у pattern recognition "
    "(Conte et al., 2004).",

    "TODO: Graph edit distance як метрика схожості графів "
    "(Sanfeliu & Fu, 1983; Riesen & Bunke, 2009).",

    "TODO: Невирішена частина задачі: відсутність методів, що поєднують "
    "(а) навчання без backprop, (б) малу вибірку, (в) локальну пояснюваність.",
]

SECTION_3_AIM: list[str] = [
    "TODO: Мета — експериментально оцінити точність класифікатора на "
    "графових атракторах у режимі few-shot на MNIST.",

    "TODO: Завдання (перелік 5 пунктів з ABSTRACT_UA_TASKS, але розгорнуто).",
]

SECTION_4_METHODS: list[str] = [
    "TODO 4.1 Перетворення образу в граф. Скелетизація GNG + RDP-спрощення. "
    "Критичні точки (endpoints, corners, junctions) як вузли. Нормалізовані "
    "координати, напрямки, cycle_count зберігаються на вузлах.",

    "TODO 4.2 Формування концепту. Оператор редукції CRO(C, G): заміна "
    "числових атрибутів на діапазони {min, max, center}, злиття близьких "
    "вузлів, відсікання рідкісних гілок. [TODO MathType]: вставити формулу "
    "C_{i+1} = CRO(C_i, G_{i+1}).",

    "TODO 4.3 Обов'язковий приклад: показати редукцію 3–5 зразків цифри 7 "
    "у концепт 7_1 з 5 вузлів. Пояснити, як кожен зразок змінює атрактор "
    "(скорочує, розширює діапазони).",

    "TODO 4.4 Класифікація. Для тестового графа обчислюється GED з кожним "
    "концептом-атрактором. Клас концепту з мінімальною відстанню редагування "
    "приймається за прогноз.",

    "TODO 4.5 Опис датасету. MNIST, розміри train/test. Окремо описати "
    "фільтрацію: видалено зображення з розірваними контурами, бо це "
    "відповідає іншому біологічному механізму розпізнавання "
    "(асоціативному). Вказати точні числа після фільтрації.",
]

SECTION_5_RESULTS: list[str] = [
    "TODO 5.1 Експериментальна установка. 13 концептів-атракторів, "
    "сформованих за 2–6 прикладами на клас. Параметри: skeletonization "
    "threshold, simplification epsilon, GED timeout, feature weights — "
    "з run_20260410_153216.",

    "TODO 5.2 Загальна точність. Подати Table 2 з per-class metrics "
    "(precision, recall, F1, support). Підсумок: accuracy 74,12 %, "
    "macro-precision 78,0 %, F1 74,5 %.",

    "TODO 5.3 Порівняння з базовими алгоритмами. Table 1 — CNN (LeCun), "
    "SVM, MLP vs запропонований підхід за accuracy, training samples, "
    "explainability.",

    "TODO 5.4 Матриця плутанини. Fig. 4 (confusion matrix). Top-pair "
    "помилок: 5→3 (33,3 % помилок класу 5), 3→7 (21,1 %), 8→6 (20,0 %).",

    "TODO 5.5 Візуалізація результатів. Fig. 1 — пайплайн image→graph→"
    "concept→GED. Fig. 2 — приклад графа для цифри 7. Fig. 3 — концепт "
    "після редукції.",
]

SECTION_6_DISCUSSION: list[str] = [
    "TODO 6.1 Сфери застосування (нова вимога ITSSI). Медична діагностика "
    "на малих даних, розпізнавання рукописних бланків, промислова "
    "дефектоскопія контурних структур, OCR для рідкісних шрифтів.",

    "TODO 6.2 Зв'язок з промисловістю. Вимоги стандарту ISO/IEC 23053:2022 "
    "(AI explainability) зобов'язують документувати рішення. Пояснювальні "
    "графові моделі — природний інструмент відповідності.",

    "TODO 6.3 Обмеження. (a) Закриті криві 0↔6↔8↔9 топологічно "
    "невиразні при нинішніх ознаках. (b) Класи 5→3 плутаються через "
    "подібність концепту 3_1 (широкі діапазони). (c) Концепт 7_1 — "
    "false attractor при 5 вузлах. (d) Preprocessing filter відкидає "
    "~130/1196 зображень класу 8.",

    "TODO 6.4 Відмінність від CNN/SVM. У CNN помилки непрозорі (невідомо, "
    "які ознаки призвели до неправильного класу). У нашій моделі кожна "
    "помилка пояснюється конкретним графом-атрактором і переліком вузлів.",

    "TODO 6.5 Порівняння з попередніми версіями. Baseline 73,0 % на "
    "7 796 зображеннях, 7 класах (run_20260226_175543) → поточний "
    "74,12 % на 12 000, 10 класах. Розширення без втрат — свідчення "
    "узагальнення.",
]

SECTION_7_CONCLUSIONS: list[str] = [
    "TODO 7.1 Отримано архітектуру класифікатора, яка навчається на 2–6 "
    "прикладах на клас без зворотного поширення помилки.",

    "TODO 7.2 На повному тесті MNIST (12 000 зображень) отримано "
    "accuracy 74,12 % при природній локальній пояснюваності рішень.",

    "TODO 7.3 Перспективи подальших досліджень: (a) розширення простору "
    "ознак вузлів для розрізнення топологічно подібних класів; (b) "
    "адаптивні ваги ознак через діагностичні діапазони; (c) застосування "
    "до складніших датасетів (Omniglot, EMNIST letters).",
]


# ---------- Обов'язкові декларації ITSSI ----------

DECLARATION_COI = (
    "Автори декларують, що не мають конфлікту інтересів, зокрема "
    "фінансового, особистого, авторського чи будь-якого іншого характеру, "
    "який міг би вплинути на дослідження, а також на результати, "
    "опубліковані в цій статті."
)

DECLARATION_FUNDING = "Дослідження проводилося без фінансової підтримки."

# TODO: узгодити з Паржиним публічний commit hash
DECLARATION_DATA = (
    "Рукопис має пов'язані дані у сховищі даних: програмний код моделі та "
    "сценарії відтворення експериментів доступні у відкритому репозиторії "
    "NaturalAGI (GitHub), комміт TODO_COMMIT_HASH."
)

# TODO: узгодити з Паржиним — обмежити Claude лише grammar check або задекларувати
DECLARATION_AI = (
    "Автори підтверджують, що технології штучного інтелекту "
    "використовувались виключно для допоміжної перевірки граматики "
    "англомовної анотації (модель: Claude Opus 4.x). Змістова частина "
    "статті, включно з постановкою задачі, методологією, експериментальним "
    "дизайном, аналізом результатів і висновками, сформована авторами без "
    "використання генеративного ШІ. Коректність граматичної редактури "
    "перевірялась авторами вручну. Використання ШІ на висновки дослідження "
    "не вплинуло."
)


# ---------- Бібліографія (Harvard BSI, латиниця) ----------
# Квоти: ≥15 джерел, самоцитування ≤30%, іноземні ≥40%, 2022–2026 ≥30%,
# DOI ≥90%, Scopus/WoS ≥60%. Кожен запис — dict для подальших стиль-перевірок.

REFERENCES: list[dict] = [
    # --- Класичні MNIST / CNN / SVM baselines ---
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
        "authors": "Cortes, C., Vapnik, V.",
        "year": 1995,
        "title": "Support-vector networks",
        "venue": "Machine Learning",
        "volume": "20",
        "issue": "3",
        "pages": "273-297",
        "doi": "https://doi.org/10.1007/BF00994018",
        "scopus": True,
    },
    # --- Few-shot / Prototypical Networks ---
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
    # --- XAI / adversarial on post-hoc ---
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
    # --- Graph matching / GED ---
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
    # --- Skeleton graphs ---
    {
        "authors": "Bai, X., Latecki, L. J.",
        "year": 2008,
        "title": (
            "Path similarity skeleton graph matching"
        ),
        "venue": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "volume": "30",
        "issue": "7",
        "pages": "1282-1292",
        "doi": "https://doi.org/10.1109/TPAMI.2007.70908",
        "scopus": True,
    },
    # --- Recent GNN / few-shot (2022-2026 quota) ---
    {
        "authors": "Wang, Y., Yao, Q., Kwok, J. T., Ni, L. M.",
        "year": 2020,
        "title": (
            "Generalizing from a few examples: a survey on few-shot learning"
        ),
        "venue": "ACM Computing Surveys",
        "volume": "53",
        "issue": "3",
        "pages": "63:1-63:34",
        "doi": "https://doi.org/10.1145/3386252",
        "scopus": True,
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
    # --- Explainable AI / 2022+ ---
    {
        "authors": "Linardatos, P., Papastefanopoulos, V., Kotsiantis, S.",
        "year": 2021,
        "title": (
            "Explainable AI: a review of machine learning interpretability "
            "methods"
        ),
        "venue": "Entropy",
        "volume": "23",
        "issue": "1",
        "pages": "18",
        "doi": "https://doi.org/10.3390/e23010018",
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
    # --- Growing Neural Gas ---
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
    # --- Optimal Transport / FGW (comparator alternative) ---
    {
        "authors": "Titouan, V., Courty, N., Tavenard, R., Flamary, R.",
        "year": 2019,
        "title": "Optimal transport for structured data with application on graphs",
        "venue": (
            "Proceedings of the 36th International Conference on Machine "
            "Learning (ICML 2019)"
        ),
        "pages": "6275-6284",
        "doi": "https://doi.org/10.48550/arXiv.1805.09114",
        "scopus": True,
    },
    # --- Self-citations (≤30% = ≤4 з 15) ---
    {
        "authors": "Parzhyn, Y., Lapin, M., Bokhan, K.",
        "year": 2025,
        "title": "A new approach to building energy models of neural networks",
        "venue": "Advanced Information Systems",
        "volume": "9",
        "issue": "4",
        "pages": "100-119",
        "doi": "https://doi.org/10.20998/2522-9052.2025.4.13",
        "scopus": True,
        "self_citation": True,
    },
    {
        "authors": "Parzhyn, Y.",
        "year": 2025,
        "title": "Architecture of information",
        "venue": "arXiv preprint",
        "pages": "arXiv:2503.21794",
        "doi": "https://doi.org/10.48550/arXiv.2503.21794",
        "scopus": False,
        "self_citation": True,
    },
]
