import logging
import numpy as np
import networkx as nx
from skan import Skeleton, summarize
from skimage.morphology import remove_small_objects, skeletonize
from skimage.filters import threshold_otsu
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
                f"Processing image with Otsu threshold (improved) "
                f"and simplification epsilon: {self.simplification_epsilon}"
            )

            # Use Otsu threshold (improved skeletonization)
            skeleton = self.skeletonize(image, threshold=None)
            self.logger.debug("Skeleton created with Otsu threshold")

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
                return graph, threshold_otsu(image)

            raise Exception("Could not create connected graph")

        except Exception as e:
            self.logger.error(f"Failed to process image: {str(e)}")
            raise

    @timed(label="binary_image")
    def binary_image(self, image, threshold=None):
        # Use Otsu threshold if not specified (improved skeletonization)
        if threshold is None:
            threshold = threshold_otsu(image)
            self.logger.info(f"Using Otsu threshold: {threshold}")

        binary = image > threshold
        binary = remove_small_objects(binary, min_size=10)
        # NO closing - it destroys thin structures and loops
        return binary

    @timed(label="skeletonize")
    def skeletonize(self, image, threshold):
        binary = self.binary_image(image, threshold)
        skeleton = skeletonize(binary)
        MIN_BRANCH_LEN = 7  # pixels; adjust to taste
        sk = Skeleton(skeleton, source_image=binary)
        summary = summarize(sk, separator="_")  # use '_' for nicer column names

        # junction-to-endpoint branches shorter than MIN_BRANCH_LEN
        short_branches = summary[
            (summary.branch_type == 1)  # 1 = junction → endpoint
            & (summary.branch_distance < MIN_BRANCH_LEN)
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
