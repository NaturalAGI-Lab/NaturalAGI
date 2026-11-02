"""Content of the AIS submission (NIK-369).

Inline markup understood by build_docx.py:
    **bold**  *italic*  <sub>x</sub>  <sup>x</sup>

Citations are written as [@key] or [@key1, @key2]. At import time they are
numbered in order of first appearance and REFERENCES is built in that order.

Sources of every number:
  stability   src/training/training_results/formation_probes/ (convergence,
              sample_count), run_20260717_* exports, supervisor_program_2026_07
  errors      experiments/run_20261023_155807 and the PhD vault
              raw/analyses/itssi_xai_2026/traces_20261023/verification/
"""
import re

UDC = "UDC 004.93'1:004.932:004.032.26"

TITLE = ("FORMATION STABILITY AND ERROR MECHANISMS OF A GRAPH CONCEPT "
         "CLASSIFIER TRAINED WITHOUT BACKPROPAGATION")

AUTHORS = ("Mykyta Lapin<sup>1</sup>, Kostiantyn Bokhan<sup>1</sup>, "
           "Yurii Parzhyn<sup>2</sup>, Kyrylo Perevoznyk<sup>1</sup>, "
           "Tetiana Aleksandrova<sup>1</sup>")

AFFILIATIONS = [
    '<sup>1</sup> National Technical University "Kharkiv Polytechnic '
    'Institute", Kharkiv, Ukraine',
    "<sup>2</sup> Augusta University, Augusta, USA",
]

ABSTRACT = [
    ("Relevance.", "When every class of a classifier is kept as an explicit "
     "graph, each step of a decision is open to inspection, but two questions decide whether that "
     "inspection is worth anything: when does a stored class stop changing "
     "as training samples arrive, and can every wrong answer be traced to "
     "the stage that produced it."),
    ("The object of research", "is a handwritten-digit classifier trained "
     "without backpropagation. Each image becomes a skeleton graph with "
     "attributes; the graphs of a subclass are merged by reduction into one "
     "concept graph, "
     "and decides by a similarity derived from graph edit distance plus a "
     "prior on concept complexity."),
    ("The subject of the research", "is the stabilization of concept graphs "
     "during formation and the mechanisms that produce misclassifications."),
    ("The purpose of this paper", "is to measure how early concepts stop "
     "changing and what more samples do to them, and to assign every "
     "wrong-class answer of a test run to the decision step that caused it."),
    ("Research Results.", "Across thirteen concepts the node and edge counts "
     "stop changing after 1 to 37 training files, while the coordinate "
     "envelopes settle on a separate schedule; more samples give a smaller "
     "graph with wider envelopes. Concepts keep 106 nodes out of 9,738 in "
     "the 869 training graphs. Of 820 wrong-class answers on 8,683 classified "
     "complete-contour MNIST test images, 312 arise because no concept of "
     "the true class reaches comparison, 383 because the winner has the "
     "higher raw similarity, and 125 because the complexity prior reverses a "
     "true-class lead. Traced cases show where each mechanism starts: "
     "skeleton pruning that removes a stroke end, a spur that gives a zero "
     "the topology of a six, a junction of an open four lost in graph "
     "construction, deletions cheaper than missed feature ranges, and a "
     "prior term larger than the similarity gap. A version without the "
     "two constants fitted to the test set reaches 92.90% on 8,708 "
     "complete-contour images against 90.89% for the original model."),
    ("Conclusions.", "Formation settles within tens of samples, and a "
     "stopping rule must watch structure and envelopes separately. Most "
     "errors originate before scoring, in graph construction and in the "
     "structural check, so the next corrections belong there rather than in "
     "the cost weights."),
]

KEYWORDS = ("structural pattern recognition; graph edit distance; concept "
            "formation; explainable artificial intelligence; error analysis; "
            "handwritten digit recognition; learning without backpropagation")

# --------------------------------------------------------------------------
# Body
# --------------------------------------------------------------------------

SECTIONS = [
 {
  "title": "Introduction",
  "blocks": [
   ("p", "**Problem statement.** Image classifiers trained by gradient "
     "descent reach high accuracy but hold what they learn in weights that "
     "no one can read. Post hoc explanations of such models describe the "
     "model only approximately, and for decisions that need an audit an "
     "inherently readable model is the safer choice [@rudin2019, "
     "@rudin2022]. Our group develops one such model: a classifier that "
     "stores each digit subclass as an attributed graph, forms that graph "
     "by structural reduction of a few training graphs, and decides by "
     "graph matching [@lapin2025asu, @parzhyn2025ais, @lapin2026itssi]. "
     "Every node, edge and parameter range of a concept can be printed and "
     "checked."),
   ("p", "Readability alone does not make the model trustworthy. Two "
     "properties still have to be measured. The first is stability: a "
     "concept that keeps changing with every new sample cannot serve as a "
     "fixed reference, and the theory behind the model claims that a "
     "concept converges to an attractor in a bounded number of steps "
     "[@lapin2026itssi]. The second is accountability of errors: if the "
     "model is readable, each wrong answer should be traceable to the step "
     "where it arose, and the errors as a whole should split into causes "
     "that point to specific corrections."),
   ("p", "Our earlier reports give accuracy and explain single decisions. "
     "On MNIST test images whose contours are complete [@lecun1998] the "
     "system decides 91.13% of the classified images correctly with 13 "
     "concepts [@lapin2026dessert]. They trace the most frequent confusion, "
     "a 2 read as a 7, to the binarized image, but they do not measure "
     "formation over time and do not account for the remaining errors. "
     "This paper closes both gaps."),
  ],
 },
 {
  "title": "Analysis of Recent Research and Publications",
  "blocks": [
   ("p", "**Graph matching.** Graph edit distance (GED) is the usual "
     "error-tolerant dissimilarity between attributed graphs. Exact GED is "
     "NP-hard, and recent work follows two lines: approximations that "
     "recast it as an assignment problem and compare heuristics on shared "
     "benchmarks [@bougleux2017, @blumenthal2019], and distances learned "
     "with graph neural networks [@riba2021]. Both lines judge a method by "
     "retrieval or classification accuracy on benchmark collections. How a "
     "complete classifier built on GED fails, error by error, is rarely "
     "reported."),
   ("p", "**Interpretable models.** Surveys of explainable artificial "
     "intelligence separate post hoc explanation of opaque models from "
     "models that are interpretable by construction [@barredo2020, "
     "@rudin2022]. Few-shot image models often keep one prototype per "
     "class, learned as a point in an embedding space by gradient descent "
     "[@ji2020]. The stability of such a prototype as data accumulates is "
     "tied to the optimizer and the backbone. A concept that is formed by "
     "reduction alone, with no gradient step, raises the question of "
     "convergence directly."),
   ("p", "**Error analysis.** Aggregate accuracy can hide failures that "
     "concentrate in a subgroup of inputs [@oakden2020], and deep models "
     "fail systematically when they rely on shortcut features that do not "
     "transfer [@geirhos2020]. In both lines the cause of a failure is "
     "inferred from outside the model. In a structural model the decision "
     "steps are explicit, so errors can be grouped by the step that "
     "decided them."),
   ("p", "**Skeleton graphs of handwriting.** Representing handwritten "
     "characters as skeleton graphs makes recognition easier to interpret "
     "[@gan2023], but the graph inherits every defect of the skeleton: "
     "spurs, broken strokes and merged loops change the topology that later "
     "stages rely on. Our pipeline builds the graph with a growing neural "
     "gas over the skeleton [@fritzke1995], so its front end is exposed to "
     "the same effects."),
   ("p", "**Unsolved part.** No published study measures when the concept "
     "graphs of a non-gradient structural classifier stop changing, and "
     "none splits all errors of such a classifier into mechanisms tied to "
     "its decision steps."),
  ],
 },
 {
  "title": "Purpose and Tasks of the Article",
  "blocks": [
   ("p", "The purpose is to measure the stabilization of concept graphs "
     "during formation and to assign every wrong-class answer of a test run "
     "to the decision step that caused it. The tasks are:"),
   ("p", "1) to record, for each concept, when its structure and its "
     "parameter envelopes stop changing during one formation pass;"),
   ("p", "2) to measure how structure and envelopes depend on the number of "
     "training samples, how strongly formation compresses the training "
     "graphs, and how the concepts transfer to other MNIST splits;"),
   ("p", "3) to split all wrong-class answers of a test run into mechanisms "
     "defined by the decision steps, and to trace representative cases of "
     "each mechanism from pixels to ranking;"),
   ("p", "4) to measure a version of the classifier without the constants "
     "that had been fitted to the test set."),
  ],
 },
 {
  "title": "The Classifier",
  "blocks": [
   ("p", "The pipeline is described in detail in [@lapin2026itssi, "
     "@lapin2026dessert]; this section fixes the terms used below. An "
     "image of 100 × 100 pixels is binarized at threshold 110 and thinned "
     "to a one-pixel skeleton. Branches that run from an intersection to a "
     "free end and are shorter than max(8% of the skeleton length, 5 px) "
     "are pruned. A growing neural gas places nodes on the skeleton, and "
     "the result is a graph of points and vectors. Points are labelled as "
     "endpoints E, corner points C and intersection points I; vectors are "
     "the stroke segments between them. Thirteen geometric features, "
     "mapped to [0, 1] when the graph is written, describe each node. The "
     "complexity of a graph is its number of nodes plus edges."),
   ("p", "A concept is formed from the training graphs of one subclass. "
     "Each new graph is reduced to the structure it shares with the "
     "current concept, and the concept stores, for each feature of each "
     "node, the range of values seen so far. We call these ranges the "
     "envelope of the concept. The 13 concepts of this paper cover the ten "
     "digits; digits 1, 2, 4 and 9 have two subclasses each, of which 1_2 "
     "and 9_1 are not in use."),
   ("p", "Classification runs in four steps. The complexity pre-filter drops "
     "every concept more complex than the image. For each remaining concept "
     "a preprocessor places a start point S on the image graph and reduces "
     "its endpoints, intersections and corners towards the concept's "
     "structure; if this fails, the concept is rejected with a message such "
     "as «concept has endpoints but image does not». The message describes "
     "the image graph after this concept-specific preprocessing, not the "
     "raw image. Accepted concepts are compared by GED with fixed costs: "
     "deleting an image node or edge costs 0.25, inserting a concept node "
     "6, substituting nodes of different labels 6, and substituting nodes "
     "of the same label costs the weighted sum of feature deviations, with "
     "1 for each feature outside the concept's range. The similarity is"),
   ("eq", "*s* = 1 − *c* / (*c* + max(*n*<sub>1</sub>, *n*<sub>2</sub>)),",
    "1"),
   ("p", "where *c* is the GED, and *n*<sub>1</sub> and *n*<sub>2</sub> "
     "count the nodes and edges of the image graph and of the concept "
     "after preprocessing. Accepted concepts "
     "are ranked by the adjusted score"),
   ("eq", "*ŝ* = *s* + λ log<sub>2</sub> *K*,", "2"),
   ("p", "where *K* is the concept complexity and λ = 0.10. The prior term "
     "favours the richer concept when two concepts match about equally "
     "well. The winner names the class."),
  ],
 },
 {
  "title": "Stabilization of Concept Formation",
  "blocks": [
   ("p", "The stability measurements replay formation offline on the cached "
     "training graphs with the production formation code and do not write "
     "to the deployed concept store. They concern the 13 concepts of the "
     "91.13% configuration [@lapin2026dessert], formed from 869 training "
     "files. The 4_1 cohort holds 36 files: six files that mixed open and "
     "closed shapes of the digit 4 were taken out, because formation could "
     "not merge the two shapes into one concept."),
   ("h2", "Two markers of convergence"),
   ("p", "For each concept we record two markers over one formation pass. "
     "The structural marker *m*<sub>topo</sub> is the last training file "
     "that changed the node or edge count of the concept. It compares "
     "counts only, so a rearrangement that keeps the counts is not seen. "
     "For the envelope marker *m*<sub>env</sub> we take the file at which "
     "a run of five consecutive files begins in which the mean envelope "
     "width grows by less than 0.02 per file. It marks the onset of slow "
     "growth: envelopes keep widening slowly after it."),
   ("tbl", 1,
    "Convergence markers of concept formation",
    ["Concept", "*m*<sub>topo</sub>", "*m*<sub>env</sub>", "Files"],
    [["0_1", "11", "13", "33"],
     ["1_1", "1", "10", "33"],
     ["1_3", "2", "5", "55"],
     ["2_1", "23", "12", "121"],
     ["2_2", "5", "12", "55"],
     ["3_1", "4", "13", "77"],
     ["4_1", "2", "10", "36"],
     ["4_2", "2", "12", "65"],
     ["5_1", "28", "11", "88"],
     ["6_1", "12", "18", "77"],
     ["7_1", "2", "15", "99"],
     ["8_1", "37", "5", "42"],
     ["9_2", "16", "10", "88"]],
    "column", [0.34, 0.22, 0.22, 0.22], []),
   ("p", "The structural marker falls between 1 and 37 files (Table 1). "
     "Concepts with a single open stroke settle at once: 1_1 after the "
     "first file, 1_3, 4_1, 4_2 and 7_1 after the second. Concepts with "
     "loops or several strokes take tens of files: 8_1 changes its counts "
     "until file 37 of 42, 5_1 until 28 and 2_1 until 23. Every concept "
     "settles well before its cohort is used up; 2_1, the largest cohort, "
     "settles at file 23 of 121."),
   ("p", "The envelope marker does not follow the structural one. For 8_1 "
     "the widths flatten at file 5 while the graph keeps changing until "
     "file 37. The same order holds for 2_1 (envelope at file 12, "
     "structure at 23) and 5_1 (11 and 28). For 7_1 the order is "
     "reversed: the structure is fixed at file 2 and the envelope settles "
     "at file 15. A flat envelope is therefore not a safe signal that "
     "formation has finished, and a stopping rule has to check both "
     "markers (Fig. 1)."),
   ("fig", "trajectories.png", 1,
    "Node count and mean envelope width of each concept against the number "
    "of training files consumed in one formation pass", "full"),
   ("h2", "Dependence on the number of samples"),
   ("p", "Three concepts of different kinds, 2_2 (loop and intersection), "
     "7_1 (one open stroke) and 4_1 (closed four), were formed repeatedly "
     "on random subsets of their cached files: three subsets each of size "
     "2, 5, 10 and 20 (Fig. 2). More files move structure and envelope in opposite "
     "directions. The node count of 2_2 falls from 16 at two files to 12.7 "
     "at five and to 12 at ten and twenty: early concepts carry nodes that "
     "later samples do not share, and reduction removes them. For 7_1 the "
     "mean envelope width is 0.33, 0.48, 0.68 and 0.80 at 2, 5, 10 and 20 "
     "files, since each sample adds its own variation. In 4_1 the "
     "structure does not move at all: from the second file on the concept "
     "has 8 nodes and 8 edges."),
   ("fig", "curves.png", 2,
    "Node count and mean envelope width against the number of training "
    "files for 2_2, 7_1 and 4_1; three draws per condition", "full"),
   ("p", "More samples buy a smaller graph and looser bands. These probe "
     "concepts were not deployed, so the test does not say which of the two "
     "effects helps recognition more; a classification run per condition "
     "is the next step."),
   ("h2", "Compression"),
   ("p", "The 869 training graphs hold 9,738 nodes and 9,242 edges with "
     "336,637 stored values; the 13 concepts keep 106 nodes and 100 edges "
     "with 6,647 values, of which 3,053 are ranges. A range counts as two "
     "values (its bounds), every scalar or string counts once, lists are "
     "counted per element, and the rule is the same for input and concept. Node compression is 91.9 times overall and "
     "reaches 176.7 times for 2_1; value compression is 50.6 times "
     "(Table 2). These ratios compare what formation consumed with what it "
     "kept. They are not parameter counts and are not comparable with the "
     "size of a neural network. Image graphs carry about 60 node "
     "properties, and formation drops only one of them, the path of the "
     "source file; the concepts "
     "gain aggregate properties that no single image node has, such as the "
     "expected degree of the start point."),
   ("tbl", 2,
    "Compression from training graphs to concepts",
    ["Concept", "Files", "Nodes in → kept", "Node ×", "Value ×"],
    [["0_1", "33", "418 → 10", "41.8", "23.2"],
     ["1_1", "33", "235 → 7", "33.6", "18.3"],
     ["1_3", "55", "187 → 3", "62.3", "34.6"],
     ["2_1", "121", "1,237 → 7", "176.7", "96.8"],
     ["2_2", "55", "902 → 12", "75.2", "41.5"],
     ["3_1", "77", "1,093 → 9", "121.4", "67.8"],
     ["4_1", "36", "400 → 8", "50.0", "27.4"],
     ["4_2", "65", "631 → 9", "70.1", "38.3"],
     ["5_1", "88", "1,192 → 7", "170.3", "93.4"],
     ["6_1", "77", "1,050 → 10", "105.0", "58.6"],
     ["7_1", "99", "669 → 5", "133.8", "73.0"],
     ["8_1", "42", "646 → 11", "58.7", "32.8"],
     ["9_2", "88", "1,078 → 8", "134.8", "74.5"],
     ["**Total**", "**869**", "**9,738 → 106**", "**91.9**", "**50.6**"]],
    "column", [0.18, 0.16, 0.30, 0.18, 0.18], [13]),
   ("h2", "Transfer to other MNIST splits"),
   ("p", "The system reads contours, so a digit with a broken stroke gives a "
     "skeleton that no concept formed from closed contours can cover. The "
     "concepts were therefore also run, without retraining, on the whole "
     "MNIST test set and on the 60,000-image training split (Table 3). A "
     "submitted image is either classified, sent to the dead-letter queue "
     "(DLQ) after a pipeline failure, or left without a result. Conditional "
     "accuracy divides by classified images, end-to-end accuracy by all "
     "submissions."),
   ("tbl", 3,
    "Concepts of the 91.13% configuration on other MNIST splits, no "
    "retraining",
    ["Split", "Submitted", "Classified", "Correct", "Conditional",
     "End-to-end", "DLQ", "No result"],
    [["Test, all", "10,000", "9,942", "8,221", "82.69%", "82.21%", "58",
      "0"],
     ["Train, all", "60,000", "51,045", "43,172", "84.58%", "71.95%", "293",
      "8,662"],
     ["Test + train", "70,000", "60,987", "51,393", "84.27%", "73.42%",
      "351", "8,662"],
     ["Train, complete", "45,501", "44,812", "38,469", "85.85%", "84.55%",
      "14", "675"]],
    "full", [0.17, 0.11, 0.11, 0.11, 0.13, 0.13, 0.11, 0.13], []),
   ("p", "On the whole test set the complete slice scores 7,911 of 8,704 "
     "(90.89%) end-to-end and the incomplete slice 310 of 1,295 (23.94%), "
     "which brings the total to 82.21%. On the training split the "
     "completeness labels come from a heuristic rather than manual review. "
     "The first run over this split left 8,662 submissions without a "
     "result; a dedicated rerun over its 45,501 complete images classified "
     "98.49% of them at 85.85% conditional accuracy. The remaining gap to "
     "the test figure fits label noise in the heuristic, which we did not "
     "isolate. Over all 70,000 MNIST images the 13 concepts reach 73.42% "
     "end-to-end with no per-split tuning."),
  ],
 },
 {
  "title": "Mechanisms of Misclassification",
  "blocks": [
   ("p", "The error analysis needs the full ranking of every concept for "
     "every image, which the 91.13% run did not store, and its concepts "
     "were retrained afterwards. We therefore repeated the test with "
     "concepts retrained on the same 869 files and the same classification "
     "parameters, storing every ranking. The run decided 7,819 of 8,683 "
     "classified images correctly, 90.05% (95% Wilson interval "
     "89.40–90.66%); 21 images failed in the pipeline and 44 were "
     "rejected by all 13 concepts. All numbers in this section come from "
     "this run, and every trace was recomputed with the production scoring "
     "code and matched the stored ranking."),
   ("h2", "Three mechanisms"),
   ("p", "Each of the 820 wrong-class answers falls into exactly one of three "
     "mechanisms, defined by the decision step that settled it:"),
   ("p", "– **gate** (312, 38.0%): no concept of the true class reached "
     "comparison. In 277 cases preprocessing rejected all of them, in 31 "
     "the complexity pre-filter removed all of them, and in 4 the two "
     "steps removed one each;"),
   ("p", "– **similarity** (383, 46.7%): a true-class concept was compared "
     "but its raw similarity was lower than the winner's;"),
   ("p", "– **prior** (125, 15.2%): a true-class concept had a raw "
     "similarity at least as high as the winner's and lost only after the "
     "prior term of (2). Without the prior, 113 of these answers would be "
     "correct; in the other 12 a third concept of another class leads on "
     "raw similarity."),
   ("p", "No ties occur on raw similarity between the true-class concept and "
     "the winner, and none on the adjusted score among the 125 prior "
     "cases, so the sort order never decides."),
   ("p", "The mechanisms concentrate in different pairs (Fig. 3). The ten "
     "most frequent pairs hold 542 answers (66.1%). The pair 2→7 is almost "
     "all similarity (90 of 93), as are 0→6 (46 of 52) and 9→4 (27 of 27). "
     "The pairs 2→6 (56 of 65) and 4→1 (40 of 41) are almost all gate. "
     "The prior dominates 5→3 (55 of 56) and 7→2 (21 of 26). Class 4 "
     "mixes gate and similarity: 4→7 has 36 gate and 44 similarity cases, "
     "4→5 has 26 and 45. The pair 2→3 has 21 similarity and 10 prior "
     "cases."),
   ("p", "The gate messages show what preprocessing found missing in the "
     "image graph (Fig. 4). Counted per rejected true-class concept, the "
     "most common are «concept has endpoints but image does not» (141), "
     "«concept has corner points but image does not» (115) and «concept "
     "has intersection points but image does not» (111). Counted per "
     "image, the pair «no corner points» plus «no intersection points» "
     "accounts for 100 gate errors, all of class 4, and «no endpoints» "
     "alone for 82, of which 56 are of class 2. In Fig. 4 «no endpoints» "
     "stands for the first message, and likewise for corners and "
     "intersections. «Too few» means the concept has more points of that "
     "type than the image. «Iteration limit» means the critical-point "
     "graphs were still not isomorphic after five reduction iterations "
     "(37 images, 15 of them of class 8 and 10 of class 0), and «pre-filter» "
     "means the concept is larger than the image (31 images)."),
   ("fig", "anatomy_ais/pairs.png", 3,
    "The ten most frequent confusion pairs by number of errors: gate (blue), "
    "similarity (orange) and prior (green)", "full"),
   ("fig", "anatomy_ais/gate_reasons.png", 4,
    "Number of gate errors by the combination of rejection messages per image "
    "(top) and number of rejections by message per true-class concept "
    "(bottom)", "full", 0.85),
   ("h2", "Gate: a pruned stroke end (2 read as 6)"),
   ("p", "Image mnist_test_2_00144 is a 2 classified as 6_1; both concepts "
     "of class 2 were rejected before comparison (Fig. 5). Its skeleton "
     "has 168 pixels. Pruning removed a 12.5 px branch from the "
     "intersection at (57, 69) to the end at (67, 75), because it was "
     "shorter than the threshold of 15.7 px, 8% of the 196.6 px skeleton "
     "length. This branch was the tail of the base of the 2. Without it "
     "the lower part of the digit is a closed loop, and the graph has one "
     "free end, at the top of the upper stroke, one intersection of degree "
     "3, six corners and one cycle."),
   ("p", "Both class-2 concepts expect a start point S of degree 1 and one "
     "more endpoint. The preprocessor turns the only free end into S, so "
     "the image graph has no endpoint left, and both concepts are rejected "
     "with «concept has endpoints but image does not». The concepts that "
     "pass are 6_1, 9_2 and 4_1: each has a loop, an intersection and no "
     "endpoint besides S. 6_1 wins with similarity 0.6892 against 0.6742 "
     "and 0.6441, and the prior does not change the order. The error "
     "starts at pruning, which removed an end that the 2 needs."),
   ("fig", "anatomy_ais/case2_pipeline.png", 5,
    "mnist_test_2_00144: image (left), binary mask (centre), skeleton and "
    "graph (right). Black marks the pruned base tail. Circle: endpoint; "
    "diamond: corner; large square: intersection; small square: vector",
    "full"),
   ("h2", "Similarity: a spur turns a 0 into a 6"),
   ("p", "Image mnist_test_0_00701 is a 0 classified as 6_1 (Fig. 6). A "
     "15.4 px spur runs from the top of the loop to a free end; the pruning "
     "threshold for this skeleton is 13.1 px, so the spur stays. The graph "
     "has one endpoint, one intersection of degree 3, five corners and one "
     "cycle, which is the topology of a 6. Concepts 6_1, 9_2, 4_1 and 0_1 "
     "pass preprocessing. Under 0_1 the spur is deleted and S is placed on "
     "the former intersection. That node then sits where no start point of "
     "0_1 lies: four of the twelve out-of-range features fall on it, and "
     "its substitution alone costs 4.1419. 0_1 reaches similarity 0.5868 "
     "and ranks fourth; 6_1 has five out-of-range features and wins with "
     "0.7120. Both concepts have complexity 20, so the prior adds the same "
     "term to both. The error is decided by the similarity function on a "
     "graph whose topology really is that of another class."),
   ("fig", "anatomy_ais/case3_pipeline.png", 6,
    "mnist_test_0_00701, panels and markers as in Fig. 5: the spur at the top "
    "survives pruning and gives the zero an endpoint and an intersection",
    "full"),
   ("h2", "Prior: a correct lead lost by 0.0121"),
   ("p", "Image mnist_test_5_00606 is a 5 classified as 3_1. Its graph is "
     "one open stroke with two endpoints and five corners, complexity 25. "
     "Concept 5_1 has GED 6.7259, one out-of-range feature and similarity "
     "0.7880; concept 3_1 has GED 7.8362, two out-of-range features and "
     "similarity 0.7614. The prior adds 0.3700 to 5_1 (complexity 13) and "
     "0.4087 to 3_1 (complexity 17). 5_1 leads on raw similarity by "
     "0.0266, the prior gives 3_1 0.0387 more, and 3_1 wins by 0.0121 "
     "(Fig. 7). The other eight concepts do not reach comparison: 2_2, 4_1, "
     "6_1 and 9_2 find no intersection in the image graph, 0_1 and 8_1 find "
     "no corner, and 1_1 and 4_2 have more endpoints than the image."),
   ("fig", "anatomy_ais/case1_ranking.png", 7,
    "mnist_test_5_00606: raw similarity (open circle) and adjusted score "
    "(filled circle) of the compared concepts. Green: predicted concept; "
    "black: true concept", "column", 0.75),
   ("p", "The same term also repairs answers. In mnist_test_2_00030, a 2 "
     "with a short spur at the intersection, 7_1 leads on raw similarity "
     "with 0.7679 against 0.7591 for 2_1; the prior adds 0.3700 to 2_1 and "
     "0.3170 to 7_1, and 2_1 wins by 0.0442. In both cases the raw gap is "
     "smaller than the difference between the two prior terms. The prior "
     "decides wherever the similarity cannot separate two concepts, and "
     "whether it decides correctly depends on which of the two is the "
     "richer one."),
   ("h2", "Class 4: a lost junction and a cheaper small concept"),
   ("p", "Class 4 gives 209 of the 820 wrong-class answers, second only to "
     "class 2 with 216, through both gate and similarity. Image mnist_test_4_00755 is an "
     "open 4 classified as 1_1 (Fig. 8). No branch was pruned. The "
     "skeleton has two junctions about 24 px apart, one where the left stroke "
     "meets the crossbar and one where the crossbar crosses the main "
     "stroke, but the graph keeps a single intersection of degree 4 with "
     "four endpoints and no corner. Concept 4_2 needs a corner, so it is "
     "rejected with «concept has corner points but image does not». "
     "Concept 4_1 has an intersection, two corners and no endpoint besides "
     "S. Endpoint reduction strips the image branches until no endpoint "
     "remains and takes the intersection with them, so 4_1 is rejected "
     "with «concept has intersection points but image does not». Only "
     "1_1, 7_1 and 1_3 reach comparison. 1_3 leads on raw similarity "
     "(0.6489 against 0.5973 and 0.5815), and the prior moves 1_1 to the "
     "top with an adjusted score of 0.9515."),
   ("p", "This image is typical of its pair. All 40 gate errors 4→1 carry "
     "the same two messages, 39 of their graphs have no corner point, 28 "
     "have exactly four endpoints and one intersection, and 11 have five "
     "endpoints and one intersection; 1_1 wins 37 of them and 1_3 the "
     "other 3. The same pair of messages rejects class 4 in 35 of the 36 "
     "gate errors 4→7. Here the class is lost before scoring, and the "
     "prior only picks among wrong concepts."),
   ("fig", "anatomy_ais/case6_pipeline.png", 8,
    "mnist_test_4_00755, panels and markers as in Fig. 5: the two junctions "
    "of the skeleton become one intersection of degree 4, and the graph has "
    "no corner point", "full"),
   ("p", "The similarity errors 4→7 show the opposite case: the image has "
     "the right topology and still loses. Image mnist_test_4_00487 has "
     "three endpoints, one corner and one intersection, the point "
     "composition of concept 4_2, as do 21 of the 44 similarity errors "
     "4→7. Under 4_2 preprocessing only turns one endpoint into S. GED "
     "substitutes all nine nodes without a deletion or a label mismatch, "
     "but eight features fall outside their ranges on four nodes, and "
     "these four substitutions cost 1.4948 to 3.0611 each. GED is 10.6695 "
     "and similarity 0.6144 (Fig. 9). Under 7_1 preprocessing removes the "
     "branch above the intersection, the intersection becomes a corner, "
     "and GED deletes two more nodes and three edges at 0.25 each. GED is "
     "4.4255 with two out-of-range features, and similarity 0.7460. The "
     "prior gives 4_2 0.0917 more than 7_1, less than the raw gap of "
     "0.1316, and 7_1 wins with 1.0630 against 1.0231."),
   ("p", "In every one of the 44 similarity errors 4→7 the winner is 7_1 "
     "and the best class-4 concept is 4_2, with median similarities of "
     "0.7428 and 0.6025. Under 7_1 none of the 44 pays a label mismatch, "
     "and all 21 images with the composition of 4_2 are matched by five "
     "substitutions and two deletions. Preprocessing for a smaller concept "
     "cuts the image down to that concept, and a deletion costs less than "
     "a node whose features miss the ranges. A smaller concept that "
     "discards what does not fit then beats the correct concept that has "
     "to match every node."),
   ("fig", "anatomy_ais/case8_matching.png", 9,
    "mnist_test_4_00487: node matching under 4_2 (top) and 7_1 (bottom), image "
    "graph on the left and concept on the right, markers as in Fig. 5. A line "
    "joins substituted nodes: darker means a higher cost, thick means a "
    "feature out of range. Star: start point; hollow circle: corner demoted "
    "to a plain point; cross: deleted node; dashed: deleted edge; pale: "
    "removed by preprocessing", "column"),
   ("h2", "The dominant pair 2→7"),
   ("p", "The pair 2→7 is the largest and the one we have studied longest "
     "[@lapin2026dessert]. In the 91.13% configuration it held 111 "
     "errors. In 110 of them the lower loop of the 2 has no hole already "
     "in the binary mask, because the loop is drawn open or its small "
     "interior is filled by a thick stroke; in the remaining case the hole "
     "is lost at vectorization. The 2 then has the open-stroke topology of "
     "concept 7_1 and loses on similarity, which matches the 90 similarity "
     "cases of 93 in the repeated run."),
  ],
 },
 {
  "title": "Results of the Current System Version",
  "blocks": [
   ("p", "The current version of the classifier drops the two constants "
     "that had been fitted to the test set: the prior weight λ = 0.10 in "
     "(2) and a width gate of 0.33 that compares an envelope with the "
     "spread of the same feature over the concepts of all classes. Every "
     "later change was accepted on a development split of 1,996 images "
     "from the MNIST training set, and the test set was run once per "
     "frozen configuration. Removing the two constants costs 4.51 points "
     "on the development split (Table 4). The changes that follow keep "
     "the rules of the method: a concept learns from positive examples "
     "only, and no score uses statistics of other classes. The originals, "
     "augmentations and 13 subclasses stay the same; each subclass now "
     "gives one concept per binarization threshold, 39 in all."),
   ("tbl", 4,
    "Steps of the current version, accuracy on the development split "
    "(1,996 images)",
    ["Step", "Accuracy, %"],
    [["Original model", "80.91"],
     ["λ = 0, no width gate", "76.40"],
     ["28 node features instead of 13", "78.01"],
     ["Cost grows over 4 half-widths outside an envelope", "80.96"],
     ["Thresholds 110, 150, 190; best similarity per concept", "83.52"],
     ["Complexity term with λ = 0.05", "83.82"],
     ["One detector for training and recognition", "84.72"],
     ["Thin skeleton as a fourth filter; concepts from each threshold",
      "84.97"],
     ["Orientation layer with bands from the concept's own images",
      "86.27"]],
    "column", [0.78, 0.22], [1]),
   ("p", "The last step adds a parametric layer. A descriptor sums the "
     "stroke centre line in four orientation bins over 2×2 and 3×3 grids. "
     "For each dimension a concept keeps the shortest interval that holds "
     "80% of the values of its own training images. A dimension scores 1 "
     "inside the interval and falls linearly to 0 one interval width "
     "outside; half of the mean score is added to the similarity of each "
     "concept that passes preprocessing."),
   ("p", "On the 8,708 complete-contour test images this version answers "
     "92.90% correctly, with the 15 images that no concept accepts counted "
     "as errors. The original model rerun on the same images gives "
     "90.89% (91.13% when the 22 images without a graph are left out). "
     "The paired difference is +2.01 points (95% CI +1.36 to +2.66; "
     "McNemar p = 2·10⁻⁹). On all 10,000 test images accuracy rises from "
     "82.24% to 85.44%, and on the 1,290 incomplete-contour images from "
     "23.95% to 35.12%."),
   ("p", "The largest confusion pairs move where the census points. "
     "Against the 91.13% run, class 4 gains most: 4→7 falls from 62 "
     "errors to 4 and 4→1 from 52 to 22. The pair 5→3, which the prior "
     "settles in 55 of its 56 cases in the census, falls from 43 to 10. "
     "2→7 falls from 111 to 66 and 2→6 from 57 to 21. One pair grows: "
     "1→7 rises from 26 to 151. The run stores the final ranking only, "
     "so its errors cannot yet be split into gate, similarity and prior, "
     "and which step moved each pair has not been traced."),
  ],
 },
 {
  "title": "Discussion",
  "blocks": [
   ("p", "**Where corrections belong.** The three mechanisms point to "
     "different parts of the system. Gate errors (38.0%) are decided "
     "before any cost is computed. The traced cases show front-end steps "
     "removing what the true concept requires: pruning cuts the end of a "
     "2, and graph construction merges the two junctions of an open 4 "
     "into one, which leaves no corner for 4_2. Changing cost weights "
     "cannot repair these answers, because the true concept never receives "
     "a cost. Similarity errors (46.7%) include cases such as the zero "
     "with a spur, where the image graph genuinely has the topology of "
     "the predicted class; there the remedy is in graph construction, not "
     "in scoring. In the 4→7 errors the topology is right, and the loss "
     "comes from preprocessing that cuts the image down to a smaller "
     "concept at deletion costs below the cost of missed ranges; that part "
     "is a scoring question. Prior errors (15.2%) are the only group that a change of "
     "the ranking rule could reverse directly, and the same rule rescues "
     "other answers, so any change has to be measured on both sides."),
   ("p", "**Stability and the theory.** The convergence markers agree with "
     "the claim that a concept reaches a stable structure in a bounded "
     "number of steps [@lapin2026itssi]: no concept changed its node or "
     "edge count after file 37, and most settled within a few files. The "
     "steps are not training epochs: each file passes through reduction "
     "once, and further files only add evidence. The envelopes keep "
     "widening slowly after the structure is fixed, so the bounded part of "
     "convergence is the structure, while the envelopes keep absorbing "
     "variation. Independence of the formed concept from the order of "
     "samples follows from the commutativity of accumulation in the theory "
     "[@lapin2026itssi]; a controlled experiment on it is left for a "
     "separate study, after the pairing step of the implementation is made "
     "to match each sample independently of the samples merged before it."),
   ("p", "**Limitations.** The stability study and the error study use two "
     "states of the system: the concepts of the 91.13% configuration and "
     "concepts retrained on the same files, which reach 90.05%. The error "
     "counts therefore describe the retrained concepts. The structural "
     "marker compares counts, not attributed graphs. The sample-count "
     "study covers three concepts and was not followed by classification "
     "runs. The traces explain individual images; the census gives the "
     "size of each mechanism but not the front-end cause of every case in "
     "it. Further traced cases are published in the project repository "
     "[@repo]."),
  ],
 },
 {
  "title": "Conclusions",
  "blocks": [
   ("p", "1. Concept formation settles its structure within 1 to 37 "
     "training files per concept, well before each cohort is exhausted. "
     "The parameter envelopes settle on a separate schedule, earlier or "
     "later than the structure, so a stopping rule for formation has to "
     "watch both."),
   ("p", "2. More training samples give a smaller concept graph with wider "
     "envelopes. The 13 concepts keep 106 of the 9,738 nodes of their "
     "training graphs, a compression of 91.9 times in nodes and 50.6 "
     "times in stored values."),
   ("p", "3. All 820 wrong-class answers of the test run split into three "
     "mechanisms: the true concept never reaches comparison (312), it "
     "loses on similarity (383), or it leads on similarity and loses "
     "through the complexity prior (125). Traced cases tie each mechanism "
     "to a step: skeleton pruning, a spur that changes the topology, a "
     "junction lost in graph construction, deletions cheaper than missed "
     "feature ranges, and a prior term larger than the similarity gap."),
   ("p", "4. Without the two constants fitted to the test set, and with "
     "changes chosen on a development split, the classifier answers "
     "92.90% of 8,708 complete-contour test images against 90.89% for the "
     "original model. The class-4 pairs and the prior pair 5→3 shrink "
     "most, while 1→7 grows from 26 to 151 errors."),
   ("p", "**Prospects.** The census sets the order of work. The class-4 gate "
     "errors and the pruning rule come first, since they remove the true "
     "concept from competition. The ranking prior should be revised only "
     "with its rescues counted. The sample-count study needs classification "
     "runs per condition, and order independence needs its controlled "
     "experiment once the pairing step is corrected."),
  ],
 },
]

# --------------------------------------------------------------------------
# References — AIS Harvard. Keys are resolved in order of first citation.
# --------------------------------------------------------------------------

REFERENCE_DB = {
 "rudin2019":
 'Rudin, C. (2019), "Stop explaining black box machine learning models for '
 'high stakes decisions and use interpretable models instead", Nature Machine '
 'Intelligence, vol. 1, no. 5, pp. 206–215, doi: '
 'https://doi.org/10.1038/s42256-019-0048-x',

 "rudin2022":
 'Rudin, C., Chen, C., Chen, Z., Huang, H., Semenova, L. and Zhong, C. '
 '(2022), "Interpretable machine learning: Fundamental principles and 10 '
 'grand challenges", Statistics Surveys, vol. 16, pp. 1–85, doi: '
 'https://doi.org/10.1214/21-SS133',

 "lapin2025asu":
 'Lapin, M. and Bokhan, K. (2025), "Few-shot learning of a graph-based neural '
 'network model without backpropagation", Management Information System and '
 'Devices, no. 187, pp. 103–122, doi: '
 'https://doi.org/10.30837/0135-1710.2025.187.103',

 "parzhyn2025ais":
 'Parzhyn, Y., Lapin, M. and Bokhan, K. (2025), "A new approach to building '
 'energy models of neural networks", Advanced Information Systems, vol. 9, '
 'no. 4, pp. 100–119, doi: https://doi.org/10.20998/2522-9052.2025.4.13',

 "lapin2026itssi":
 'Lapin, M., Parzhyn, Y., Bokhan, K., Perevoznyk, K. and Aleksandrova, T. '
 '(2026), "Invariant structural learning: concept formation as hypergraph '
 'attractor dynamics", Innovative Technologies and Scientific Solutions for '
 'Industries, no. 2(36), pp. 70–94, doi: '
 'https://doi.org/10.30837/2522-9818.2026.2.070',

 "lecun1998":
 'LeCun, Y., Bottou, L., Bengio, Y. and Haffner, P. (1998), "Gradient-based '
 'learning applied to document recognition", Proceedings of the IEEE, vol. 86, '
 'no. 11, pp. 2278–2324, doi: https://doi.org/10.1109/5.726791',

 "lapin2026dessert":
 'Lapin, M., Bokhan, K., Parzhyn, Y., Perevoznyk, K. and Aleksandrova, T. '
 '(2026), "Traceable decisions without backpropagation: graph concept '
 'attractors for handwritten digit recognition", Proceedings of the IEEE '
 '7th International Conference on Dependable Systems, Services and '
 'Technologies (DESSERT 2026), Corfu, Greece, in press',

 "fritzke1995":
 'Fritzke, B. (1995), "A growing neural gas network learns topologies", '
 'Advances in Neural Information Processing Systems 7, MIT Press, Cambridge, '
 'MA, pp. 625–632, available at: '
 'https://proceedings.neurips.cc/paper/1994/hash/'
 'd56b9fc4b0f1be8871f5e1c40c0067e7-Abstract.html',

 "repo":
 'NaturalAGI-Lab (2026), "NaturalAGI: structural pattern recognition '
 'without backpropagation", GitHub repository, available at: '
 'https://github.com/NaturalAGI-Lab/NaturalAGI',

 "bougleux2017":
 'Bougleux, S., Brun, L., Carletti, V., Foggia, P., Gaüzère, B. and Vento, '
 'M. (2017), "Graph edit distance as a quadratic assignment problem", Pattern '
 'Recognition Letters, vol. 87, pp. 38–46, doi: '
 'https://doi.org/10.1016/j.patrec.2016.10.001',

 "blumenthal2019":
 'Blumenthal, D. B., Boria, N., Gamper, J., Bougleux, S. and Brun, L. (2019), '
 '"Comparing heuristics for graph edit distance computation", The VLDB '
 'Journal, vol. 29, no. 1, pp. 419–458, doi: '
 'https://doi.org/10.1007/s00778-019-00544-1',

 "riba2021":
 'Riba, P., Fischer, A., Lladós, J. and Fornés, A. (2021), "Learning graph '
 'edit distance by graph neural networks", Pattern Recognition, vol. 120, '
 'article 108132, doi: https://doi.org/10.1016/j.patcog.2021.108132',

 "barredo2020":
 'Barredo Arrieta, A., Díaz-Rodríguez, N., Del Ser, J., Bennetot, A., Tabik, '
 'S., Barbado, A. et al. (2020), "Explainable Artificial Intelligence (XAI): '
 'Concepts, taxonomies, opportunities and challenges toward responsible AI", '
 'Information Fusion, vol. 58, pp. 82–115, doi: '
 'https://doi.org/10.1016/j.inffus.2019.12.012',

 "ji2020":
 'Ji, Z., Chai, X., Yu, Y., Pang, Y. and Zhang, Z. (2020), "Improved '
 'prototypical networks for few-shot learning", Pattern Recognition Letters, '
 'vol. 140, pp. 81–87, doi: https://doi.org/10.1016/j.patrec.2020.07.015',

 "oakden2020":
 'Oakden-Rayner, L., Dunnmon, J., Carneiro, G. and Ré, C. (2020), "Hidden '
 'stratification causes clinically meaningful failures in machine learning '
 'for medical imaging", Proceedings of the ACM Conference on Health, '
 'Inference, and Learning, pp. 151–159, doi: '
 'https://doi.org/10.1145/3368555.3384468',

 "geirhos2020":
 'Geirhos, R., Jacobsen, J.-H., Michaelis, C., Zemel, R., Brendel, W., '
 'Bethge, M. and Wichmann, F. A. (2020), "Shortcut learning in deep neural '
 'networks", Nature Machine Intelligence, vol. 2, no. 11, pp. 665–673, doi: '
 'https://doi.org/10.1038/s42256-020-00257-z',

 "gan2023":
 'Gan, J., Chen, Y., Hu, B., Leng, J., Wang, W. and Gao, X. (2023), '
 '"Characters as graphs: Interpretable handwritten Chinese character '
 'recognition via Pyramid Graph Transformer", Pattern Recognition, vol. 137, '
 'article 109317, doi: https://doi.org/10.1016/j.patcog.2023.109317',
}

_CITE = re.compile(r"\[(@[\w]+(?:,\s*@[\w]+)*)\]")


def _number_citations() -> list:
    order: list = []

    def resolve(match: re.Match) -> str:
        numbers = []
        for key in re.findall(r"@(\w+)", match.group(1)):
            if key not in order:
                order.append(key)
            numbers.append(str(order.index(key) + 1))
        return "[" + ", ".join(numbers) + "]"

    for section in SECTIONS:
        blocks = section["blocks"]
        for index, block in enumerate(blocks):
            if block[0] in ("p", "h2"):
                blocks[index] = (block[0], _CITE.sub(resolve, block[1]))
    return [REFERENCE_DB[key] for key in order]


REFERENCES = _number_citations()

# --------------------------------------------------------------------------
# Back matter
# --------------------------------------------------------------------------

RECEIVED = "Received (Надійшла)"
ACCEPTED = "Accepted for publication (Прийнято до друку)"

KHPI_UA = ("Національний технічний університет \"Харківський політехнічний "
           "інститут\", Харків, Україна")
KHPI_EN = ("National Technical University \"Kharkiv Polytechnic Institute\", "
           "Kharkiv, Ukraine")
DEPT_UA = "кафедри системного аналізу та інформаційно-аналітичних технологій"
DEPT_EN = ("the Department of System Analysis and Information and Analytical "
           "Technologies")

AUTHOR_BLOCK = [
    {
     "ua_name": "Лапін Микита Олексійович",
     "ua_body": f"аспірант {DEPT_UA}, {KHPI_UA};",
     "en_name": "Mykyta Lapin",
     "en_body": f"Postgraduate Student of {DEPT_EN}, {KHPI_EN}.",
     "email": "Mykyta.Lapin@cit.khpi.edu.ua",
     "orcid": "https://orcid.org/0009-0003-6307-1172",
     "scopus": "https://www.scopus.com/authid/detail.uri?authorId=60171161300",
    },
    {
     "ua_name": "Бохан Костянтин Олександрович",
     "ua_body": f"кандидат технічних наук, доцент {DEPT_UA}, {KHPI_UA};",
     "en_name": "Kostiantyn Bokhan",
     "en_body": f"Candidate of Technical Sciences, Associate Professor of "
                f"{DEPT_EN}, {KHPI_EN}.",
     "email": "kostiantyn.bokhan@khpi.edu.ua",
     "orcid": "https://orcid.org/0000-0003-3375-2527",
     "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57191592568",
    },
    {
     "ua_name": "Паржин Юрій Володимирович",
     "ua_body": "доктор технічних наук, постдокторант Школи комп'ютерних та кібернаук, "
                "Університет Огасти, Огаста, США;",
     "en_name": "Yurii Parzhyn",
     "en_body": "Doctor of Technical Sciences, Postdoctoral Fellow, School of Computer and Cyber "
                "Sciences, Augusta University, Augusta, USA.",
     "email": "yparzhyn@augusta.edu",
     "orcid": "https://orcid.org/0000-0001-5727-1918",
     "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57224412390",
    },
    {
     "ua_name": "Перевозник Кирило Максимович",
     "ua_body": f"аспірант {DEPT_UA}, {KHPI_UA};",
     "en_name": "Kyrylo Perevoznyk",
     "en_body": f"Postgraduate Student of {DEPT_EN}, {KHPI_EN}.",
     "email": "kyrylo.perevoznyk@cs.khpi.edu.ua",
     "orcid": "https://orcid.org/0009-0009-2327-1501",
     "scopus": "https://www.scopus.com/authid/detail.uri?authorId=59564678000",
    },
    {
     "ua_name": "Александрова Тетяна Євгенівна",
     "ua_body": f"доктор технічних наук, професор, завідувач {DEPT_UA}, "
                f"{KHPI_UA};",
     "en_name": "Tetiana Aleksandrova",
     "en_body": f"Doctor of Technical Sciences, Professor, Head of {DEPT_EN}, "
                f"{KHPI_EN}.",
     "email": "Tetiana.Aleksandrova@khpi.edu.ua",
     "orcid": "https://orcid.org/0000-0001-9596-0669",
     "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57189376480",
    },
]

UA_TITLE = ("Стабільність формування та механізми помилок графового "
            "класифікатора концептів, навченого без зворотного поширення "
            "помилки")

UA_AUTHORS = ("М. О. Лапін, К. О. Бохан, Ю. В. Паржин, К. М. Перевозник, "
              "Т. Є. Александрова")

UA_ABSTRACT = [
    ("Актуальність.", "Класифікатор, що зберігає кожен клас як явний граф, "
     "можна перевірити на кожному кроці, але цінність такої перевірки "
     "залежить від двох питань: коли збережений клас перестає змінюватися з "
     "надходженням навчальних прикладів і чи можна кожну хибну відповідь "
     "простежити до етапу, який її спричинив."),
    ("Об’єкт дослідження", "– класифікатор рукописних цифр, навчений без "
     "зворотного поширення помилки. Він перетворює зображення на "
     "атрибутований скелетний граф, зводить графи одного підкласу до "
     "одного графа-концепту й ухвалює рішення за подібністю на основі "
     "редакційної відстані між графами з поправкою на складність "
     "концепту."),
    ("Предмет дослідження", "– стабілізація графів-концептів під час "
     "формування та механізми, що породжують хибні класифікації."),
    ("Мета статті", "– виміряти, як рано концепти перестають змінюватися і "
     "що з ними роблять додаткові приклади, та віднести кожну відповідь із "
     "хибним класом до кроку рішення, який її спричинив."),
    ("Результати дослідження.", "Для тринадцяти концептів кількості вузлів "
     "і ребер перестають змінюватися після 1–37 навчальних файлів, тоді як "
     "координатні оболонки стабілізуються за окремим графіком; більше "
     "прикладів дає менший граф із ширшими оболонками. Концепти зберігають "
     "106 вузлів із 9 738 у 869 навчальних графах. Із 820 відповідей із "
     "хибним класом на 8 683 класифікованих тестових зображеннях MNIST із "
     "повними контурами 312 виникають тому, що жоден концепт істинного "
     "класу не доходить до порівняння, 383 – тому, що переможець має вищу "
     "сиру подібність, і 125 – тому, що поправка на складність перевертає "
     "перевагу концепту істинного класу. Простежені випадки показують, де "
     "починається кожен механізм: обрізання скелета, що прибирає кінець "
     "штриха, відросток, що надає нулю топологію шістки, вузол розгалуження "
     "відкритої четвірки, втрачений під час побудови графа, вилучення "
     "вузлів, дешевші за вихід ознак за межі діапазонів, і доданок поправки, "
     "більший за різницю подібностей. Версія без двох констант, "
     "підібраних на тестовій вибірці, досягає 92,90 % на 8 708 зображеннях "
     "із повними контурами проти 90,89 % у вихідної моделі."),
    ("Висновки.", "Формування стабілізується за десятки прикладів, і "
     "правило зупинки має окремо стежити за структурою та оболонками. "
     "Більшість помилок виникає до обчислення подібності – під час побудови "
     "графа і структурної перевірки, тож наступні виправлення належать "
     "туди, а не до ваг вартостей."),
]

UA_KEYWORDS = ("структурне розпізнавання образів; редакційна відстань між "
               "графами; формування концептів; пояснюваний штучний інтелект; "
               "аналіз помилок; розпізнавання рукописних цифр; навчання без "
               "зворотного поширення помилки")
