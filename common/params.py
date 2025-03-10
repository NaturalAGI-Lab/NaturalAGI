from dataclasses import dataclass

# TODO add to the skel function
# @dataclass
# class SkeletonizationParams:
#     min_skeleton_threshold: int
#     threshold_step: int
#     simplification_epsilon: int
#     # Neural Gas parameters
#     N: int = 50
#     maxit: int = 100
#     L: int = 100
#     epsilon_b: float = 0.2
#     epsilon_n: float = 0.01
#     alpha: float = 0.5
#     delta: float = 0.995
#     T: int = 50
#     cnr_threshold: float = 0


@dataclass
class ClassificationParams:
    feature_weight: float
    structural_weight: float
    ged_timeout: float
    min_structural_similarity: float = 0.3
