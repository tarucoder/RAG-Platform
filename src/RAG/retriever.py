from src.infrastructure.config import Config
from src.infrastructure.logger import logger
from src.data.vector_store import VectorStore

class Retriever:
    """Retrieves context chunks from the persistent VectorStore matching user query, applying similarity thresholding."""
    
    def __init__(self):
        self.vector_store = VectorStore.get_instance()
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        self.top_k = Config.TOP_K_CONTEXT
        logger.info(
            f"Initialized Retriever with similarity_threshold={self.similarity_threshold} "
            f"and top_k={self.top_k}."
        )

    def retrieve(self, query: str, top_k: int = None) -> list[dict]:
        """Queries VectorStore and filters results by cosine similarity threshold.
        
        Note:
        - ChromaDB/LocalVectorDB returns cosine distance.
        - Similarity = 1.0 - Cosine Distance.
        - Distance threshold = 1.0 - Similarity Threshold.
        - Results with Distance > (1.0 - Similarity Threshold) are filtered out as out-of-domain.
        """
        k = top_k if top_k is not None else self.top_k
        logger.info(f"Retrieving top {k} contexts for query: '{query}'")
        
        raw_results = self.vector_store.query_instance(query, top_k=k)
        
        # Max distance allowed
        max_allowed_distance = 1.0 - self.similarity_threshold
        
        filtered_results = []
        for result in raw_results:
            distance = result.get("distance", 1.0)
            similarity = 1.0 - distance
            
            if distance <= max_allowed_distance:
                filtered_results.append(result)
                logger.debug(f"Pass: chunk {result['id']} similarity={similarity:.4f} (distance={distance:.4f})")
            else:
                logger.debug(f"Skip: chunk {result['id']} similarity={similarity:.4f} below threshold {self.similarity_threshold}")
                
        logger.info(f"Retrieved {len(filtered_results)} of {len(raw_results)} chunks above similarity threshold.")
        return filtered_results
