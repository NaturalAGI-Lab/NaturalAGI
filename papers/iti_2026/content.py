"""Text of the IT&I(s)-2026 regular-presentation paper.

Numbers re-verified 2026-09-20 against:
  src/training/training_results/formation_probes/{convergence,sample_count,retry_2026_08_4_1}
  src/training/training_results/run_20260630_235356/metrics.csv
"""

TITLE = "CONCEPT STABILITY IN A GRAPH CLASSIFIER THAT LEARNS WITHOUT BACKPROPAGATION"

AUTHORS = [
    ("Mykyta Lapin", "postgraduate student"),
    ("Kostiantyn Bokhan", "associate professor"),
    ("Yurii Parzhyn", "postdoctoral fellow"),
    ("Kyrylo Perevoznyk", "postgraduate student"),
    ("Tetiana Aleksandrova", "professor, head of the department"),
]

KHPI = ("Department of Systems Analysis and Information-Analytical Technologies, "
        "National Technical University “Kharkiv Polytechnic Institute”")

AUTHOR_AFFILIATION = {
    "Kostiantyn Bokhan": KHPI,
    "Yurii Parzhyn": "School of Computer and Cyber Sciences, Augusta University, USA",
    "Tetiana Aleksandrova": KHPI,
}

BODY = [
    ("Introduction.",
     "A classifier that learns without backpropagation and keeps each class as an explicit graph can be "
     "read at every step. Interpretable modelling asks for that access to the model itself [1]. Readability "
     "still says nothing about when the stored class stops changing as training samples accumulate. This "
     "paper reports offline probes that measure two properties of concept formation in NaturalAGI [2, 3]: "
     "how early the learned concept stops growing, and how it responds to the number of training samples. "
     "The audited system turns a handwritten digit into an attributed skeleton graph, reduces the graphs of one subclass into a single concept graph, and "
     "classifies by inexact graph matching [4]. On its selected MNIST [5] cohort it decided 7,915 of 8,685 "
     "completed records correctly: 91.13% of the completed records and 90.90% of all 8,707 admitted ones."),

    ("Probe design.",
     "The probes replay formation on cached sample graphs and never write to the deployed concept store, so "
     "the numbers below describe learning, not recognition. The sample-count "
     "probe forms 2_2, 7_1 and 4_1 from 2, 5, 10 and 20 cached files, with three draws per condition. The "
     "full-cohort probe records two markers for each of thirteen concepts: the earliest step after which the "
     "node and edge counts never change again, and the first step at which the mean width of the normalized "
     "coordinate envelopes changes by less than 0.02 over five consecutive steps. Six files that mixed open "
     "and closed digit-4 shapes were removed from the 4_1 cohort, which formation could not reconcile; its "
     "retained cohort holds 36 files."),

    ("Stabilization and sample count.",
     "Across the thirteen concepts the size marker falls between 1 and 37 files. The envelope marker does "
     "not track it. For 8_1 the widths flatten at step 5 while "
     "the graph keeps changing until step 37; for 2_1 and 5_1 the envelope markers at steps 12 and 11 also "
     "precede the last size change at steps 23 and 28. A plateau in width is therefore unsafe as a stopping "
     "rule. Adding examples moves the two properties in opposite directions: 2_2 falls from 16 nodes at two "
     "files to 12 at ten and twenty, while the mean envelope width of 7_1 grows from 0.33 to 0.48, 0.68 and "
     "0.80 over the same counts. The cleaned 4_1 cohort holds eight nodes and eight edges from its second "
     "file onwards. More examples buy a smaller graph and looser bands; no downstream classification was run "
     "with these probe concepts, so neither trade is shown to be better for recognition."),

    ("Conclusion.",
     "Concept formation in this system settles its graph size within 1 to 37 files per concept, and its "
     "envelope widths settle on a separate schedule. A stopping rule for formation therefore has to watch "
     "both markers. More examples give a smaller graph with wider bands; a classification run with the "
     "probe concepts is the next test of which trade helps recognition."),
]

REFERENCES = [
    "Rudin, C., Chen, C., Chen, Z., Huang, H., Semenova, L., Zhong, C. (2022). Interpretable machine "
    "learning: Fundamental principles and 10 grand challenges. Statistics Surveys, 16, 1–85. "
    "https://doi.org/10.1214/21-SS133",

    "Lapin, M., Parzhyn, Y., Bokhan, K., Perevoznyk, K., Aleksandrova, T. (2026). Invariant structural "
    "learning: Concept formation as hypergraph attractor dynamics. Innovative Technologies and Scientific "
    "Solutions for Industries, 2(36), 70–94. https://doi.org/10.30837/2522-9818.2026.2.070",

    "Parzhyn, Y., Lapin, M., Bokhan, K. (2025). A new approach to building energy models of neural networks. "
    "Advanced Information Systems, 9(4), 100–119. https://doi.org/10.20998/2522-9052.2025.4.13",

    "Bunke, H., Allermann, G. (1983). Inexact graph matching for structural pattern recognition. Pattern "
    "Recognition Letters, 1(4), 245–253. https://doi.org/10.1016/0167-8655(83)90033-8",

    "LeCun, Y., Bottou, L., Bengio, Y., Haffner, P. (1998). Gradient-based learning applied to document "
    "recognition. Proceedings of the IEEE, 86(11), 2278–2324. https://doi.org/10.1109/5.726791",
]
