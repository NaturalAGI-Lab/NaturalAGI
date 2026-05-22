"""Apply ITSSI 2026 editor revisions to Стаття_Паржин_2026.docx.

Mutates only `<w:t>` text nodes inside `<w:r>` runs that DO NOT contain
`<w:object>` (MathType OLE formulas). Drawing/oleObject blocks are
preserved untouched.

Operations:
  1) Replace Harvard parenthetical and narrative citations with `[N]`
     (Vancouver, ordered by first appearance).
  2) Re-order References paragraphs into the same Vancouver order and
     prefix each with `[N] ` instead of an alphabetical Harvard entry.
  3) Insert two new References (Chukhran et al., 2025 + Parzhyn-Lapin-Bokhan
     energy models, 2025) at the right Vancouver positions.
  4) Add citation tokens for the two new entries in the body text.
  5) Rebuild the "Information about the authors" block to follow ITSSI
     order: degree → title → org → position.

Run:
    natural-agi/bin/python papers/itssi_paper_2026/revise_docx.py
"""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

from lxml import etree

ROOT = Path(__file__).resolve().parent
SRC_DOCX = ROOT / "Стаття_Паржин_2026.docx"
DST_DOCX = ROOT / "Стаття_Паржин_2026_revised.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


# ---------------------------------------------------------------------------
# Vancouver mapping (ordered by first appearance in body)
# ---------------------------------------------------------------------------

# Each entry: (canonical_key, list_of_inline_forms_seen_in_text, full_reference_entry)
#   canonical_key is the alphabetic-Harvard surface used as a regex anchor.
#   list_of_inline_forms is the surface forms we expect to see in body text.
#   full_reference_entry is the latinised Harvard BSI body text used for the
#   References section, prefixed with `N. ` later.

VANCOUVER: List[Tuple[str, List[str], str]] = [
    (
        "Parzhyn, 2025",
        ["(Parzhyn, 2025)"],
        'Parzhyn, Y. (2025), "Architecture of information", arXiv preprint '
        "arXiv:2503.21794. DOI: https://doi.org/10.48550/arXiv.2503.21794.",
    ),
    (
        "LeCun et al., 1998",
        ["(LeCun et al., 1998)"],
        'LeCun, Y., Bottou, L., Bengio, Y., Haffner, P. (1998), "Gradient-based '
        'learning applied to document recognition", Proceedings of the IEEE, '
        "Vol. 86, No. 11, pp. 2278-2324. DOI: https://doi.org/10.1109/5.726791.",
    ),
    (
        "Snell et al., 2017",
        ["(Snell et al., 2017)", "Snell et al. (2017)"],
        'Snell, J., Swersky, K., Zemel, R. (2017), "Prototypical networks for '
        'few-shot learning", Advances in Neural Information Processing Systems '
        "30 (NeurIPS 2017), pp. 4077-4087. DOI: "
        "https://doi.org/10.48550/arXiv.1703.05175.",
    ),
    (
        "Vinyals et al., 2016",
        ["(Vinyals et al., 2016)"],
        'Vinyals, O., Blundell, C., Lillicrap, T., Kavukcuoglu, K., Wierstra, D. '
        '(2016), "Matching networks for one shot learning", Advances in Neural '
        "Information Processing Systems 29 (NeurIPS 2016), pp. 3630-3638. DOI: "
        "https://doi.org/10.48550/arXiv.1606.04080.",
    ),
    (
        "Finn et al., 2017",
        ["(Finn et al., 2017)"],
        'Finn, C., Abbeel, P., Levine, S. (2017), "Model-agnostic meta-learning '
        'for fast adaptation of deep networks", Proceedings of the 34th '
        "International Conference on Machine Learning (ICML 2017), "
        "pp. 1126-1135. DOI: https://doi.org/10.48550/arXiv.1703.03400.",
    ),
    (
        "Minh et al., 2022",
        ["Minh et al. (2022)"],
        'Minh, D., Wang, H. X., Li, Y. F., Nguyen, T. N. (2022), "Explainable '
        'artificial intelligence: a comprehensive review", Artificial Intelligence '
        "Review, Vol. 55, No. 5, pp. 3503-3568. DOI: "
        "https://doi.org/10.1007/s10462-021-10088-y.",
    ),
    (
        "Hooshyar and Yang, 2024",
        ["Hooshyar and Yang (2024)"],
        'Hooshyar, D., Yang, Y. (2024), "Problems with SHAP and LIME in '
        "interpretable AI for education: a comparative study of post-hoc "
        'explanations and neural-symbolic rule extraction", IEEE Access, Vol. 12, '
        "pp. 137472-137490. DOI: https://doi.org/10.1109/ACCESS.2024.3463948.",
    ),
    (
        "Rajabi and Etminani, 2024",
        ["Rajabi and Etminani (2024)"],
        'Rajabi, E., Etminani, K. (2024), "Knowledge-graph-based explainable AI: '
        'a systematic review", Journal of Information Science, Vol. 50, No. 4, '
        "pp. 1019-1029. DOI: https://doi.org/10.1177/01655515221112844.",
    ),
    (
        "Nawaz et al., 2025",
        ["Nawaz et al. (2025)"],
        'Nawaz, U., Anees-ur-Rahaman, M., Saeed, Z. (2025), "A review of '
        "neuro-symbolic AI integrating reasoning and learning for advanced "
        'cognitive systems", Intelligent Systems with Applications, Vol. 26, '
        "pp. 200541. DOI: https://doi.org/10.1016/j.iswa.2025.200541.",
    ),
    (
        "Ribeiro et al., 2016",
        ["(Ribeiro et al., 2016)"],
        'Ribeiro, M. T., Singh, S., Guestrin, C. (2016), ""Why should I trust '
        'you?": Explaining the predictions of any classifier", Proceedings of the '
        "22nd ACM SIGKDD International Conference on Knowledge Discovery and "
        "Data Mining (KDD 2016), pp. 1135-1144. DOI: "
        "https://doi.org/10.1145/2939672.2939778.",
    ),
    (
        "Lundberg and Lee, 2017",
        ["(Lundberg and Lee, 2017)"],
        'Lundberg, S. M., Lee, S.-I. (2017), "A unified approach to interpreting '
        'model predictions", Advances in Neural Information Processing Systems '
        "30 (NeurIPS 2017), pp. 4765-4774. DOI: "
        "https://doi.org/10.48550/arXiv.1705.07874.",
    ),
    (
        "Slack et al., 2020",
        ["Slack et al. (2020)"],
        'Slack, D., Hilgard, S., Jia, E., Singh, S., Lakkaraju, H. (2020), '
        '"Fooling LIME and SHAP: adversarial attacks on post hoc explanation '
        'methods", Proceedings of the AAAI/ACM Conference on AI, Ethics, and '
        "Society (AIES '20), pp. 180-186. DOI: "
        "https://doi.org/10.1145/3375627.3375830.",
    ),
    (
        "Ding et al., 2022",
        ["(Ding et al., 2022)"],
        'Ding, K., Wang, J., Li, J., Shu, K., Liu, C., Liu, H. (2022), "Graph '
        "prototypical networks for few-shot learning on attributed networks\", "
        "Proceedings of the 31st ACM International Conference on Information "
        "and Knowledge Management, pp. 2023-2032. DOI: "
        "https://doi.org/10.1145/3511808.3557434.",
    ),
    (
        "Lapin and Bokhan, 2025",
        ["(Lapin and Bokhan, 2025)"],
        'Lapin, M., Bokhan, K. (2025), "Few-shot learning of graph neural network '
        'models without backpropagation", Automated Control Systems and '
        "Instruments, No. 187, pp. 103-122. DOI: "
        "https://doi.org/10.30837/0135-1710.2025.187.103. [in Ukrainian, "
        "original title: \"Навчання за кількома прикладами (few-shot) графової "
        "моделі нейронної мережі без використання зворотного поширення помилки\"]",
    ),
    (
        "Sanfeliu and Fu, 1983",
        ["Sanfeliu and Fu (1983)"],
        'Sanfeliu, A., Fu, K.-S. (1983), "A distance measure between attributed '
        'relational graphs for pattern recognition", IEEE Transactions on Systems, '
        "Man, and Cybernetics, Vol. SMC-13, No. 3, pp. 353-362. DOI: "
        "https://doi.org/10.1109/TSMC.1983.6313167.",
    ),
    (
        "Conte et al., 2004",
        ["Conte et al. (2004)", "(Conte et al., 2004)"],
        'Conte, D., Foggia, P., Sansone, C., Vento, M. (2004), "Thirty years of '
        'graph matching in pattern recognition", International Journal of Pattern '
        "Recognition and Artificial Intelligence, Vol. 18, No. 3, pp. 265-298. "
        "DOI: https://doi.org/10.1142/S0218001404003228.",
    ),
    (
        "Riesen and Bunke, 2009",
        ["Riesen and Bunke (2009)", "(Riesen and Bunke, 2009)"],
        'Riesen, K., Bunke, H. (2009), "Approximate graph edit distance '
        "computation by means of bipartite graph matching\", Image and Vision "
        "Computing, Vol. 27, No. 7, pp. 950-959. DOI: "
        "https://doi.org/10.1016/j.imavis.2008.04.004.",
    ),
    (
        "Piao et al., 2023",
        ["Piao et al. (2023)", "(Piao et al., 2023)"],
        'Piao, C., Xu, T., Sun, X., Rong, Y., Zhao, K., Cheng, H. (2023), '
        '"Computing graph edit distance via neural graph matching", Proceedings '
        "of the VLDB Endowment, Vol. 16, No. 8, pp. 1817-1829. DOI: "
        "https://doi.org/10.14778/3594512.3594514.",
    ),
    (
        "Moscatelli et al., 2024",
        ["Moscatelli et al. (2024)"],
        'Moscatelli, A., Piquenot, J., Berar, M., Heroux, P., Adam, S. (2024), '
        '"Graph node matching for edit distance", Pattern Recognition Letters, '
        "Vol. 184, pp. 14-20. DOI: https://doi.org/10.1016/j.patrec.2024.05.020.",
    ),
    (
        "Xie et al., 2024",
        ["Xie et al. (2024)"],
        'Xie, Y., Liang, Y., Wen, C., Qin, A. K., Gong, M. (2024), "Federated '
        "collaborative graph neural networks for few-shot graph classification\", "
        "Machine Intelligence Research, Vol. 21, No. 6, pp. 1077-1091. DOI: "
        "https://doi.org/10.1007/s11633-023-1463-3.",
    ),
    (
        "Chukhran et al., 2025",
        ["(Chukhran et al., 2025)"],
        'Chukhran, I., Udovenko, S., Shergin, V., Chala, L. (2025), "Method of '
        "Completing 3D Models of Point Clouds Using Graph Neural Networks\", "
        "Innovative Technologies and Scientific Solutions for Industries, "
        "No. 2(32), pp. 129-150. DOI: "
        "https://doi.org/10.30837/2522-9818.2025.2.129.",
    ),
    (
        "von der Malsburg, 1999",
        [
            "Malsburg (1999)",
            "(Malsburg, 1999)",
            "(von der Malsburg, 1999)",
            "von der Malsburg (1999)",
        ],
        'von der Malsburg, C. (1999), "The what and why of binding: the modeler\'s '
        'perspective", Neuron, Vol. 24, No. 1, pp. 95-104. DOI: '
        "https://doi.org/10.1016/S0896-6273(00)80825-9.",
    ),
    (
        "Yarbus, 1967",
        ["Yarbus (1967)"],
        'Yarbus, A. L. (1967), "Eye Movements and Vision", Plenum Press, New York. '
        "DOI: https://doi.org/10.1007/978-1-4899-5379-7.",
    ),
    (
        "Bajcsy et al., 2018",
        ["Bajcsy et al. (2018)"],
        'Bajcsy, R., Aloimonos, Y., Tsotsos, J. K. (2018), "Revisiting active '
        'perception", Autonomous Robots, Vol. 42, No. 2, pp. 177-196. DOI: '
        "https://doi.org/10.1007/s10514-017-9615-3.",
    ),
    (
        "Rucci and Victor, 2015",
        ["Rucci and Victor (2015)"],
        'Rucci, M., Victor, J. D. (2015), "The unsteady eye: an information-'
        'processing stage, not a bug", Trends in Neurosciences, Vol. 38, No. 4, '
        "pp. 195-206. DOI: https://doi.org/10.1016/j.tins.2015.01.005.",
    ),
    (
        "Quiroga et al., 2005",
        ["(Quiroga et al., 2005)"],
        'Quiroga, R. Q., Reddy, L., Kreiman, G., Koch, C., Fried, I. (2005), '
        '"Invariant visual representation by single neurons in the human brain", '
        "Nature, Vol. 435, pp. 1102-1107. DOI: "
        "https://doi.org/10.1038/nature03687.",
    ),
    (
        "Quiroga, 2012",
        ["(Quiroga, 2012)"],
        'Quiroga, R. Q. (2012), "Concept cells: the building blocks of '
        'declarative memory functions", Nature Reviews Neuroscience, Vol. 13, '
        "No. 8, pp. 587-597. DOI: https://doi.org/10.1038/nrn3251.",
    ),
    (
        "Magee, 2000",
        ["(Magee, 2000)"],
        'Magee, J. C. (2000), "Dendritic integration of excitatory synaptic '
        'input", Nature Reviews Neuroscience, Vol. 1, No. 3, pp. 181-190. DOI: '
        "https://doi.org/10.1038/35044552.",
    ),
    (
        "Häusser, 2001",
        ["(Häusser, 2001)"],
        'Häusser, M. (2001), "Synaptic function: dendritic democracy", Current '
        "Biology, Vol. 11, No. 1, pp. R10-R12. DOI: "
        "https://doi.org/10.1016/S0960-9822(00)00034-8.",
    ),
    (
        "Branco and Häusser, 2010",
        ["(Branco and Häusser, 2010)"],
        'Branco, T., Häusser, M. (2010), "The single dendritic branch as a '
        "fundamental functional unit in the nervous system\", Current Opinion in "
        "Neurobiology, Vol. 20, No. 4, pp. 494-502. DOI: "
        "https://doi.org/10.1016/j.conb.2010.07.009.",
    ),
    (
        "Larkum, 2022",
        ["(Larkum, 2022)"],
        'Larkum, M. E. (2022), "Are dendrites conceptually useful?", '
        "Neuroscience, Vol. 489, pp. 4-14. DOI: "
        "https://doi.org/10.1016/j.neuroscience.2022.03.008.",
    ),
    (
        "Parzhin et al., 2022",
        ["(Parzhin et al., 2022)"],
        'Parzhin, Y., Galkyn, S., Sobol, M. (2022), "Method for binary contour '
        "images vectorization based on structural connection tracking\", "
        "2022 IEEE 3rd KhPI Week on Advanced Technology (KhPIWeek), pp. 1-6. "
        "DOI: https://doi.org/10.1109/KhPIWeek57572.2022.9916331.",
    ),
    (
        "Davey and Priestley, 2002",
        ["(Davey and Priestley, 2002)"],
        'Davey, B. A., Priestley, H. A. (2002), "Introduction to Lattices and '
        'Order", Cambridge University Press, Cambridge, 2nd ed. DOI: '
        "https://doi.org/10.1017/CBO9780511809088.",
    ),
    (
        "Ganter and Wille, 1999",
        ["(Ganter and Wille, 1999)"],
        'Ganter, B., Wille, R. (1999), "Formal Concept Analysis: Mathematical '
        'Foundations", Springer, Berlin. DOI: '
        "https://doi.org/10.1007/978-3-642-59830-2.",
    ),
    (
        "Buzsáki, 2010",
        ["(Buzsáki, 2010)"],
        'Buzsáki, G. (2010), "Neural syntax: cell assemblies, synapsembles, and '
        'readers", Neuron, Vol. 68, No. 3, pp. 362-385. DOI: '
        "https://doi.org/10.1016/j.neuron.2010.09.023.",
    ),
    (
        "Glansdorff and Prigogine, 1971",
        ["(Glansdorff and Prigogine, 1971)"],
        'Glansdorff, P., Prigogine, I. (1971), "Thermodynamic Theory of '
        'Structure, Stability and Fluctuations", Wiley-Interscience, London.',
    ),
    (
        "Strogatz, 2015",
        ["(Strogatz, 2015)"],
        'Strogatz, S. H. (2015), "Nonlinear Dynamics and Chaos: With Applications '
        'to Physics, Biology, Chemistry and Engineering", Westview Press, '
        "Boulder, CO, 2nd ed.",
    ),
    (
        "Bredon, 1967",
        ["(Bredon, 1967)"],
        'Bredon, G. E. (1967), "Sheaf Theory", Springer, New York. DOI: '
        "https://doi.org/10.1007/978-1-4612-0647-7.",
    ),
    (
        "Parzhin et al., 2020",
        ["(Parzhin et al., 2020)"],
        'Parzhin, Y., Kosenko, V., Podorozhniak, A., Malyeyeva, O., Timofeyev, V. '
        '(2020), "Detector neural network vs connectionist artificial neural '
        'networks", Neurocomputing, Vol. 414, pp. 191-203. DOI: '
        "https://doi.org/10.1016/j.neucom.2020.07.025.",
    ),
    (
        "Parzhyn, Lapin, Bokhan, 2025",
        ["(Parzhyn, Lapin and Bokhan, 2025)"],
        'Parzhyn, Y., Lapin, M., Bokhan, K. (2025), "A new approach to building '
        'energy models of neural networks", Advanced Information Systems, '
        "Vol. 9, No. 4, pp. 100-119. DOI: "
        "https://doi.org/10.20998/2522-9052.2025.4.1.",
    ),
    (
        "Riesen, 2015",
        ["Riesen (2015)"],
        'Riesen, K. (2015), "Structural Pattern Recognition with Graph Edit '
        'Distance: Approximation Algorithms and Applications", Springer '
        "International Publishing, Cham. DOI: "
        "https://doi.org/10.1007/978-3-319-27252-8.",
    ),
    (
        "Fritzke, 1995",
        ["(Fritzke, 1995)"],
        'Fritzke, B. (1995), "A growing neural gas network learns topologies", '
        "Advances in Neural Information Processing Systems 7 (NeurIPS 1994), "
        "pp. 625-632. DOI: https://doi.org/10.5555/2998687.2998765.",
    ),
    (
        "Douglas and Peucker, 1973",
        ["(Douglas and Peucker, 1973)"],
        'Douglas, D. H., Peucker, T. K. (1973), "Algorithms for the reduction of '
        "the number of points required to represent a digitized line or its "
        'caricature", Cartographica: The International Journal for Geographic '
        "Information and Geovisualization, Vol. 10, No. 2, pp. 112-122. DOI: "
        "https://doi.org/10.3138/FM57-6770-U75U-7727.",
    ),
    (
        "Hagberg, Schult and Swart, 2008",
        ["(Hagberg, Schult and Swart, 2008)"],
        'Hagberg, A. A., Schult, D. A., Swart, P. J. (2008), "Exploring network '
        'structure, dynamics, and function using NetworkX", Proceedings of the '
        "7th Python in Science Conference (SciPy 2008), pp. 11-15. DOI: "
        "https://doi.org/10.25080/TCWV9851.",
    ),
    (
        "European Parliament and Council of the European Union, 2024",
        ["(European Parliament and Council of the European Union, 2024)"],
        'European Parliament, Council of the European Union (2024), "Regulation '
        "(EU) 2024/1689 of the European Parliament and of the Council of 13 June "
        "2024 laying down harmonised rules on artificial intelligence "
        '(Artificial Intelligence Act)", Official Journal of the European Union, '
        "L series, 12 July 2024.",
    ),
    (
        "European Parliament and Council of the European Union, 2016",
        ["(European Parliament and Council of the European Union, 2016)"],
        'European Parliament, Council of the European Union (2016), "Regulation '
        "(EU) 2016/679 of the European Parliament and of the Council of 27 April "
        "2016 on the protection of natural persons with regard to the processing "
        "of personal data and on the free movement of such data (General Data "
        'Protection Regulation)", Official Journal of the European Union, '
        "L 119, 4 May 2016, pp. 1-88.",
    ),
]

KEY_TO_NUM = {key: i + 1 for i, (key, _, _) in enumerate(VANCOUVER)}


# ---------------------------------------------------------------------------
# Citation replacement patterns
# ---------------------------------------------------------------------------

# The specific Harvard surface forms in the original text. Order matters:
# narrative replacements run BEFORE parenthetical so that "Author (year)" doesn't
# get partially mangled by the parenthetical regex.

NARRATIVE_REPLACEMENTS: List[Tuple[str, str]] = [
    ("Minh et al. (2022)", f"Minh et al. [{KEY_TO_NUM['Minh et al., 2022']}]"),
    (
        "Hooshyar and Yang (2024)",
        f"Hooshyar and Yang [{KEY_TO_NUM['Hooshyar and Yang, 2024']}]",
    ),
    (
        "Rajabi and Etminani (2024)",
        f"Rajabi and Etminani [{KEY_TO_NUM['Rajabi and Etminani, 2024']}]",
    ),
    ("Nawaz et al. (2025)", f"Nawaz et al. [{KEY_TO_NUM['Nawaz et al., 2025']}]"),
    ("Slack et al. (2020)", f"Slack et al. [{KEY_TO_NUM['Slack et al., 2020']}]"),
    (
        "Sanfeliu and Fu (1983)",
        f"Sanfeliu and Fu [{KEY_TO_NUM['Sanfeliu and Fu, 1983']}]",
    ),
    ("Conte et al. (2004)", f"Conte et al. [{KEY_TO_NUM['Conte et al., 2004']}]"),
    (
        "Riesen and Bunke (2009)",
        f"Riesen and Bunke [{KEY_TO_NUM['Riesen and Bunke, 2009']}]",
    ),
    ("Piao et al. (2023)", f"Piao et al. [{KEY_TO_NUM['Piao et al., 2023']}]"),
    (
        "Moscatelli et al. (2024)",
        f"Moscatelli et al. [{KEY_TO_NUM['Moscatelli et al., 2024']}]",
    ),
    ("Xie et al. (2024)", f"Xie et al. [{KEY_TO_NUM['Xie et al., 2024']}]"),
    ("Yarbus (1967)", f"Yarbus [{KEY_TO_NUM['Yarbus, 1967']}]"),
    ("Bajcsy et al. (2018)", f"Bajcsy et al. [{KEY_TO_NUM['Bajcsy et al., 2018']}]"),
    (
        "Rucci and Victor (2015)",
        f"Rucci and Victor [{KEY_TO_NUM['Rucci and Victor, 2015']}]",
    ),
    ("Snell et al. (2017)", f"Snell et al. [{KEY_TO_NUM['Snell et al., 2017']}]"),
    ("Riesen (2015)", f"Riesen [{KEY_TO_NUM['Riesen, 2015']}]"),
    (
        "von der Malsburg (1999)",
        f"von der Malsburg [{KEY_TO_NUM['von der Malsburg, 1999']}]",
    ),
    ("Malsburg (1999)", f"Malsburg [{KEY_TO_NUM['von der Malsburg, 1999']}]"),
    ("Buzsáki (2010)", f"Buzsáki [{KEY_TO_NUM['Buzsáki, 2010']}]"),
]


# Parenthetical citations. Multi-cite groups are handled by mapping the entire
# expression to a comma-separated [N1, N2, …]. We use string replace so that
# ordering is straightforward — list longest first to avoid prefix collisions.

def n(key: str) -> int:
    return KEY_TO_NUM[key]


PAREN_REPLACEMENTS: List[Tuple[str, str]] = [
    # Multi-cites first
    (
        "(Magee, 2000; Häusser, 2001; Branco and Häusser, 2010; Larkum, 2022)",
        f"[{n('Magee, 2000')}, {n('Häusser, 2001')}, {n('Branco and Häusser, 2010')}, {n('Larkum, 2022')}]",
    ),
    (
        "(Häusser, 2001; Branco and Häusser, 2010; Magee, 2000)",
        f"[{n('Häusser, 2001')}, {n('Branco and Häusser, 2010')}, {n('Magee, 2000')}]",
    ),
    (
        "(Glansdorff and Prigogine, 1971; Strogatz, 2015)",
        f"[{n('Glansdorff and Prigogine, 1971')}, {n('Strogatz, 2015')}]",
    ),
    (
        "(Quiroga et al., 2005; Quiroga, 2012)",
        f"[{n('Quiroga et al., 2005')}, {n('Quiroga, 2012')}]",
    ),
    (
        "(Yarbus, 1967; Bajcsy et al., 2018; Rucci and Victor, 2015)",
        f"[{n('Yarbus, 1967')}, {n('Bajcsy et al., 2018')}, {n('Rucci and Victor, 2015')}]",
    ),
    # Compound-with-clause
    (
        "(analogously to local-to-global consistency in sheaf theory, Bredon, 1967)",
        f"(analogously to local-to-global consistency in sheaf theory [{n('Bredon, 1967')}])",
    ),
    (
        "(which is graph-edit-distance based, Piao et al., 2023)",
        f"(which is graph-edit-distance based [{n('Piao et al., 2023')}])",
    ),
    (
        "(their formulation lies outside the scope of this work; Parzhin et al., 2020)",
        f"(their formulation lies outside the scope of this work [{n('Parzhin et al., 2020')}])",
    ),
    # Singletons
    ("(Parzhyn, 2025)", f"[{n('Parzhyn, 2025)')}]" if False else f"[{n('Parzhyn, 2025')}]"),
    ("(LeCun et al., 1998)", f"[{n('LeCun et al., 1998')}]"),
    ("(Snell et al., 2017)", f"[{n('Snell et al., 2017')}]"),
    ("(Vinyals et al., 2016)", f"[{n('Vinyals et al., 2016')}]"),
    ("(Finn et al., 2017)", f"[{n('Finn et al., 2017')}]"),
    ("(Ribeiro et al., 2016)", f"[{n('Ribeiro et al., 2016')}]"),
    ("(Lundberg and Lee, 2017)", f"[{n('Lundberg and Lee, 2017')}]"),
    ("(Ding et al., 2022)", f"[{n('Ding et al., 2022')}]"),
    ("(Lapin and Bokhan, 2025)", f"[{n('Lapin and Bokhan, 2025')}]"),
    ("(Conte et al., 2004)", f"[{n('Conte et al., 2004')}]"),
    ("(Riesen and Bunke, 2009)", f"[{n('Riesen and Bunke, 2009')}]"),
    ("(Piao et al., 2023)", f"[{n('Piao et al., 2023')}]"),
    ("(Davey and Priestley, 2002)", f"[{n('Davey and Priestley, 2002')}]"),
    ("(Ganter and Wille, 1999)", f"[{n('Ganter and Wille, 1999')}]"),
    ("(von der Malsburg, 1999)", f"[{n('von der Malsburg, 1999')}]"),
    ("(Buzsáki, 2010)", f"[{n('Buzsáki, 2010')}]"),
    ("(Parzhin et al., 2022)", f"[{n('Parzhin et al., 2022')}]"),
    ("(Parzhin et al., 2020)", f"[{n('Parzhin et al., 2020')}]"),
    ("(Larkum, 2022)", f"[{n('Larkum, 2022')}]"),
    ("(Quiroga et al., 2005)", f"[{n('Quiroga et al., 2005')}]"),
    ("(Fritzke, 1995)", f"[{n('Fritzke, 1995')}]"),
    ("(Douglas and Peucker, 1973)", f"[{n('Douglas and Peucker, 1973')}]"),
    ("(Hagberg, Schult and Swart, 2008)", f"[{n('Hagberg, Schult and Swart, 2008')}]"),
    (
        "(European Parliament and Council of the European Union, 2024)",
        f"[{n('European Parliament and Council of the European Union, 2024')}]",
    ),
    (
        "(European Parliament and Council of the European Union, 2016)",
        f"[{n('European Parliament and Council of the European Union, 2016')}]",
    ),
]


# ---------------------------------------------------------------------------
# Body-text additions for newly-cited references
# ---------------------------------------------------------------------------

# After "Xie et al. (2024) ..." in P022, append a sentence citing Chukhran 2025.
# After "Glansdorff and Prigogine (1971) and Strogatz (2015)..." we'll inject
# the energy-models reference inside Conclusions paragraph 134 (final future-
# work pointers).

CHUKHRAN_INSERT_TARGET = (
    "Xie et al."  # we look for the sentence containing this and append after period
)

ENERGY_MODELS_CITATION = (
    f" An alternative formulation grounded in energy minimisation for related "
    f"neural-network models was developed in [{n('Parzhyn, Lapin, Bokhan, 2025')}]."
)


# ---------------------------------------------------------------------------
# Information-about-the-authors block (ITSSI order)
# ---------------------------------------------------------------------------

# Each author block is rebuilt from these fields. Telephone is intentionally omitted.
AUTHORS_INFO = [
    {
        "ua_name": "Лапін Микита Олексійович",
        "ua_block": (
            "аспірант, Національний технічний університет \"Харківський "
            "політехнічний інститут\", аспірант кафедри системного аналізу та "
            "інформаційно-аналітичних технологій, Харків, Україна."
        ),
        "en_name": "Mykyta Lapin",
        "en_block": (
            "PhD student, National Technical University \"Kharkiv Polytechnic "
            "Institute\", PhD student at the Department of Systems Analysis and "
            "Information-Analytical Technologies, Kharkiv, Ukraine;"
        ),
        "email": "Mykyta.Lapin@cit.khpi.edu.ua",
        "orcid": "https://orcid.org/0009-0003-6307-1172",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=60171161300",
    },
    {
        "ua_name": "Паржин Юрій Володимирович",
        "ua_block": (
            "доктор технічних наук, Університет Огасти, постдокторант Школи "
            "Комп'ютерних та Кібер Наук, м. Огаста, Джорджія, США."
        ),
        "en_name": "Yurii Parzhyn",
        "en_block": (
            "Doctor of Sciences (Engineering), Augusta University, Postdoctoral "
            "Fellow at the School of Computer and Cyber Sciences, Augusta, "
            "Georgia, USA;"
        ),
        "email": "yparzhyn@augusta.edu",
        "orcid": "https://orcid.org/0000-0001-5727-1918",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57224412390",
    },
    {
        "ua_name": "Бохан Костянтин Олександрович",
        "ua_block": (
            "кандидат технічних наук, доцент, Національний технічний "
            "університет \"Харківський політехнічний інститут\", доцент "
            "кафедри системного аналізу та інформаційно-аналітичних "
            "технологій, Харків, Україна."
        ),
        "en_name": "Kostiantyn Bokhan",
        "en_block": (
            "Candidate of Technical Sciences (PhD in Engineering), Associate "
            "Professor, National Technical University \"Kharkiv Polytechnic "
            "Institute\", Associate Professor at the Department of Systems "
            "Analysis and Information-Analytical Technologies, Kharkiv, "
            "Ukraine;"
        ),
        "email": "kostiantyn.bokhan@khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0003-3375-2527",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57191592568",
    },
    {
        "ua_name": "Перевозник Кирило Максимович",
        "ua_block": (
            "аспірант, Національний технічний університет \"Харківський "
            "політехнічний інститут\", аспірант кафедри системного аналізу та "
            "інформаційно-аналітичних технологій, Харків, Україна."
        ),
        "en_name": "Kyrylo Perevoznyk",
        "en_block": (
            "PhD student, National Technical University \"Kharkiv Polytechnic "
            "Institute\", PhD student at the Department of Systems Analysis and "
            "Information-Analytical Technologies, Kharkiv, Ukraine;"
        ),
        "email": "kyrylo.perevoznyk@cs.khpi.edu.ua",
        "orcid": "https://orcid.org/0009-0009-2327-1501",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=59564678000",
    },
    {
        "ua_name": "Александрова Тетяна Євгенівна",
        "ua_block": (
            "доктор технічних наук, професор, Національний технічний "
            "університет \"Харківський політехнічний інститут\", завідувач "
            "кафедри системного аналізу та інформаційно-аналітичних "
            "технологій, Харків, Україна."
        ),
        "en_name": "Tetiana Aleksandrova",
        "en_block": (
            "Doctor of Sciences (Engineering), Professor, National Technical "
            "University \"Kharkiv Polytechnic Institute\", Head of the "
            "Department of Systems Analysis and Information-Analytical "
            "Technologies, Kharkiv, Ukraine;"
        ),
        "email": "Tetiana.Aleksandrova@khpi.edu.ua",
        "orcid": "https://orcid.org/0000-0001-9596-0669",
        "scopus": "https://www.scopus.com/authid/detail.uri?authorId=57189376480",
    },
]


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


def replace_in_t_text(text: str) -> str:
    """Apply citation replacements to a single <w:t> text value."""
    if not text:
        return text
    out = text
    # Narrative replacements first
    for old, new in NARRATIVE_REPLACEMENTS:
        out = out.replace(old, new)
    # Then parenthetical
    for old, new in PAREN_REPLACEMENTS:
        out = out.replace(old, new)
    # Inject Chukhran 2025 after the Xie sentence
    if "Xie et al. [" in out and "Chukhran" not in out and CHUKHRAN_INSERT_TARGET in out:
        # Find sentence ending after Xie et al [N]
        # Pattern: "...Xie et al. [N] ... .  Other..."
        # We'll append after the first period ending a sentence containing "Xie et al."
        match = re.search(
            r"(Xie et al\.\s*\[\d+\][^.]*?\.)", out
        )
        if match:
            insert_pos = match.end()
            chukhran_sentence = (
                f" A complementary direction within the same problem class is "
                f"reconstruction of incomplete spatial graphs by graph neural "
                f"networks, exemplified by the recent work [{n('Chukhran et al., 2025)') if False else n('Chukhran et al., 2025')}] "
                f"on completing 3D point-cloud models in the same journal."
            )
            out = out[:insert_pos] + chukhran_sentence + out[insert_pos:]
    # Inject energy-models citation in Conclusions paragraph
    # We mark via a unique sentinel — the Conclusions paragraph contains
    # "structural attractor as the fixed point of the reduction operator"
    energy_token = "[" + str(n('Parzhyn, Lapin, Bokhan, 2025')) + "]"
    if (
        "structural attractor as the fixed point of the reduction operator"
        in out
        and energy_token not in out
    ):
        stripped = out.rstrip()
        if not stripped.endswith("."):
            stripped += "."
        out = stripped + ENERGY_MODELS_CITATION
    return out


def collect_citation_replacement_targets(root: etree._Element) -> List[etree._Element]:
    body = root.find(w("body"))
    return body.findall(w("p"))


def find_paragraph_with_text(paras: List[etree._Element], substring: str) -> int | None:
    for i, p in enumerate(paras):
        text = "".join(t.text or "" for t in p.iter(w("t")))
        if substring in text:
            return i
    return None


def paragraph_text(p: etree._Element) -> str:
    return "".join(t.text or "" for t in p.iter(w("t")))


def replace_citations_in_body(body: etree._Element, ref_idx: int) -> None:
    """Apply citation replacements to <w:t> nodes in body up to References."""
    paras = body.findall(w("p"))
    for i, p in enumerate(paras):
        if i >= ref_idx:
            break  # don't touch References & after
        for t in p.iter(w("t")):
            t.text = replace_in_t_text(t.text or "")


def rebuild_references(body: etree._Element, ref_idx: int) -> None:
    """Replace alphabetical Harvard References block with Vancouver-numbered list."""
    paras = body.findall(w("p"))
    # Find end of references block — first paragraph that begins
    # "Відомості про авторів" or "Information about" after ref_idx
    end_idx = len(paras)
    for j in range(ref_idx + 1, len(paras)):
        text = paragraph_text(paras[j]).strip()
        if (
            text.startswith("Відомості про авторів")
            or text.startswith("Information about")
            or text.startswith("ІНВАРІАНТНО-СТРУКТУРНЕ")
        ):
            end_idx = j
            break
    # Keep the "References" header paragraph (paras[ref_idx]) intact.
    # Remove the alphabetical entries (paras[ref_idx+1:end_idx]).
    # Use one of the existing reference paragraphs as a style template.
    template = None
    for j in range(ref_idx + 1, end_idx):
        if paragraph_text(paras[j]).strip():
            template = deepcopy(paras[j])
            break
    if template is None:
        raise RuntimeError("No reference paragraph template found")

    # Strip all child <w:r>/<w:hyperlink>/etc from template, keep <w:pPr>
    for child in list(template):
        if not child.tag.endswith("}pPr"):
            template.remove(child)

    # Remove existing reference paragraphs (between ref_idx and end_idx, skip header)
    for j in range(end_idx - 1, ref_idx, -1):
        body.remove(paras[j])

    # Insert new Vancouver-numbered entries right after the "References" header.
    insertion_index = list(body).index(paras[ref_idx]) + 1
    for num in range(len(VANCOUVER), 0, -1):
        key, _, full_entry = VANCOUVER[num - 1]
        new_p = deepcopy(template)
        # Append a single run with text "[N] {full_entry}"
        r = etree.SubElement(new_p, w("r"))
        t = etree.SubElement(r, w("t"))
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = f"{num}. {full_entry}"
        body.insert(insertion_index, new_p)


def rebuild_authors_block(body: etree._Element) -> None:
    """Replace 'Відомості про авторів' English block with new ITSSI order.

    The Ukrainian per-author block (P195, P199, P203, P207, P211 в Паржині) і
    англомовний блок (P196-197, P200-201, P204-205, P208-209, P212-213) ми
    переписуємо у формат «ступінь, звання, організація, посада».
    """
    paras = body.findall(w("p"))
    # Find the 'Відомості про авторів' header
    start = None
    for i, p in enumerate(paras):
        if "Відомості про авторів" in paragraph_text(p):
            start = i
            break
    if start is None:
        return
    # End: next paragraph that starts with the Ukrainian-uppercase title
    end = len(paras)
    for j in range(start + 1, len(paras)):
        text = paragraph_text(paras[j]).strip()
        if text.startswith("ІНВАРІАНТНО") or text.startswith("Лапін М. О., Паржин"):
            end = j
            break

    # Pick a template paragraph for normal text (the 'Лапін' line)
    template = None
    for j in range(start + 1, end):
        text = paragraph_text(paras[j]).strip()
        if text and "@" not in text and "ORCID" not in text:
            template = deepcopy(paras[j])
            break
    if template is None:
        return
    # Strip children but keep pPr
    for child in list(template):
        if not child.tag.endswith("}pPr"):
            template.remove(child)

    # Remove existing per-author paragraphs (skip header at `start`)
    for j in range(end - 1, start, -1):
        body.remove(paras[j])

    insertion_index = list(body).index(paras[start]) + 1

    def emit_para(text: str) -> etree._Element:
        np = deepcopy(template)
        r = etree.SubElement(np, w("r"))
        t = etree.SubElement(r, w("t"))
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text
        return np

    for author in reversed(AUTHORS_INFO):
        # Insert in reverse so the final order matches AUTHORS_INFO
        # Block order:
        #   1) "{ua_name} – {ua_block}"
        #   2) "{en_name} – {en_block}"
        #   3) "e-mail: …; ORCID: …; Scopus: …"
        #   4) blank
        blank = emit_para("")
        contact = emit_para(
            f"e-mail: {author['email']}; ORCID Author ID: {author['orcid']}; "
            f"Scopus Author ID: {author['scopus']}."
        )
        en_para = emit_para(f"{author['en_name']} – {author['en_block']}")
        ua_para = emit_para(f"{author['ua_name']} – {author['ua_block']}")
        for new_p in (blank, contact, en_para, ua_para):
            body.insert(insertion_index, new_p)


def main(args) -> None:
    src = Path(args.src) if args.src else SRC_DOCX
    dst = Path(args.dst) if args.dst else DST_DOCX

    if dst.exists():
        dst.unlink()
    shutil.copy(src, dst)

    # Read document.xml from the copy
    with zipfile.ZipFile(dst, "r") as zf:
        doc_xml = zf.read("word/document.xml")

    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(doc_xml, parser)
    body = root.find(w("body"))
    paras = body.findall(w("p"))

    ref_idx = None
    for i, p in enumerate(paras):
        if paragraph_text(p).strip() == "References":
            ref_idx = i
            break
    if ref_idx is None:
        raise RuntimeError("References paragraph not found")

    print(f"References at P{ref_idx} of {len(paras)}")

    print("Replacing inline citations …")
    replace_citations_in_body(body, ref_idx)

    print("Rebuilding References list (Vancouver order) …")
    rebuild_references(body, ref_idx)

    print("Rebuilding 'Відомості про авторів' block …")
    rebuild_authors_block(body)

    # Serialise
    new_xml = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    # Replace document.xml in the copy zip
    tmp_zip = dst.with_suffix(".tmp.docx")
    with (
        zipfile.ZipFile(dst, "r") as zin,
        zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml
            zout.writestr(item, data)
    tmp_zip.replace(dst)
    print(f"Wrote {dst}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=None)
    parser.add_argument("--dst", default=None)
    args = parser.parse_args()
    main(args)
