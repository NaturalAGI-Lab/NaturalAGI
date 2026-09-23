% Error Anatomy and Concept Stability in a Graph-Based Classifier Without Backpropagation

:::abstract
Structural classifiers expose their representations, but readable graphs do not by themselves establish reliable recognition or stable learning. This paper audits a non-backpropagation handwritten-digit classifier that reduces attributed skeleton graphs into class concepts and ranks graph-edit matches. A selected MNIST evaluation produced 7,915 correct decisions among 8,685 completed records: 91.13% conditional accuracy, or 90.90% across all 8,707 admitted records. We analyse 111 errors from digit 2 to digit 7 and distinguish graph construction, candidate preparation, edit costs and final ranking. Removing the complexity prefilter did not recover the richer digit-2 concept in the archived replay; the remaining digit-2 concept also lost the raw-similarity comparison. Offline formation probes then separate structural stability from attribute stability. Across ten sample orders, two tested concepts preserved their labelled topology, whereas the third formed two labelled-graph families. Across thirteen selected formation cohorts, node and edge counts reached their final values after 1–37 samples, while coordinate envelopes could continue changing. Additional runs expose the effect of input selection and incomplete processing on reported accuracy. These observations support decision-level auditability and finite-sample structural stabilization, but not order-invariant learning, topological attractors, or robustness to unrestricted handwritten inputs.
:::

:::keywords
Structural pattern recognition, Graph edit distance, Concept formation
:::

# Introduction

An explicit decision process is useful only if its intermediate objects can explain both successful predictions and failures. Interpretable machine learning therefore requires more than a visually plausible explanation attached to a prediction [1]. In structural recognition, an image graph can reveal what the system retained, while an edit path can show how that graph was matched to a class representation. However, the same representation can also discard a discriminative feature, admit an overly general concept, or depend on the order of training examples.

This paper examines these issues in NaturalAGI, a classifier that learns attributed graph concepts without backpropagation. Handwritten images are converted into skeleton graphs; repeated graph reduction creates a compact representative for each configured subclass. Classification prepares a candidate-specific image graph, evaluates an asymmetric graph-edit cost, and applies a complexity-adjusted winner-take-all rule. Every stage is inspectable, but inspection must distinguish the mathematical model from the particular implementation and dataset selection.

The research question is whether the observed recognition and formation behaviour supports the stronger interpretation of a stable structural concept, and where that interpretation fails. We address it through three connected analyses. First, an error audit follows the dominant 2→7 confusion through graph construction, candidate eligibility, matching and ranking. Second, cached formation experiments vary sample order and sample count, measuring topology and attribute envelopes separately. Third, evaluation records are reconciled against their actual denominators, including dead-letter and missing-result outcomes.

The contribution is an empirical audit: it connects candidate rejection with feature-range penalties, identifies order sensitivity despite invariant node counts, and separates structural stabilization from attribute convergence and generalization. It evaluates an existing architecture rather than claiming a new recognition model or state-of-the-art MNIST accuracy.

# Related Work

## Interpretability and the limits of visible explanations

Rudin et al. [1] distinguish interpretable modelling objectives and their assessment. Here interpretability concerns access to the graph labels, feature ranges, reductions and costs that determine a prediction. Whether a non-specialist understands that trace remains a separate, untested question.

Explanations also need robustness checks. Baniecki and Biecek [2] survey attacks that alter or exploit model explanations, while García-Cuesta et al. [3] examine fragility in prototype-based explanations. These studies motivate checking the consistency of an explanatory mechanism rather than accepting its visual plausibility. They do not establish that explicit graph methods are immune to manipulation. Our audit addresses ordinary misclassification and training-order sensitivity, not adversarial security.

Forest et al. [4] use concept bottlenecks to expose degradation information for remaining-useful-life prediction and intervention. Our concepts are instead attributed representative graphs with feature envelopes, not an independently validated vocabulary of human semantics. These two meanings of concept entail different interpretability claims.

## Graph representations and matching

Graph construction is itself a modelling choice. Gan et al. [5] represent handwritten Chinese characters with skeleton graphs and process them using a Pyramid Graph Transformer. Han et al. [6] construct Vision GNN graphs from image patches and learn interactions between neighbouring nodes. Both demonstrate that graph-structured representations can participate in modern visual recognition; neither makes graph classification inherently non-backpropagation. Our representation is an explicit point–vector incidence graph, and learning updates that graph rather than a graph neural network.

Inexact graph matching has a long history in structural pattern recognition [7]. Its costs specify which discrepancies can be tolerated and therefore embody part of the recognition model. Recent work combines combinatorial search with learned guidance: Wang et al. [8] learn an A* search heuristic for graph edit distance, while Piao et al. [9] jointly predict edit distance and node matching. Tang et al. [10] formulate graph alignment through fused Gromov–Wasserstein optimization. These approaches are relevant alternatives for matching efficiency and alignment quality, but their benchmark results are not directly comparable with the selected MNIST cohorts studied here.

Replacing the distance optimizer would not necessarily change the structural eligibility conditions preceding it. We therefore distinguish preparation failures, computed edit costs and later class-ranking scores.

## Learning without backpropagation and small training sets

Avoiding backpropagation does not identify a single learning mechanism. Hinton’s Forward-Forward procedure [11], for example, uses positive and negative forward passes with layer-local objectives. Neuro-symbolic approaches cover a broader range of combinations of learning and structured reasoning [12]. The present method belongs to neither category by default: it incrementally aligns and reduces explicit graphs using configured structural and feature costs.

Small numbers of training examples also require careful qualification. Meta-learning and few-shot learning commonly exploit experience acquired across tasks or transferred representations [13, 14]. NaturalAGI’s source-example count is therefore not a like-for-like measure of data efficiency against such systems. Its image-processing rules, subclass choices, geometric augmentation and selected evaluation cohort supply substantial prior structure. We report these conditions rather than equating a small source set with general few-shot capability.

Earlier work by the authors develops the underlying detector and concept-formation programme [15, 16]. The present paper contributes an empirical stability and failure analysis of the implementation, not an independent replication of those publications. In particular, graph visibility, finite-sample stabilization and a successful self-match are treated as separate observations rather than combined into a proof of a stable semantic attractor.

# Materials and Methods

## From an image to an attributed graph

The processing pipeline first thresholds the grayscale image, cleans small components and performs morphological closing. Zhang–Suen thinning [17] and adaptive branch pruning produce a skeleton. Growing Neural Gas [18] approximates the skeleton, after which Douglas–Peucker simplification [19] reduces geometric detail and nearby junctions are merged. In the baseline configuration, the initial intensity threshold was 110 and the simplification tolerance was 4.55. Disconnected results could trigger retries at lower thresholds, in steps of five down to 20; 110 was therefore not a fixed threshold for every production image.

The stored representation is a bipartite incidence graph. Point nodes describe geometric locations; Vector nodes reify the binary connections between points. Edges link points to vectors, not arbitrary sets of points. We write an attributed graph as G = (V, E, A), where A includes labels and measured features, and define its implementation-level complexity as follows:

:::equation
C(G)=|V|+|E|. \tag{1}
:::

Point labels include endpoints, corners, junctions and a designated start point. Features include relative coordinates, directions, angles, neighbouring-branch information and length ratios. Coordinate normalization uses the centre of the graph’s bounding box, not the image centre. With half-width h_x and half-height h_y, coordinates are divided by the half-diagonal ρ = √(h_x² + h_y²), then rounded to one decimal place. Feature-specific scaling is applied where required before classification. Widths of normalized-x/y envelopes reported below refer to the stored coordinate convention, not a universal probability scale.

Anchoring does not ensure identical detail across independently constructed graphs. Thresholding can join strokes, pruning can remove a branch, and GNG or simplification can change the geometry. Final topology must therefore be interpreted against the recorded construction protocol.

## Incremental concept formation and candidate preparation

A configured subclass is represented by one concept graph. Formation starts from a sample graph and processes subsequent graphs incrementally. The implementation aligns candidate start points, seeks compatibility between critical-point structures, and reduces endpoint, intersection or corner structures where supported. Surviving matched elements accumulate attribute ranges and representative values. Range centres are accumulated statistics; they must not be assumed to equal the midpoint of the two stored bounds.

Reduction is constrained and order dependent in principle. Choosing the first graph fixes an initial structure, while subsequent alignments determine which elements survive and which measurements are aggregated. Although reductions remove elements, labels can also be recomputed or reassigned after a structural change. Thus neither monotonic loss of every label nor uniqueness of the final attributed graph follows from a shrinking node count.

Classification uses a separate preparation step for each concept. An initial complexity filter excludes concepts more complex than the input graph. For the remaining candidates, an image copy is aligned and reduced towards the concept’s critical structure. A failure to obtain the required compatibility is an eligibility failure, not a zero-cost match. The diagnostic exports encode such rejected comparisons with a zero similarity; this sentinel must not be interpreted as a completed GED calculation.

This distinction is important for ablation design. Disabling the initial complexity filter changes which candidates reach preparation, but it does not disable the later structural checks. Likewise, changing a ranking coefficient cannot recover a concept that never produces an eligible comparison. We therefore retain separate records for initial filtering, structural preparation, raw matching and final selection.

## Feature costs, graph similarity and winner selection

The archived baseline checks thirteen features: normalized x and y, distance to centroid, horizontal and vertical direction, angle with the x-axis, minimum junction angle, endpoint and corner flags, length ratio to the longest vector, average neighbouring-vector length, neighbouring-endpoint count, and neighbouring-junction count. Features unavailable on a particular node pair are skipped. The weights of the available features are normalized over that pair, so extending the feature list can dilute existing contributions.

For an interval-valued concept feature f with bounds l_f and u_f, its unnormalized diagnostic weight is a_f/(u_f − l_f + ε); categorical features use a_f without the width term. The baseline used ε = 0.1. Direction-category strengths were 0.6, endpoint/corner strengths 0.4, and the other feature strengths 1.0. The weight offset is positive to avoid singular behaviour for a zero-width range.

Inside a non-zero-width interval, the feature contribution grows with distance from the stored centre and is capped by the feature’s normalized weight. An exact match to a zero-width interval contributes zero. In the archived hard-boundary configuration, an out-of-range value instead contributes the full NO_MATCH cost of 1.0. It is not multiplied by that feature’s normalized weight. This discontinuity can make one boundary violation more influential than several small in-range deviations.

GED is computed with a five-second optimization deadline and asymmetric operations. Node deletion and edge deletion cost 0.25, node insertion costs 6.0, and edge insertion costs zero; edge substitution does not distinguish attributes in this configuration. The six configured node-cost levels are 0, 0.25, 0.5, 0.8, 1.0 and 6.0. These are the archived per-run values, not the current module defaults. A deadline-limited result is not a certificate that the global minimum edit path has been found.

For an eligible prepared image G′_i and concept H_j, let c_ij denote the returned edit cost. The raw similarity and ranking score are:

:::equation
\begin{gathered}s_{ij}=1-\frac{c_{ij}}{c_{ij}+\max\{C(G'_i),C(H_j),1\}},\\r_{ij}=s_{ij}+0.10\log_2 C(H_j).\end{gathered} \tag{2}
:::

The highest ranking score determines the selected concept and hence the digit class. The complexity term is a soft preference for a more structured eligible concept, not a rule that the largest concept always wins. Ranking scores can exceed one and are not calibrated class probabilities. Raw similarity, adjusted ranking and eligibility are therefore reported separately throughout the error analysis.

# Experimental Design

## Evidence sets and evaluation denominators

The experiments use MNIST handwritten digits [20] and archived pipeline outputs. The main accuracy record is the selected-test baseline. Its training archive contains 76 original images and 805 files including geometric variants, distributed across thirteen configured concepts for ten digit classes. The concept snapshot contains 106 nodes and 100 edges. The augmented files are not 805 independent handwritten sources.

The baseline evaluation admitted 8,707 selected test records. Selection excluded incomplete or unsuitable images before submission and was not a class-balanced sampling procedure. For example, 582 of the standard test set’s 974 digit-8 images were admitted, compared with 1,129 of 1,135 digit-1 images. This cohort supports a conditional statement about selected inputs, not a benchmark accuracy claim for the full 10,000-image test split.

We distinguish submitted or admitted records N, completed classification records n, correct decisions k, explicit dead-letter failures d, and records without a collected completion or dead-letter result m. “Completed” includes wrong labels and explicit unrecognized outcomes. Conditional accuracy and all-record accuracy are defined as:

:::equation
A_c=k/n,\qquad A_a=k/N,\qquad N=n+d+m. \tag{3}
:::

An unrecognized completed record contributes to n but not k. A dead-letter failure is counted in d and cannot be silently dropped from the all-record denominator. Missing outcomes contribute to m; the records alone do not establish whether each was caused by image content, a service failure or result collection. We use “all-record accuracy” rather than equating missing processing with a completed wrong prediction.

Additional runs submit the full 10,000-image test split, the 60,000-image training split, and a separately selected 45,501-image complete-input subset of the latter. The 60,000-image split includes sources used to construct the concepts and is not held out. These runs retain their own completion counts and are not pooled into a supposedly independent 70,000-image experiment.

## Error audit and replay protocol

The primary error cohort comprises all 111 baseline records labelled as digit 2 but predicted as digit 7. A construction audit rebuilt these images at a fixed threshold of 110 and recorded pixel-hole, skeleton-hole and final graph-cycle counts. Because this diagnostic did not reproduce the adaptive threshold retries, and because graph construction contains stochastic steps, it is a controlled reconstruction rather than an exact replay of every original production intermediate.

A separate archived comparison replay disabled the initial complexity prefilter and recorded raw and adjusted scores for concepts 2_2, 2_1 and 7_1, together with preparation outcomes. The replay tests whether admitting a previously filtered concept is sufficient to recover the correct alternative. It does not test a different skeletonizer, cost function or ranking coefficient. The representative image mnist_test_2_00766 also has an earlier detailed feature-cost trace. We distinguish its earlier numeric scores from the later replay instead of combining them as one run.

## Formation-order, sample-count and stabilization probes

Formation experiments operate offline on cached sample graphs, without updating the deployed concept store. Their cleaned corpus contains 869 files from 85 sources and is distinct from the baseline training archive. One source group in the 4_1 cohort, comprising six files, was excluded because it mixed open and closed digit-4 topologies that the formation procedure could not reconcile. Its retained cohort contains 36 files from six sources. Results for this cohort are conditional on that morphology-based selection.

The order probe evaluates concepts 2_2, 7_1 and 8_1 under ten shuffled orders, using seeds 0–9. Final graphs are compared by node-label-aware GED with a 20-second deadline. There are 45 pairwise comparisons per concept, but these pairs share fitted graphs and are not independent replicates. This probe tests labelled topology; it does not establish equality of feature values.

The sample-count probe uses N ∈ {2, 5, 10, 20} files and three draws per condition for concepts 2_2, 7_1 and 4_1. N counts cached augmented files, not independent original digits. We inspect final node counts and mean coordinate-envelope width. No downstream classification experiment for these small-sample concepts was completed, so smaller concepts or narrower ranges cannot be read as evidence of better accuracy.

For the full-cohort stabilization probe, let q_t = (|V_t|, |E_t|) denote graph size after t samples, and let W_t be mean normalized-x/y envelope width over the current surviving nodes. We record the earliest suffix for which q_t equals its final value and an envelope-change marker:

:::equation
\begin{gathered}m_s=\min\{t:q_u=q_n,\ \forall u\in\{t,\ldots,n\}\},\\m_e=\min\{t:|W_u-W_{u-1}|<0.02,\ \forall u\in\{t,\ldots,t+4\}\}.\end{gathered} \tag{4}
:::

The envelope search starts at t = 2 and requires t + 4 ≤ n. Its five-change marker is descriptive, not an implemented stopping rule. W_t can decrease when the surviving-node set changes; constant size does not imply invariant adjacency, labels or attributes. Both markers summarize finite recorded trajectories.

## Provenance and scope of inference

The evidence consists of run configurations, metrics, per-class outcomes, concept snapshots, replay CSV files and per-step formation summaries. The baseline manifest records commit f34b049 and a dirty working tree. It therefore identifies a code lineage but does not preserve a fully reconstructible clean source state. Later diagnostics were run after that baseline and may reproduce a decision without reproducing every numeric intermediate.

These are exploratory implementation studies. Sample selection, shared augmented sources, fixed graph caches and the small number of order replicates preclude population-level significance claims. We report observed counts and mechanisms rather than confidence intervals that would assume independent samples. No new accuracy improvement, controlled augmentation ablation, human explanation assessment, or measurement of power consumption is asserted.

# Results

## Recognition outcomes and processing coverage

The baseline run completed 8,685 of 8,707 admitted records and produced 7,915 correct decisions. The remaining completed records comprise 726 wrong class labels and 44 unrecognized outcomes; 22 additional records entered the dead-letter queue. Accordingly, the often-quoted 91.13% is conditional on completion. Across all admitted records, accuracy is 90.90%. The 111 cases of 2→7 constitute 15.29% of wrong class labels, or 14.42% of all 770 unsuccessful completed decisions.

Table 1 compares the independently recorded evaluation runs. The full test split gives 82.21% all-record accuracy, substantially below the selected-test cohort. This difference is consistent with a strong dependence on admission conditions, but it is not a randomized estimate of the effect of completeness filtering: the runs also differ in diagnostic context.

:::table Table 1. Evaluation outcomes; percentages use the explicit denominators defined in Eq. (3).
Run / input cohort | N | n | k | d | m | k/n (%) | k/N (%)
Selected test | 8,707 | 8,685 | 7,915 | 22 | 0 | 91.13 | 90.90
Full test | 10,000 | 9,942 | 8,221 | 58 | 0 | 82.69 | 82.21
Training split | 60,000 | 51,045 | 43,172 | 293 | 8,662 | 84.58 | 71.95
Complete subset | 45,501 | 44,812 | 38,469 | 14 | 675 | 85.85 | 84.55
:::

The 60,000-image run illustrates a different problem: its 84.58% conditional accuracy accompanies 8,662 records without collected outcomes. Reporting that percentage alone would hide a large processing gap. The dedicated complete-subset run improves coverage but still leaves 675 such records. Its 84.55% all-record accuracy cannot be treated as a clean held-out score because the underlying split contains concept-training sources and its completeness selection differs from the baseline test selection.

Class-wise admission changes the input distribution before scoring. Weighted aggregate metrics describe the selected population but cannot correct that upstream selection; an unrestricted-input claim requires a separately controlled evaluation with complete outcome accounting.

## Anatomy of the 2→7 confusion

In the fixed-threshold construction audit, all 111 final graphs were acyclic. Of the corresponding binary masks, 110 had no hole. One image, mnist_test_2_00412, retained two holes through the skeleton stage but no cycle in the final graph. Thus most missing loops were already absent at the binary stage, whereas one documented case lost that distinction later. The result does not support attributing every error to the same operation.

Figure 1 summarizes the replay comparisons for which both 2_1 and 7_1 were eligible. Their raw-score differences all exceed the configured prior advantage of 2_1; preparation failures are excluded from this plot rather than interpreted as measured similarities.

:::figure figures/replay_score_margin.png
Fig. 1. Raw-score advantage of 7_1 in 106 eligible comparisons from the archived 2→7 replay. The dashed line is the ranking bonus favouring 2_1. Every observed difference lies above it. The five 2_1 preparation failures are excluded; comparison indices indicate sorted order, not independent trials.
:::

The replay then isolates candidate preparation from the initial size filter. Concept 2_2 was initially too complex for 86 of the 111 images. When that filter was disabled, all 111 comparisons with 2_2 still failed the later compatibility check. Therefore prefilter removal alone was insufficient. This finding does not imply that 2_2 received a large optimized edit distance: no eligible GED score was produced for it.

The simpler digit-2 concept 2_1 remained eligible for most images, with five preparation failures in the replay. Concept 7_1 had a higher raw similarity than 2_1 in all 111 comparisons, including those five sentinel-zero cases. The mean raw-score gap was 0.1401 and the smallest gap was 0.0533. The existing complexity prior favours 2_1 over 7_1 by 0.10 log₂(13/9) = 0.0531, just below even that smallest observed raw gap. Consequently, the configured prior did not reverse any of these decisions.

Table 2 gives the representative replay. Its ranking scores are greater than one because they contain the additive complexity term. The richer 2_2 candidate remains excluded after preparation; it is not assigned a meaningful adjusted probability. The replay’s 2_1 similarity of 0.7469 also differs from the earlier detailed trace’s 0.7300. Both retain the wrong winner, but their numeric intermediates are not interchangeable.

:::table Table 2. Candidate comparison for mnist_test_2_00766 in the archived prefilter-disabled replay.
Concept | Complexity | Preparation | Raw similarity | Ranking score
2_2 | 24 | Rejected | — | —
2_1 | 13 | Eligible | 0.7469 | 1.1169
7_1 | 9 | Eligible | 0.8317 | 1.1487
:::

The earlier feature-cost trace explains one way the simpler valid digit-2 candidate is disadvantaged. Three values lie outside its learned bands (Table 3). Each out-of-range feature contributes 1.0 under the archived hard-boundary rule; the complete node costs are slightly larger because they also include other contributions. These are feature costs and node costs, respectively, not two descriptions of the same quantity.

:::table Table 3. Three boundary violations in the earlier detailed trace for concept 2_1.
Matched node / feature | Image value | Concept band | Full node cost
Start point / distance to centroid | 0.558 | [0.69, 1.00] | 1.010
Corner / normalized x | 0.200 | [−0.70, 0.10] | 1.103
Horizontal vector / relative length | 0.306 | [0.43, 1.00] | 1.302
:::

For 7_1, the five matched-node costs in that trace are 0.038, 0.058, 0.224, 0.233 and 0.388. Four additional image nodes can be deleted at 0.25 each. A compact, broadly compatible concept can therefore obtain a favourable score even when the visually intended class is different. The observation implicates both available structure and the cost model; it does not establish that graph construction is the sole cause or that adjusting learned ranges could never help.

Finally, all thirteen stored concepts recognize their own representation with raw similarity 1.0 in the archived self-check. This confirms a limited form of implementation self-consistency. It neither measures separation between different classes nor validates the geometry of the score on unseen handwriting. In particular, a successful self-match does not contradict the systematic 2→7 errors.

## Order sensitivity and finite-sample stabilization

All ten orders produced twelve-node graphs for 2_2, five-node graphs for 7_1 and eleven-node graphs for 8_1. Node counts alone suggest stability, but label-aware comparison gives a different result (Table 4). The 2_2 runs split into an eight-member family and a two-member family. Their 29 within-family pairs have zero GED, while 16 cross-family pairs have GED 1, giving a mean of 0.356. Thus size invariance did not imply labelled-topology invariance.

:::table Table 4. Formation under ten sample orders; the 45 pairs per concept are dependent comparisons.
Concept | Final nodes | Zero-GED pairs | Mean pair GED | Mean-XY-width range
2_2 | 12 | 29/45 | 0.356 | 0.438–0.492
7_1 | 5 | 45/45 | 0.000 | 0.870–1.010
8_1 | 11 | 45/45 | 0.000 | 0.766–1.066
:::

Even the two topology-stable concepts had non-identical coordinate envelopes across orders. A fixed sorted input order can make the formation procedure repeatable on the same cached graphs, but it does not prove insensitivity to a different order, nor remove stochasticity introduced when images are converted into new graphs. Structural and attributed reproducibility are distinct requirements.

The full-cohort trajectories reach their final node and edge counts after 1–37 files (Table 5). These are descriptive size markers, not proofs that the complete graph ceased changing at those steps. For 8_1, the small-change envelope marker occurs at step 5, well before the final size is reached at step 37. For 2_1 and 5_1, the corresponding envelope markers also precede the last size change. A local plateau in mean width is therefore unsafe as an unconditional termination criterion.

:::table Table 5. Full-cohort formation markers from Eq. (4); 4_1 uses the explicitly cleaned 36-file cohort.
Concept | Files n | Size marker | Envelope marker
0_1 | 33 | 11 | 13
1_1 | 33 | 1 | 10
1_3 | 55 | 2 | 5
2_1 | 121 | 23 | 12
2_2 | 55 | 5 | 12
3_1 | 77 | 4 | 13
4_1 | 36 | 2 | 10
4_2 | 65 | 2 | 12
5_1 | 88 | 28 | 11
6_1 | 77 | 12 | 18
7_1 | 99 | 2 | 15
8_1 | 42 | 37 | 5
9_2 | 88 | 16 | 10
:::

The selected 4_1 cohort stabilizes at eight nodes and eight edges from its second file onwards. Its successful trajectory does not establish robustness to mixing incompatible topologies: the open-top source group was removed before this cleaned probe. A method intended to learn directly from heterogeneous handwriting must either represent such variants separately or provide a defined outcome when no supported reduction can reconcile them.

## Sample count and representation size

The sample-count probe reinforces the distinction between a structural skeleton and its attribute envelopes. For 2_2, mean node count across the three draws declines from 16 at N = 2 to approximately 12.7 at N = 5, then to 12 at N = 10 and N = 20. For 7_1, mean coordinate-envelope width increases from approximately 0.33 to 0.48, 0.68 and 0.80 over the same sample counts. The cleaned 4_1 conditions complete, with eight nodes and eight edges for N ≥ 5.

These results show that adding cached examples can remove structural detail while widening the admissible measurements of surviving elements. Neither effect is necessarily beneficial for discrimination: reducing detail can suppress noise or erase a class distinction, while wider bands can accommodate variation or accept another class. The missing downstream-accuracy experiment prevents selecting a preferred N from these descriptive curves.

The stored baseline has 106 concept nodes and 100 edges. By comparison, the later cleaned formation-input exports contain 9,738 nodes and 9,242 edges, giving inventory ratios of 91.9 and 92.4, respectively. These compare different retained evidence sets; they are not a measured lossless compression factor for one input–output run. We report graph-element counts rather than equating range endpoints with learned neural parameters or claiming a corresponding reduction in bytes, compute time or energy consumption.

# Discussion

The central positive result is diagnostic access. The observed 2→7 error can be decomposed into a constructed representation, a failed rich candidate, a surviving simpler alternative, explicit feature-boundary penalties and a ranking decision. This is more informative than a confusion matrix alone because each proposed remedy can be attached to a particular stage. However, access to the trace does not itself establish that its representation or score is appropriate.

The ablation supports a narrow conclusion: removing the initial size filter did not rescue 2_2, and the configured complexity prior did not overturn a raw-score error. It does not show that every alternative ranking coefficient, feature weighting, learned range, graph construction or concept partition would fail. The raw-gap calculation identifies the limitation of the existing prior; it is not a proof that a larger prior would improve accuracy without new false positives. A defensible follow-up must evaluate both corrected and newly introduced errors across classes.

Likewise, finite-sample stabilization is not an attractor theorem. The two labelled-graph families of 2_2 contradict universal order invariance within the tested conditions. This concerns the implementation, not a disproof of the conditional formal results in [16]. Envelope variation persists even when labelled topology is unchanged, and a local width plateau can precede further structural change. Stable concept learning therefore requires separate tests of structural equivalence, attribute stability and predictive behaviour under new sample orders and independently constructed graphs.

The evidence has four principal limitations. First, morphology-based selection, including the explicit 4_1 exclusion, limits the input population being described. Second, augmented variants and pairwise comparisons are dependent observations. Third, a dirty baseline worktree and differing replay versions restrict exact computational reproducibility. Fourth, missing outcomes in larger runs confound classifier quality with processing coverage. None of these limitations is corrected by increasing the number of reported decimal places or by treating all cached files as independent examples.

The results suggest a sequence of controlled tests rather than a claim of a completed solution. Topology-preserving construction should be evaluated with paired intermediate graphs. Cost-model changes should retain candidate eligibility records and measure cross-class effects. Heterogeneous subclasses should be tested without silently excluding incompatible shapes. Any early-stopping rule should combine structural and attribute criteria and then be assessed on prediction quality. These experiments would test whether the observed stability is useful for recognition, not merely whether the stored graph becomes small.

Within this scope, the non-backpropagation design offers an inspectable learning and decision process with a small retained concept inventory. The available evidence does not establish superior data efficiency, lower energy use, immunity to explanation attacks, or semantic equivalence to human digit concepts. Keeping these claims separate preserves the practical value of the trace while avoiding conclusions that the experiments were not designed to support.

# Conclusions

The audited classifier exposes a concrete interaction between structural eligibility and asymmetric feature costs in its dominant 2→7 confusion. All 111 richer digit-2 comparisons remained ineligible after removal of the initial complexity filter, while the simpler digit-2 alternative lost the raw-score comparison in the archived replay. An explicit decision trace therefore helps identify where an error arises, but does not guarantee that the representation or ranking is discriminative.

Formation probes provide evidence of early size stabilization under selected conditions, not universal order-invariant concepts. Two tested concepts retained labelled topology across ten orders; the third formed two families, and coordinate envelopes varied even with unchanged topology. Evaluation accounting further reduces the selected baseline from 91.13% on completed records to 90.90% on all admitted records, while unrestricted test inputs produce 82.21% all-record accuracy. Together, these findings define a reproducible audit logic and the empirical limits that subsequent claims of stable structural learning must address.

:::ai
Declaration on Generative AI. OpenAI Codex was used for proofreading and literature search.
:::

# References

1. Rudin, C., Chen, C., Chen, Z., Huang, H., Semenova, L., Zhong, C.: Interpretable machine learning: Fundamental principles and 10 grand challenges. Statistics Surveys 16, 1–85 (2022). https://doi.org/10.1214/21-SS133
2. Baniecki, H., Biecek, P.: Adversarial attacks and defenses in explainable artificial intelligence: A survey. Information Fusion 107, 102303 (2024). https://doi.org/10.1016/j.inffus.2024.102303
3. García-Cuesta, E., Manrique, D., Ionescu, R.C.: Interpretable deep prototype-based neural networks: Can a 1 look like a 0? Electronics 14(18), 3584 (2025). https://doi.org/10.3390/electronics14183584
4. Forest, F., Rombach, K., Fink, O.: Interpretable prognostics with concept bottleneck models. Information Fusion 124, 103427 (2025). https://doi.org/10.1016/j.inffus.2025.103427
5. Gan, J., Chen, Y., Hu, B., Leng, J., Wang, W., Gao, X.: Characters as graphs: Interpretable handwritten Chinese character recognition via Pyramid Graph Transformer. Pattern Recognition 137, 109317 (2023). https://doi.org/10.1016/j.patcog.2023.109317
6. Han, K., Wang, Y., Guo, J., Tang, Y., Wu, E.: Vision GNN: An image is worth graph of nodes. Advances in Neural Information Processing Systems 35, 8291–8303 (2022). https://doi.org/10.52202/068431-0603
7. Bunke, H., Allermann, G.: Inexact graph matching for structural pattern recognition. Pattern Recognition Letters 1(4), 245–253 (1983). https://doi.org/10.1016/0167-8655(83)90033-8
8. Wang, R., Zhang, T., Yu, T., Yan, J., Yang, X.: Combinatorial learning of graph edit distance via dynamic embedding. In: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pp. 5241–5250 (2021). https://doi.org/10.1109/CVPR46437.2021.00520
9. Piao, C., Xu, T., Sun, X., Rong, Y., Zhao, K., Cheng, H.: Computing graph edit distance via neural graph matching. Proceedings of the VLDB Endowment 16(8), 1817–1829 (2023). https://doi.org/10.14778/3594512.3594514
10. Tang, J., Zhao, X., Kong, L., Zhou, X., Li, J.: Fused Gromov–Wasserstein alignment for graph edit distance computation and beyond. Proceedings of the VLDB Endowment 18(10), 3641–3654 (2025). https://doi.org/10.14778/3748191.3748221
11. Hinton, G.: The Forward-Forward algorithm: Some preliminary investigations. arXiv:2212.13345 (2022). https://doi.org/10.48550/arXiv.2212.13345
12. Nawaz, U., Anees-ur-Rahaman, M., Saeed, Z.: A review of neuro-symbolic AI integrating reasoning and learning for advanced cognitive systems. Intelligent Systems with Applications 26, 200541 (2025). https://doi.org/10.1016/j.iswa.2025.200541
13. Hospedales, T., Antoniou, A., Micaelli, P., Storkey, A.: Meta-learning in neural networks: A survey. IEEE Transactions on Pattern Analysis and Machine Intelligence 44(9), 5149–5169 (2022). https://doi.org/10.1109/TPAMI.2021.3079209
14. Song, Y., Wang, T., Cai, P., Mondal, S.K., Sahoo, J.P.: A comprehensive survey of few-shot learning: Evolution, applications, challenges, and opportunities. ACM Computing Surveys 55(13s), 1–40 (2023). https://doi.org/10.1145/3582688
15. Parzhyn, Y., Lapin, M., Bokhan, K.: A new approach to building energy models of neural networks. Advanced Information Systems 9(4), 100–119 (2025). https://doi.org/10.20998/2522-9052.2025.4.13
16. Lapin, M., Parzhyn, Y., Bokhan, K., Perevoznyk, K., Aleksandrova, T.: Invariant structural learning: Concept formation as hypergraph attractor dynamics. Innovative Technologies and Scientific Solutions for Industries 2(36), 70–94 (2026). https://doi.org/10.30837/2522-9818.2026.2.070
17. Zhang, T.Y., Suen, C.Y.: A fast parallel algorithm for thinning digital patterns. Communications of the ACM 27(3), 236–239 (1984). https://doi.org/10.1145/357994.358023
18. Fritzke, B.: A growing neural gas network learns topologies. In: Advances in Neural Information Processing Systems 7, pp. 625–632. MIT Press (1995). https://proceedings.neurips.cc/paper/1994/hash/d56b9fc4b0f1be8871f5e1c40c0067e7-Abstract.html
19. Douglas, D.H., Peucker, T.K.: Algorithms for the reduction of the number of points required to represent a digitized line or its caricature. Cartographica 10(2), 112–122 (1973). https://doi.org/10.3138/FM57-6770-U75U-7727
20. LeCun, Y., Bottou, L., Bengio, Y., Haffner, P.: Gradient-based learning applied to document recognition. Proceedings of the IEEE 86(11), 2278–2324 (1998). https://doi.org/10.1109/5.726791
