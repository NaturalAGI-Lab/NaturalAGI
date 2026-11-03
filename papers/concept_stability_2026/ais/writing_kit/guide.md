# Як писати статтю AIS

Шаблон: `lapin_ais_2026_template.docx`. Відкрий його в Pages і пиши замість `[text]`, `[текст]` і `[caption]`. Під кожним заголовком червоним курсивом стоїть аутлайн із розділу «Розділи» нижче; видаляй його, коли напишеш абзац. Шаблон збирає `build_template.py` з цього файлу. Розкладку, шрифти, рисунки, таблиці, формули й список джерел зроблено за правилами журналу (`../../journal_rules/AIS_ArticleRequirements_EN.pdf`), їх не чіпай. Посилання на джерело в тексті — номер у квадратних дужках, `[7]`. Здавати треба .docx: «Файл → Експортувати в → Word».

Порядок писання: 2 → 3 → 5 → 4 → 1 → анотації. Методи найпростіші, вступ найважчий.

## Терміни

Терміни в аутлайні — англійською, у тій формі, в якій вони мають стояти в статті. Один термін — одне поняття; не замінюй їх синонімами.

| Term | Що означає |
|---|---|
| concept, subclass | збережений граф одного підкласу цифри (0_1, 4_2 …); 13 concepts на 10 цифр |
| formation, reduction | побудова concept з training graphs; кожен новий граф зводиться до спільної з concept структури |
| envelope | діапазони значень кожної feature кожного node, які зберігає concept |
| training file, cohort | одне навчальне зображення; усі training files одного subclass |
| structural marker *m*<sub>topo</sub>, envelope marker *m*<sub>env</sub> | два маркери збіжності formation |
| binary mask, skeleton, pruning, branch, spur | бінаризоване зображення; скелет завтовшки 1 px; обрізання коротких branches; короткий відросток |
| growing neural gas | метод, що ставить nodes на skeleton |
| point, vector; endpoint E, corner point C, intersection point I | вузли графа й відрізки між ними; типи points |
| start point S | точка, з якої preprocessing починає зіставлення |
| complexity | кількість nodes плюс edges графа |
| complexity pre-filter | відкидає concepts, складніші за зображення |
| preprocessing, rejection message | зведення image graph до структури concept; повідомлення, з яким concept відхилено |
| graph edit distance (GED); deletion, insertion, substitution; label mismatch | відстань між графами та її операції; заміна nodes різних типів |
| out-of-range feature | feature, значення якої поза envelope |
| similarity *s*, adjusted score *ŝ*, complexity prior | формули (1) і (2); доданок λ log<sub>2</sub> *K* |
| census; mechanism: gate, similarity, prior | розподіл усіх wrong-class answers за кроком, що їх вирішив |
| wrong-class answer, confusion pair (2→7) | хибна відповідь; пара «істинний клас → передбачений» |
| complete contours, incomplete contours | зображення з повними й розірваними контурами |
| conditional accuracy, end-to-end accuracy, dead-letter queue (DLQ) | точність серед classified; серед усіх submitted; черга збоїв конвеєра |
| compression | відношення nodes і values у training graphs до збережених у concepts |

## Розділи

Кожен пункт «П» — один абзац: які тези в ньому мають бути. Переказуй своїми словами, порядок тез можна міняти.

### Анотація

Англійська й українська, кожна 1200–1800 знаків із пробілами, без скорочень, зрозумілих лише з тексту. Мітки вже стоять у шаблоні. Твоя анотація від 02.11: vault `raw/analyses/error_anatomy_ais_2026/detector_check/job_diveye_abs/user_abs_raw.txt`.
- Актуальність: graph-based classifiers можна читати й перевіряти; їхня надійність залежить від стабільності formation і від того, чи можна простежити wrong-class answer до кроку.
- Предмет: стабільність concept formation і mechanisms помилок класифікації.
- Мета: визначити, коли concept graphs стабілізуються, і знайти причини помилок на кроках обробки.
- Завдання: три завдання з 1.3 коротко.
- Методи: skeleton graphs, concept formation by reduction, GED з complexity prior.
- Результати: 13 concepts; structural marker — 1–37 training files, envelopes ростуть далі; 91,13 %; у повторному запуску (90,05 %, 8 683 зображення) 820 wrong-class answers = 312 gate + 383 similarity + 125 prior.
- Висновки: структура стабільна за десятки прикладів; кожна помилка прив'язана до кроку, тож видно, що виправляти.

### 1.1 Research Background

- П1. Gradient-trained networks точні, але знання сидять у weights, які не прочитаєш; post hoc explanations лише наближені; для рішень, які треба перевіряти, краща inherently interpretable model [1, 2]. Наша модель: subclass цифри — attributed graph, сформований reduction кількох training graphs, рішення — graph matching [3–5]. Кожен node, edge й envelope можна роздрукувати.
- П2. Читабельність ще не означає довіри, треба виміряти дві властивості. Stability: concept, що міняється з кожним прикладом, не може бути еталоном; теорія стверджує збіжність до attractor за обмежене число кроків [5]. Accountability of errors: кожну wrong-class answer має бути видно до кроку, де вона виникла, а всі помилки мають ділитися на causes, що вказують на конкретні виправлення.
- П3. Що вже зроблено: 91,13 % на MNIST test images with complete contours, 13 concepts [6, 7]; пояснено найчастішу confusion pair 2→7. Чого немає: formation у часі не виміряно, решту помилок не пояснено. Ця стаття закриває обидві прогалини. Кінцеве речення за вимогою журналу: «Therefore, research on … is timely and relevant».

### 1.2 Literature Review and Problem Statement

Журнал вимагає: кожне джерело окремо — що зроблено і чому питання лишилося невирішеним.
- П1. Graph edit distance. GED — стандартна error-tolerant dissimilarity між attributed graphs. [8] survey of GED algorithms → порівнює алгоритми, а не помилки класифікатора. [9] GED як quadratic assignment problem → обчислення відстані, а не рішення на її основі. [10] heuristics, бо exact GED NP-hard → міряє heuristics, помилки класифікатора поза дослідженням. [11] GED, learned by a graph neural network → залежить від gradient training.
- П2. Interpretability. [1] high-stakes decisions потребують inherently interpretable models → не міряє stability класів. [2] ten challenges of interpretable ML → concept formation серед них немає. [12] XAI survey and taxonomy → огляд, моделі не тестує. [13] post hoc explanation of GNNs → пояснює trained model постфактум, а наші класи й так читабельні. [14] prototypical networks for few-shot learning → клас — точка, навчена gradient descent; для concept, сформованого лише reduction, питання convergence відкрите.
- П3. Error analysis. [15] hidden stratification у медичних зображеннях → модель розглянуто ззовні, збій прив'язано до subset of inputs, а не до decision step. [16] shortcut learning → кроки мережі не прочитати, тож групувати помилки за decision step нема як.
- П4. Skeletons. [17] ієрогліфи як skeleton graphs → мета — recognition, а не облік помилок, хоча skeleton успадковує spurs, broken strokes і merged loops. [18] skeleton pruning без spurious branches → вплив pruned branch на клас відкритий. Наш граф будує growing neural gas по skeleton [19], тож ті самі дефекти стосуються і нас.
- П5. Підсумок: graph matching міряє відстань; interpretability ставить вимоги або пояснює trained models; error analysis дивиться ззовні; робота зі skeletons закінчується до рішення. Немає дослідження, яке міряє, коли concept graphs non-gradient structural classifier перестають змінюватися, і яке ділить усі його wrong-class answers на mechanisms за decision steps.

### 1.3 Research Aim and Objectives

- Мета: виміряти stabilization of concept graphs під час formation і віднести кожну wrong-class answer тестового запуску до decision step, що її спричинив.
- Завдання 1: зафіксувати для кожного concept, коли структура й envelopes перестають змінюватися за один formation pass.
- Завдання 2: виміряти залежність структури й envelopes від number of training samples і compression of training graphs.
- Завдання 3: розділити всі wrong-class answers на mechanisms за decision steps і простежити representative cases кожного mechanism від pixels до ranking.

### 2.1 The classifier

Журнал також хоче в розділі 2: гіпотезу, припущення, програмне забезпечення, обґрунтування вибору методів. У тезах їх майже немає, тож додай коротко.
- П1. Pipeline [5, 7]: image 100 × 100 → binarization at threshold 110 → one-pixel skeleton → pruning of branches from an intersection to a free end shorter than max(8 % of skeleton length, 5 px) → growing neural gas places nodes on the skeleton → graph of points and vectors. Points: endpoints E, corner points C, intersection points I; vectors — stroke segments між ними. 13 geometric features у [0, 1] на кожен node. Complexity = nodes + edges.
- П2. Concept: формується з training graphs одного subclass; кожен новий graph проходить reduction до спільної з concept структури; concept зберігає range кожної feature кожного node — це envelope. 13 concepts на 10 цифр; 1, 2, 4, 9 мають по два subclasses, 1_2 і 9_1 не використовуються.
- П3. Classification у чотири кроки: (1) complexity pre-filter відкидає concepts, складніші за image; (2) preprocessing ставить start point S і зводить endpoints, intersections і corners до структури concept, а якщо не вдається — rejection message («concept has endpoints but image does not»), яке описує image graph після preprocessing, а не raw image; (3) GED з фіксованими costs, similarity за формулою (1); (4) ranking за adjusted score, формула (2), λ = 0,10; complexity prior віддає перевагу richer concept, коли два збігаються майже однаково; winner називає клас.

### 2.2 Formation measurements

- П1. Formation відтворено offline на cached training graphs кодом продакшену, без запису в deployed concept store. Concepts of the 91.13 % configuration [7], 869 training files. Cohort 4_1 — 36 files: шість прибрано, бо вони змішували open і closed shapes цифри 4, і formation не могла їх об'єднати.
- П2. Два маркери за один formation pass: structural marker *m*<sub>topo</sub> і envelope marker *m*<sub>env</sub> (визначення в розділі «Формули»). Обмеження: *m*<sub>topo</sub> бачить лише counts, rearrangement без зміни counts не помічає; *m*<sub>env</sub> позначає onset of slow growth, після нього envelopes ще повільно ширшають.

### 2.3 Error analysis

- Чому окремий запуск: census потребує full ranking усіх concepts для кожного image, а запуск 91,13 % його не зберіг, і concepts після нього retrained.
- Що зроблено: concepts retrained на тих самих 869 files із тими самими classification parameters, ranking збережено.
- Результат запуску: 7 819 із 8 683 = 90,05 % (95 % Wilson interval 89,40–90,66 %); 21 pipeline failure; 44 images rejected by all 13 concepts.
- Усі числа 3.3 — з цього запуску; кожен trace перераховано production scoring code, і він збігся зі stored ranking.

### 3.1 Convergence of concept formation (завдання 1)

- П1. Таблиця 1: *m*<sub>topo</sub> від 1 до 37 training files. Concepts з одним open stroke стабілізуються одразу: 1_1 після першого file; 1_3, 4_1, 4_2, 7_1 після другого. З loops чи кількома strokes — десятки files: 8_1 до file 37 із 42, 5_1 до 28, 2_1 до 23. Кожен concept стабілізується задовго до кінця cohort: 2_1, найбільша cohort, на file 23 із 121.
- П2. *m*<sub>env</sub> не йде слідом за *m*<sub>topo</sub>: 8_1 — envelope на file 5, структура до 37; 2_1 — 12 і 23; 5_1 — 11 і 28; 7_1 навпаки — структура на 2, envelope на 15. Отже, flat envelope не означає кінця formation, і stopping rule має перевіряти обидва markers (рис. 1).

### 3.2 Sample count and compression (завдання 2)

- 3.2.1. Три різні concepts: 2_2 (loop і intersection), 7_1 (один open stroke), 4_1 (closed four); по три random subsets на 2, 5, 10, 20 files (рис. 2). Більше files рухає структуру й envelope у протилежні боки: nodes 2_2 16 → 12,7 → 12 → 12, бо ранні concepts мають nodes, яких наступні samples не мають; mean envelope width 7_1 0,33 / 0,48 / 0,68 / 0,80, бо кожен sample додає свою variation; nodes 4_1 9,3 → 8. Висновок: smaller graph і looser bands. Ці probe concepts не deployed, тож невідомо, що з двох ефектів більше допомагає recognition; наступний крок — classification run на кожну умову.
- 3.2.2. Таблиця 2: 869 training graphs — 9 738 nodes, 9 242 edges, 336 637 stored values → 106 nodes, 100 edges, 6 647 values, з них 3 053 ranges. Counting rule (розділ «Формули»). Node compression 91,9×, для 2_1 176,7×; value compression 50,6×. Це відношення consumed до kept, а не parameter count, і з розміром neural network його не порівнюють. Image node має ~60 properties, formation відкидає лише source file path; concepts набувають aggregate properties, яких немає в жодному image node, наприклад expected degree of the start point.
- 3.2.3. Generalization to other MNIST splits, для довідки: не окреме завдання, бо мета статті — complete contours; коротко. Система читає contours, тож цифра з broken stroke дає skeleton, який не покриє жоден concept із closed contours. Тому concepts без retraining запущено на всьому test set і на training split 60 000 (таблиця 3). Пояснити: classified / DLQ (pipeline failure) / no result; conditional accuracy ділить на classified, end-to-end accuracy — на всі submitted. Test: complete 7 911 із 8 704 (90,89 %), incomplete 310 із 1 295 (23,94 %), разом 82,21 %. Training split: completeness labels з heuristic, а не manual review; перший run лишив 8 662 без result; rerun на 45 501 complete — classified 98,49 %, conditional accuracy 85,85 %; gap до test схожий на label noise heuristic, але його не isolated. Усі 70 000 — 73,42 % end-to-end без per-split tuning.

### 3.3 Mechanisms of misclassification (завдання 3)

- 3.3.1, П1. Кожна з 820 wrong-class answers потрапляє рівно в один mechanism за decision step, що її вирішив. Gate 312 (38,0 %): жоден true-class concept не дійшов до comparison (277 — rejected by preprocessing, 31 — complexity pre-filter, 4 — обидва). Similarity 383 (46,7 %): true-class concept compared, але його raw similarity нижча, ніж у winner. Prior 125 (15,2 %): raw similarity не нижча, програш лише через prior term у (2); без prior 113 були б correct, в інших 12 веде third concept. Ties немає, sort order нічого не вирішує.
- 3.3.1, П2. Confusion pairs (рис. 3): ten most frequent pairs — 542 answers (66,1 %). Similarity: 2→7 90 із 93, 0→6 46 із 52, 9→4 27 із 27. Gate: 2→6 56 із 65, 4→1 40 із 41. Prior: 5→3 55 із 56, 7→2 21 із 26. Змішані: 4→7 36 gate + 44 similarity; 4→5 26 + 45; 2→3 21 similarity + 10 prior.
- 3.3.1, П3. Rejection messages (рис. 4). Per rejected true-class concept: no endpoints 141, no corner points 115, no intersection points 111. Per image: «no corner points + no intersection points» 100, усі class 4; «no endpoints» 82, з них 56 class 2; iteration limit (critical-point graphs не isomorphic після п'яти reduction iterations) 37, з них 15 class 8 і 10 class 0; pre-filter 31. Пояснити legend рис. 4: «too few» — concept має більше points цього типу, ніж image.
- 3.3.2 Gate, mnist_test_2_00144 (рис. 5). Двійка classified as 6_1, обидва class-2 concepts rejected до comparison. Skeleton 168 px; pruning прибрав branch 12,5 px від intersection (57, 69) до end (67, 75), бо threshold 15,7 px = 8 % від 196,6 px skeleton length. Це був tail основи двійки, без нього низ — closed loop: одна free end, одна intersection of degree 3, шість corners, один cycle. Обидва class-2 concepts чекають start point S of degree 1 і ще один endpoint; preprocessing робить S з єдиного free end, endpoints не лишається → «concept has endpoints but image does not». Pass 6_1, 9_2, 4_1 (loop, intersection, без endpoints крім S); 6_1 wins 0,6892 проти 0,6742 і 0,6441, prior порядок не міняє. Помилка починається з pruning.
- 3.3.3 Similarity, mnist_test_0_00701 (рис. 6). Нуль → 6_1. Spur 15,4 px угорі loop, pruning threshold 13,1 px, тож spur лишився. Graph: один endpoint, intersection of degree 3, п'ять corners, cycle — topology шістки. Pass preprocessing: 6_1, 9_2, 4_1, 0_1. Під 0_1 spur deleted, S стає на former intersection, де в 0_1 start point немає: 4 із 12 out-of-range features на цьому node, лише його substitution коштує 4,1419. 0_1 — 0,5868, fourth; 6_1 — п'ять out-of-range features, 0,7120. Обидва мають complexity 20, prior term однаковий. Помилку вирішує similarity на graph, topology якого справді від іншого класу.
- 3.3.4 Prior, mnist_test_5_00606 (рис. 7). П'ятірка → 3_1. Graph: один open stroke, два endpoints, п'ять corners, complexity 25. 5_1: GED 6,7259, одна out-of-range feature, *s* = 0,7880. 3_1: GED 7,8362, дві out-of-range features, *s* = 0,7614. Prior +0,3700 для 5_1 (complexity 13) і +0,4087 для 3_1 (17). 5_1 веде на 0,0266, prior дає 3_1 на 0,0387 більше, 3_1 wins на 0,0121. Решта вісім concepts до comparison не дійшли: 2_2, 4_1, 6_1, 9_2 — no intersection; 0_1, 8_1 — no corner; 1_1, 4_2 — more endpoints than the image. Зворотний бік: mnist_test_2_00030 — 7_1 веде 0,7679 проти 0,7591 у 2_1, prior +0,3700 для 2_1 і +0,3170 для 7_1, 2_1 wins на 0,0442. В обох випадках raw gap менший за різницю prior terms; prior вирішує, коли similarity не розрізняє, а правильно чи ні — залежить від того, хто richer.
- 3.3.5 Class 4, П1 (рис. 8). Class 4 — 209 wrong-class answers, другий після class 2 (216), і через gate, і через similarity. mnist_test_4_00755: open 4 → 1_1. Нічого не pruned. У skeleton два junctions за ~24 px, а graph має одну intersection of degree 4, чотири endpoints, жодного corner. 4_2 потребує corner → «concept has corner points but image does not». 4_1 має intersection, два corners і жодного endpoint, крім S; endpoint reduction знімає branches разом з intersection → «concept has intersection points but image does not». Compared лише 1_1, 7_1, 1_3; 1_3 веде на raw similarity (0,6489 проти 0,5973 і 0,5815), prior піднімає 1_1 до adjusted score 0,9515.
- 3.3.5, П2. Типовість: усі 40 gate errors 4→1 мають ті самі два rejection messages; 39 graphs без corner; 28 мають чотири endpoints і одну intersection, 11 — п'ять endpoints і одну intersection; 1_1 wins 37, 1_3 — 3. Та сама пара messages rejects class 4 у 35 із 36 gate errors 4→7. Тут клас втрачено до scoring, prior лише вибирає серед wrong concepts.
- 3.3.5, П3 (рис. 9). Протилежний випадок, similarity 4→7: mnist_test_4_00487 має три endpoints, один corner, одну intersection — point composition of concept 4_2 (так само 21 із 44 similarity errors 4→7). Під 4_2 preprocessing лише робить S з одного endpoint; GED substitutes усі дев'ять nodes без deletion і без label mismatch, але вісім out-of-range features на чотирьох nodes, ці substitutions коштують від 1,4948 до 3,0611 кожна; GED 10,6695, *s* = 0,6144. Під 7_1 preprocessing прибирає branch над intersection, intersection стає corner, GED deletes ще два nodes і три edges по 0,25; GED 4,4255, дві out-of-range features, *s* = 0,7460. Prior дає 4_2 на 0,0917 більше — менше за raw gap 0,1316; 7_1 wins 1,0630 проти 1,0231.
- 3.3.5, П4. У всіх 44 similarity errors 4→7 winner 7_1, best class-4 concept — 4_2, median similarities 0,7428 і 0,6025. Під 7_1 жодна не платить за label mismatch; усі 21 images з composition 4_2 matched п'ятьма substitutions і двома deletions. Mechanism: preprocessing для smaller concept обрізає image до нього, а deletion дешевша за node з out-of-range features, тож smaller concept, що discards зайве, перемагає correct concept, який мусить match кожен node.
- 3.3.6 Dominant pair 2→7 [7]. У 91.13 % configuration — 111 errors; у 110 lower loop двійки без hole вже в binary mask (loop drawn open або interior filled товстим stroke), в одному випадку hole втрачено при vectorization. Двійка отримує open-stroke topology, як 7_1, і програє на similarity — це збігається з 90 similarity cases із 93 у повторному запуску.

### 4. Discussion

Журнал хоче: тлумачення; порівняння з іншими дослідженнями; практичне значення (де, за яких умов, який ефект); як результат закриває проблему з 1.2; наприкінці обмеження, недоліки й розвиток.
- П1. Where corrections belong. Gate (38,0 %) вирішується до будь-якого cost: pruning зрізає end двійки, graph construction зливає два junctions четвірки; зміна cost weights тут не допоможе, бо true concept cost не отримує. Similarity (46,7 %): частина cases має справді іншу topology (zero with a spur) → виправляти graph construction, а не scoring. 4→7: topology правильна, програш через preprocessing для smaller concept і дешеві deletions → це scoring question. Prior (15,2 %): єдина група, яку може прямо змінити ranking rule, але воно ж rescues інші answers (2_00030), тож міряти треба обидва боки.
- П2. Stability і теорія [5]: жоден concept не змінив node чи edge count після file 37, більшість — за кілька files. Кроки — не epochs: кожен file проходить reduction один раз. Bounded part of convergence — структура, envelopes і далі вбирають variation. Order independence випливає з commutativity of accumulation у теорії [5]; controlled experiment — окремо, після виправлення pairing step.
- П3. Comparison з іншими роботами: [15, 16] знаходять failures ззовні, за subsets of inputs, а тут кожна wrong-class answer прив'язана до decision step; [17, 18] зупиняються на skeleton, а тут видно, як skeleton defect змінює клас; [8–11] міряють distance, а тут видно, де вона помиляється в classifier.
- П4. Practical significance: де застосовувати (задачі, де рішення треба перевіряти й пояснювати); умови (images with complete contours, див. 23,94 % на incomplete); expected effect (correction можна спрямувати на конкретний decision step і заздалегідь оцінити, скільки помилок він зачепить).
- П5. Limitations: метод моделює біологічні механізми (виділення контуру, скелет, ріст мережі вузлів), але їхні реалізації неідеальні, тож частина структур і skeletons спотворена ще до formation і classification: pruning зрізає кінці, spurs додають endpoints, junctions зливаються (рис. 5, 6, 8; gate 38,0 %). Growing neural gas ставить nodes ітеративно й не гарантує однакову convergence: [число з перевірки GNG, якщо її зробимо]. Далі: два стани системи (91,13 % і retrained 90,05 %), тож census описує retrained concepts; structural marker порівнює counts, а не attributed graphs; sample-count study — три concepts і без classification runs; traces пояснюють окремі images, а census дає розмір mechanism, але не причину кожного case. Інші traces — у repository [20].
- П6. Prospects за порядком: gate errors class 4 і pruning rule, бо вони прибирають true concept зі змагання; complexity prior переглядати лише з підрахунком rescued answers; classification runs для кожної sample-count умови; order experiment після виправлення pairing step.

### 5. Conclusions

Журнал вимагає: один висновок на кожне завдання; у кожному — особливість результату, чим пояснюється, числа.
- 1 (завдання 1): структура стабілізується за 1–37 training files на concept, задовго до кінця cohort; envelopes — за окремим графіком, раніше чи пізніше за структуру; stopping rule має стежити за обома markers.
- 2 (завдання 2): більше samples — smaller graph і wider envelopes; 13 concepts зберігають 106 із 9 738 nodes, compression 91,9× за nodes і 50,6× за values.
- 3 (завдання 3): усі 820 wrong-class answers — три mechanisms: true concept не дійшов до comparison (312), програв на similarity (383), вів на similarity й програв через prior (125). Traces прив'язують кожен mechanism до decision step: skeleton pruning, spur, що міняє topology, junction, втрачений у graph construction, deletions дешевші за out-of-range features, prior term більший за similarity gap.

### Кінцеві розділи

Conflicts of interest, Funding і Data Availability заповнено стандартними формулюваннями журналу. Author Contributions і Use of artificial intelligence пишеш сам: журнал вимагає назвати модель, де й для чого її використано, як перевірено результат і чи вплинула вона на висновки.

## Рисунки

| № | Файл у `../../figures/anatomy_ais/` | Що показує |
|---|---|---|
| 1 | `trajectories.png` | Node count (суцільна, ліва вісь) і mean envelope width (штрихова, права вісь) кожного concept від кількості training files; пунктир — *m*<sub>topo</sub> (синій) і *m*<sub>env</sub> (помаранчевий) |
| 2 | `curves.png` | (a) node count і (b) mean envelope width для 2_2, 7_1, 4_1 при 2, 5, 10, 20 training files; точки — три draws, лінії — середні |
| 3 | `pairs.png` | Ten most frequent confusion pairs: gate (синій), similarity (помаранчевий), prior (зелений) |
| 4 | `gate_reasons.png` | (a) gate errors за комбінацією rejection messages per image; (b) rejections за message per true-class concept |
| 5 | `case2_pipeline.png` | mnist_test_2_00144: image, binary mask, skeleton і graph; чорним — pruned tail основи. Коло — endpoint, ромб — corner point, великий квадрат — intersection point, малий — vector |
| 6 | `case3_pipeline.png` | mnist_test_0_00701, markers як на рис. 5: spur угорі лишився після pruning |
| 7 | `case1_ranking.png` | mnist_test_5_00606: raw similarity (порожнє коло) і adjusted score (повне); зелений — predicted concept, чорний — true concept |
| 8 | `case6_pipeline.png` | mnist_test_4_00755: два junctions skeleton стали однією intersection of degree 4, corner point немає |
| 9 | `case8_matching.png` | mnist_test_4_00487: node matching під 4_2 (угорі) і 7_1 (унизу). Лінія — substitution, темніша = дорожча, товста = out-of-range feature; зірка — start point S; хрестик — deleted node; штрих — deleted edge; блідий — removed by preprocessing |

## Таблиці

1. Convergence markers: *m*<sub>topo</sub>, *m*<sub>env</sub> і кількість training files кожного concept.
2. Compression: training files, nodes in → kept, node compression і value compression.
3. Concepts of the 91.13 % configuration на інших MNIST splits без retraining: submitted, classified, correct, conditional і end-to-end accuracy, DLQ, no result.

## Формули

- (1) *s* = 1 − *c* / (*c* + max(*n*<sub>1</sub>, *n*<sub>2</sub>)): *c* — GED, *n*<sub>1</sub>, *n*<sub>2</sub> — nodes плюс edges image graph і concept після preprocessing.
- (2) *ŝ* = *s* + λ log<sub>2</sub> *K*: *K* — complexity of the concept, λ = 0,10 (complexity prior).
- GED costs: deletion of an image node or edge 0,25; insertion of a concept node 6; substitution of nodes with different labels 6; substitution of nodes with the same label — weighted sum of feature deviations, 1 за кожну out-of-range feature.
- *m*<sub>topo</sub> — останній training file, що змінив node чи edge count. *m*<sub>env</sub> — file, з якого починаються п'ять поспіль files із приростом mean envelope width менше 0,02 на file.
- Compression counting rule: range — два values, scalar чи string — один, list — поелементно, однаково для input і concept.
- Confidence interval of accuracy — Wilson interval, 95 %.

## Числа

| Число | Джерело |
|---|---|
| 91,13 %, 13 концептів, 869 файлів | `experiments/run_20260630_235356/findings.md` |
| 7 819 із 8 683 = 90,05 % (Вілсон 89,40–90,66 %); 21 збій конвеєра; 44 відхилено всіма концептами | `experiments/run_20261023_155807/metrics.csv`, `incorrect_results.csv` |
| 820 помилок: шлюз 312 (38,0 %: 277 передобробка, 31 пре-фільтр, 4 обидва), подібність 383 (46,7 %), пріор 125 (15,2 %; без пріора 113 правильні) | vault `raw/analyses/error_anatomy_ais_2026/data.json`, ключ `population` |
| Пари: 10 найчастіших = 542 (66,1 %); 2→7 подібність 90 із 93; 0→6 46 із 52; 9→4 27 із 27; 2→6 шлюз 56 із 65; 4→1 40 із 41; 5→3 пріор 55 із 56; 7→2 21 із 26; 4→7 36 шлюз і 44 подібність; 4→5 26 і 45; 2→3 21 подібність і 10 пріор | там само |
| Повідомлення на концепт: немає кінцевих точок 141, кутів 115, перетинів 111. На зображення: «немає кутів + перетинів» 100 (усі клас 4), «немає кінцевих точок» 82 (56 клас 2), ліміт ітерацій 37 (15 клас 8, 10 клас 0), пре-фільтр 31 | там само |
| Клас 4: 209 помилок, клас 2: 216; 4→1: 39 без кута, 28 з чотирма кінцевими точками, 11 з п'ятьма; 1_1 виграє 37, 1_3 — 3; 4→7: 35 із 36 тими самими повідомленнями | там само |
| Таблиця 1 і рис. 1 | `src/training/training_results/formation_probes/convergence/` |
| Рис. 2: вузли 2_2 16 → 12,7 → 12 → 12; оболонка 7_1 0,33 / 0,48 / 0,68 / 0,80; вузли 4_1 9,3 → 8 | `src/training/training_results/formation_probes/sample_count/` |
| Стиснення: 9 738 вузлів, 9 242 ребра, 336 637 значень → 106 вузлів, 100 ребер, 6 647 значень (3 053 діапазони); 91,9× за вузлами, 176,7× для 2_1, 50,6× за значеннями; ~60 властивостей вузла | vault `raw/analyses/error_anatomy_ais_2026/check_concepts.json` |
| Таблиця 3: тест 82,69 % умовна / 82,21 % наскрізна; повні 7 911 із 8 704 (90,89 %), неповні 310 із 1 295 (23,94 %); трейн 45 501 повних, класифіковано 98,49 %, 85,85 %; усі 70 000 — 73,42 % | vault `raw/analyses/supervisor_program_2026_07/dataset_variants_findings.md`, `experiments/run_20260717_161201/` |
| Випадки: 2_00144 скелет 168 px, гілка 12,5 px < поріг 15,7 px (8 % від 196,6), подібність 6_1 0,6892 / 9_2 0,6742 / 4_1 0,6441. 0_00701 відросток 15,4 px > поріг 13,1 px, заміна вузла 4,1419, 0_1 0,5868, 6_1 0,7120. 5_00606: 5_1 GED 6,7259, *s* 0,7880, пріор +0,3700; 3_1 GED 7,8362, *s* 0,7614, пріор +0,4087, різниця 0,0121. 2_00030: 7_1 0,7679 проти 2_1 0,7591, 2_1 виграє на 0,0442. 4_00755: 1_3 0,6489, 7_1 0,5973, 1_1 0,5815, 1_1 скоригована 0,9515. 4_00487: 4_2 GED 10,6695, *s* 0,6144; 7_1 GED 4,4255, *s* 0,7460; 1,0630 проти 1,0231; медіани 44 випадків 0,7428 і 0,6025 | vault `raw/analyses/error_anatomy_ais_2026/data.json`, ключ `cases`; `raw/analyses/itssi_xai_2026/traces_20261023/verification/` |
| 2→7 у конфігурації 91,13 %: 111 помилок, у 110 петля без отвору вже в масці | vault `raw/evidence/2026-08-01_blue_remarks/` |

## Джерела

Номери — як у списку шаблону. Самоцитувань 5 із 20 (25 %, межа журналу).

| № | Що зроблено | Що лишається відкритим для нас |
|---|---|---|
| 1 | Rudin: для рішень високої ціни потрібні інтерпретовні моделі, а не пояснення чорних скриньок | Не вимірює стабільність класів моделі |
| 2 | Rudin та ін.: десять задач інтерпретовного ML | Формування графових концептів серед них немає |
| 3–5, 7 | Наші: модель без зворотного поширення, енергетичні моделі, теорія атракторів, точність 91,13 % | Формування в часі й повний облік помилок не виміряно |
| 6 | MNIST | — |
| 8 | Gao та ін.: огляд алгоритмів GED | Порівнює алгоритми, не помилки класифікатора |
| 9 | Bougleux та ін.: GED як квадратична задача про призначення | Обчислення відстані, не рішення |
| 10 | Blumenthal та ін.: порівняння евристик GED | Помилки класифікатора поза дослідженням |
| 11 | Riba та ін.: GED, навчена графовою нейромережею | Залежить від градієнтного навчання |
| 12 | Barredo Arrieta та ін.: огляд і таксономія XAI | Огляд, модель не тестує |
| 13 | Yuan та ін.: таксономія пояснень GNN post hoc | Пояснює навчену глибоку модель постфактум |
| 14 | Ji та ін.: прототипні мережі для few-shot | Клас — точка, навчена градієнтом; збіжність редукції не розглянуто |
| 15 | Oakden-Rayner та ін.: приховані збої на підмножинах медичних зображень | Збій прив'язаний до підмножини входів, не до кроку рішення |
| 16 | Geirhos та ін.: shortcut learning | Кроки мережі не прочитати, групувати помилки за кроком нема як |
| 17 | Gan та ін.: ієрогліфи як скелетні графи | Мета — розпізнавання, не облік помилок |
| 18 | Bai та ін.: обрізання скелета без хибних гілок | Вплив обрізаної гілки на клас відкритий |
| 19 | Fritzke: growing neural gas | Метод побудови графа |
| 20 | Репозиторій проєкту | Додаткові розбори випадків |
