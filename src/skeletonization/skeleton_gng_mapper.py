import logging
import numpy as np
import networkx as nx
from skan import Skeleton, summarize
from skimage.morphology import closing, square, remove_small_objects, skeletonize
import gng
from settings import Settings
from network_simplification import NetworkSimplification
from converter import Converter
from normalization import normalize_graph
from common import timed


class SkeletonGNGMapper:
    def __init__(
        self,
        settings: Settings,
        skeletonization_threshold: int = None,
        simplification_epsilon: float = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.min_threshold = 20  # Minimum threshold value
        self.threshold_step = 5  # Step to decrease threshold
        self.skeletonization_threshold = (
            skeletonization_threshold or self.settings.skeletonization_threshold
        )
        self.simplification_epsilon = (
            simplification_epsilon or self.settings.simplification_epsilon
        )

    @timed(label="process_image")
    def process_image(self, image):
        try:
            self.logger.info(
                f"Processing image with skeletonization threshold: {self.skeletonization_threshold} "
                f"and simplification epsilon: {self.simplification_epsilon}"
            )
            current_threshold = self.skeletonization_threshold

            while current_threshold >= self.min_threshold:
                try:
                    skeleton = self.skeletonize(image, threshold=current_threshold)
                    self.logger.debug(
                        f"Skeleton created with threshold {current_threshold}"
                    )

                    points = self.skeleton_to_points(skeleton)
                    self.logger.debug(f"Extracted {len(points)} points from skeleton")

                    net = self.fit_gng(points)
                    self.logger.debug("GNG network fitted")

                    simplified_network = NetworkSimplification.simplify_network(
                        net, self.simplification_epsilon
                    )
                    self.logger.debug(
                        f"Network simplified into {len(simplified_network)} segments"
                    )

                    graph = Converter.convert_simplified_network_to_networkx(
                        simplified_network
                    )
                    graph = normalize_graph(graph)
                    self.logger.debug(
                        f"Created graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges"
                    )

                    if nx.is_connected(graph):
                        return graph, current_threshold

                    current_threshold -= self.threshold_step

                except Exception as e:
                    self.logger.error(
                        f"Error processing with threshold {current_threshold}: {str(e)}"
                    )
                    current_threshold -= self.threshold_step
                    continue

            raise Exception("Could not create connected graph with any threshold")

        except Exception as e:
            self.logger.error(f"Failed to process image: {str(e)}")
            raise

    @timed(label="binary_image")
    def binary_image(self, image, threshold):
        binary = image > threshold
        binary = remove_small_objects(binary, min_size=10)
        binary = closing(binary, square(3))
        return binary

    @timed(label="skeletonize")
    def skeletonize(self, image, threshold):
        binary = self.binary_image(image, threshold)
        skeleton = skeletonize(binary)
        sk = Skeleton(skeleton, source_image=binary)
        summary = summarize(sk, separator="_")  # use '_' for nicer column names

        # Adaptive pruning: remove branches shorter than X% of total skeleton length
        PRUNE_PERCENT = 0.08  # 5% of total skeleton length
        MIN_ABSOLUTE = 5  # minimum threshold in pixels (safety floor)

        total_length = summary["branch_distance"].sum()
        adaptive_threshold = max(total_length * PRUNE_PERCENT, MIN_ABSOLUTE)

        self.logger.debug(
            f"Adaptive pruning: total_length={total_length:.1f}, "
            f"threshold={adaptive_threshold:.1f}px ({PRUNE_PERCENT*100}%)"
        )

        # junction-to-endpoint branches shorter than adaptive threshold
        short_branches = summary[
            (summary.branch_type == 1)  # 1 = junction → endpoint
            & (summary.branch_distance < adaptive_threshold)
        ].index  # <- the row index *is* the branch id

        sk = sk.prune_paths(short_branches)  # same as delete_paths(...) in ≤0.11
        return sk.skeleton_image

    @timed(label="skeleton_to_points")
    def skeleton_to_points(self, skeleton: np.ndarray):
        points = []
        h, w = skeleton.shape
        for y in range(h):
            for x in range(w):
                if skeleton[y, x] > 0:
                    points.append([x, y])
        return np.array(points)

    @timed(label="fit_gng")
    def fit_gng(self, points):
        return gng.fit(points, self.settings)
