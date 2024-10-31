from grakel.kernels import Kernel
from collections import defaultdict
from grakel import Graph

class WeightedWeisfeilerLehman(Kernel):
    """Weisfeiler-Lehman kernel that accounts for node weights."""
    def __init__(self, n_iter=5, normalize=False):
        super().__init__(normalize=normalize)
        self.n_iter = n_iter

    def initialize(self):
        self.label_lookup = {}
        self.X = None

    def parse_input(self, X):
        if not isinstance(X, list):
            raise TypeError('input must be a list of graphs')

        out = []
        for idx, graph in enumerate(X):
            if not isinstance(graph, Graph):
                raise TypeError('Each element of X must be a grakel.Graph instance')
            out.append(graph)
        return out

    def fit_transform(self, X):
        self.initialize()
        X = self.parse_input(X)
        feature_dicts = [self._compute_wl_features(g) for g in X]

        # Build the feature vectors
        all_features = set()
        for fd in feature_dicts:
            all_features.update(fd.keys())
        all_features = sorted(all_features)
        feature_vectors = []
        for fd in feature_dicts:
            vector = [fd.get(f, 0) for f in all_features]
            feature_vectors.append(vector)

        # Compute the weighted kernel matrix
        import numpy as np
        K = np.dot(feature_vectors, np.transpose(feature_vectors))

        if self.normalize:
            K = self._normalize(K)
        return K

    def _compute_wl_features(self, g):
        node_labels = g.get_labels(purpose="any")
        node_weights = g.get_labels(purpose="weight")
        adjacency_dict = g.get_adjacency_list()
        label_lookup = {}
        label_histogram = defaultdict(float)  # Use float for weighted counts

        # Initialize labels
        labels = {}
        for node in g.nodes:
            labels[node] = node_labels[node]

        for iteration in range(self.n_iter):
            new_labels = {}
            for node in g.nodes:
                # Get current label
                current_label = labels[node]

                # Get neighbor labels
                neighbor_labels = [labels[neighbor] for neighbor in adjacency_dict[node]]

                # Combine labels
                all_labels = [current_label] + sorted(neighbor_labels)
                combined_label = '_'.join(all_labels)

                # Map combined labels to a unique label
                if combined_label not in label_lookup:
                    label_lookup[combined_label] = str(len(label_lookup) + 1)
                new_label = label_lookup[combined_label]
                new_labels[node] = new_label

                # Update histogram with node weight
                weight = node_weights[node]
                label_histogram[new_label] += weight

            labels = new_labels

        return dict(label_histogram)

    def _normalize(self, K):
        import numpy as np
        diagonal = np.sqrt(np.diag(K))
        K_normalized = K / (diagonal[:, None] * diagonal[None, :])
        return K_normalized
