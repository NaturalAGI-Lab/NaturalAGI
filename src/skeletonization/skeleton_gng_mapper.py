import logging
import numpy as np
import networkx as nx
from opentelemetry import trace
from skan import Skeleton, summarize
from skimage.morphology import closing, square, remove_small_objects, skeletonize
import gng
from settings import Settings
from network_simplification import NetworkSimplification
from converter import Converter
from normalization import normalize_graph
from common import timed

_tracer = trace.get_tracer("skeletonization")


class SkeletonGNGMapper:
    def __init__(
        self,
        settings: Settings,
        skeletonization_threshold: int = None,
        simplification_epsilon: float = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.min_threshold = 20
        self.threshold_step = 5
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
            attempt_number = 0

            while current_threshold >= self.min_threshold:
                try:
                    with _tracer.start_as_current_span(
                        "skeletonization.attempt"
                    ) as attempt_span:
                        attempt_span.set_attribute("threshold", current_threshold)
                        attempt_span.set_attribute("attempt", attempt_number)

                        skeleton = self.skeletonize(image, current_threshold)
                        points = self.skeleton_to_points(skeleton)
                        net = self.fit_gng(points)
                        simplified = self._simplify_network(net)
                        graph = self._convert_to_networkx(simplified)
                        graph = self._normalize(graph)

                        connected = nx.is_connected(graph)
                        attempt_span.set_attribute("connected", connected)

                        if connected:
                            return graph, current_threshold

                    current_threshold -= self.threshold_step
                    attempt_number += 1

                except Exception as e:
                    self.logger.error(
                        f"Error processing with threshold {current_threshold}: {str(e)}"
                    )
                    current_threshold -= self.threshold_step
                    attempt_number += 1
                    continue

            raise Exception("Could not create connected graph with any threshold")

        except Exception as e:
            self.logger.error(f"Failed to process image: {str(e)}")
            raise

    @_tracer.start_as_current_span("skeletonization.binary_image")
    @timed(label="binary_image")
    def binary_image(self, image, threshold):
        span = trace.get_current_span()
        span.set_attribute("threshold", threshold)
        binary = image > threshold
        binary = remove_small_objects(binary, min_size=10)
        binary = closing(binary, square(3))
        return binary

    @_tracer.start_as_current_span("skeletonization.skeletonize")
    @timed(label="skeletonize")
    def skeletonize(self, image, threshold):
        span = trace.get_current_span()
        span.set_attribute("threshold", threshold)
        binary = self.binary_image(image, threshold)
        skeleton = skeletonize(binary)
        sk = Skeleton(skeleton, source_image=binary)
        summary = summarize(sk, separator="_")

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

        span.set_attribute("pruned_branches", len(short_branches))
        sk = sk.prune_paths(short_branches)
        return sk.skeleton_image

    @_tracer.start_as_current_span("skeletonization.skeleton_to_points")
    @timed(label="skeleton_to_points")
    def skeleton_to_points(self, skeleton: np.ndarray):
        # argwhere returns [row, col] = [y, x]; reverse to get [x, y]
        result = np.argwhere(skeleton > 0)[:, ::-1]
        span = trace.get_current_span()
        span.set_attribute("point_count", len(result))
        return result

    @_tracer.start_as_current_span("skeletonization.fit_gng")
    @timed(label="fit_gng")
    def fit_gng(self, points):
        span = trace.get_current_span()
        span.set_attribute("max_neurons", self.settings.N)
        span.set_attribute("iterations", self.settings.maxit)
        span.set_attribute("input_points", len(points))
        net = gng.fit(points, self.settings)
        neuron_count = int(np.where(np.sum(net.C, axis=0) > 0)[0].size)
        span.set_attribute("neuron_count", neuron_count)
        return net

    @_tracer.start_as_current_span("skeletonization.simplify_network")
    def _simplify_network(self, net):
        span = trace.get_current_span()
        span.set_attribute("epsilon", float(self.simplification_epsilon))
        simplified = NetworkSimplification.simplify_network(
            net, self.simplification_epsilon
        )
        span.set_attribute("segment_count", len(simplified))
        return simplified

    @_tracer.start_as_current_span("skeletonization.convert_to_networkx")
    def _convert_to_networkx(self, simplified_network):
        graph = Converter.convert_simplified_network_to_networkx(simplified_network)
        span = trace.get_current_span()
        span.set_attribute("node_count", graph.number_of_nodes())
        span.set_attribute("edge_count", graph.number_of_edges())
        return graph

    @_tracer.start_as_current_span("skeletonization.normalize")
    def _normalize(self, graph: nx.Graph) -> nx.Graph:
        graph = normalize_graph(graph)
        span = trace.get_current_span()
        span.set_attribute("node_count", graph.number_of_nodes())
        return graph
