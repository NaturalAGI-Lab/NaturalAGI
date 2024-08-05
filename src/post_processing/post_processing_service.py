from post_processing_repository import PostProcessingRepository


class PostProcessingService:
    def __init__(self, post_processing_repository: PostProcessingRepository):
        self.post_processing_repository = post_processing_repository

    def process(self, session_id: str) -> None:
        # self.post_processing_repository.merge_nodes_location(
        #     ["VectorLocation", "VectorLength", "VectorOrientation"]
        # )
        self.post_processing_repository.stabilize_structures(session_id)
