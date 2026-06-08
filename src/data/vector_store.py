import json
import sys
import platform
import numpy as np
from pathlib import Path
from src.infrastructure.config import Config
from src.infrastructure.logger import logger

class LocalVectorDB:
    """A pure-Python drop-in replacement for ChromaDB collection to avoid binary DLL crashes."""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = {}
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load local database: {e}")
                self.data = {}

    def persist(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist local database: {e}")

    def add(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]):
        for idx, item_id in enumerate(ids):
            self.data[item_id] = {
                "vector": embeddings[idx],
                "document": documents[idx],
                "metadata": metadatas[idx]
            }
        self.persist()

    def delete(self, where: dict = None):
        if not where:
            return
        keys_to_delete = []
        for item_id, item in self.data.items():
            match = True
            for key, val in where.items():
                if item.get("metadata", {}).get(key) != val:
                    match = False
                    break
            if match:
                keys_to_delete.append(item_id)
        for key in keys_to_delete:
            del self.data[key]
        if keys_to_delete:
            self.persist()

    def get(self, where: dict = None) -> dict:
        result_ids = []
        result_documents = []
        result_metadatas = []
        for item_id, item in self.data.items():
            match = True
            if where:
                for key, val in where.items():
                    if item.get("metadata", {}).get(key) != val:
                        match = False
                        break
            if match:
                result_ids.append(item_id)
                result_documents.append(item.get("document"))
                result_metadatas.append(item.get("metadata"))
        return {
            "ids": result_ids,
            "documents": result_documents,
            "metadatas": result_metadatas
        }

    def query(self, query_embeddings: list[list[float]], n_results: int = 3) -> dict:
        if not self.data or not query_embeddings:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        query_vector = np.array(query_embeddings[0])
        item_ids = list(self.data.keys())
        vectors = np.array([self.data[iid]["vector"] for iid in item_ids])
        
        # Cosine similarity (dot product for normalized vectors)
        similarities = np.dot(vectors, query_vector)
        
        # Apply link penalty to similarities
        import re
        adjusted_similarities = []
        for idx, iid in enumerate(item_ids):
            doc = self.data[iid]["document"]
            score = similarities[idx]
            
            # Count markdown links [label](url)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', doc)
            total_len = len(doc)
            link_len = sum(len(label) + len(url) + 4 for label, url in links)
            link_ratio = link_len / total_len if total_len > 0 else 0.0
            
            if link_ratio > 0.40 or len(links) > 4:
                penalty = 0.2
            else:
                penalty = 1.0
            adjusted_similarities.append(score * penalty)
            
        distances = 1.0 - np.array(adjusted_similarities)
        
        sorted_indices = np.argsort(distances)[:n_results]
        
        ret_ids = [item_ids[idx] for idx in sorted_indices]
        ret_documents = [self.data[item_ids[idx]]["document"] for idx in sorted_indices]
        ret_metadatas = [self.data[item_ids[idx]]["metadata"] for idx in sorted_indices]
        ret_distances = [float(distances[idx]) for idx in sorted_indices]
        
        return {
            "ids": [ret_ids],
            "documents": [ret_documents],
            "metadatas": [ret_metadatas],
            "distances": [ret_distances]
        }

class VectorStore:
    """Manages the persistent vector store using ChromaDB or pure-Python LocalVectorDB fallback."""
    _instance = None

    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            self.persist_dir = str(Config.VECTOR_DB_DIR)
        else:
            self.persist_dir = persist_dir
            
        # Ensure persistent database directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        self.use_fallback = False
        
        # Check for Python 3.14+ on Windows where PyTorch & ChromaDB C++ extensions fail to load/initialize
        if platform.system() == "Windows" and sys.version_info >= (3, 14):
            logger.warning(
                "Windows with Python 3.14+ detected. Bypassing SentenceTransformer and ChromaDB "
                "to prevent DLL initialization crash. Gracefully falling back to scikit-learn HashingVectorizer "
                "and pure-Python LocalVectorDB storage."
            )
            self.use_fallback = True
        
        if self.use_fallback:
            from sklearn.feature_extraction.text import HashingVectorizer
            self.model = HashingVectorizer(n_features=384, norm='l2', alternate_sign=False)
            self.collection = LocalVectorDB(Path(self.persist_dir) / "local_db.json")
        else:
            try:
                # Load package dynamically
                # pyrefly: ignore [missing-import]
                import chromadb
                logger.info(f"Initializing persistent ChromaDB client at: {self.persist_dir}")
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                
                logger.info("Attempting to load sentence-transformer embedding model BAAI/bge-small-en-v1.5...")
                # pyrefly: ignore [missing-import]
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
                logger.info("Successfully loaded sentence-transformer BGE model.")
                
                # Create or get collection
                self.collection = self.client.get_or_create_collection(
                    name="mutual_funds",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                logger.warning(
                    f"SentenceTransformer or ChromaDB failed to load ({e}). "
                    "Gracefully falling back to scikit-learn HashingVectorizer (384 dimensions) and LocalVectorDB."
                )
                self.use_fallback = True
                from sklearn.feature_extraction.text import HashingVectorizer
                self.model = HashingVectorizer(n_features=384, norm='l2', alternate_sign=False)
                self.collection = LocalVectorDB(Path(self.persist_dir) / "local_db.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def query(cls, query_text: str, top_k: int = 3) -> list[dict]:
        """Class method helper for quick querying (verifies matches)."""
        return cls.get_instance().query_instance(query_text, top_k)

    def _embed(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        """Generates embeddings using the active backend (BGE or HashingVectorizer)."""
        if self.use_fallback:
            vectors = self.model.transform(texts).toarray()
            return [v.tolist() for v in vectors]
        else:
            if is_query:
                prefix = "Represent this sentence for searching relevant passages: "
                texts = [prefix + t for t in texts]
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return [e.tolist() for e in embeddings]

    def query_instance(self, query_text: str, top_k: int = 3) -> list[dict]:
        """Queries the vector collection for similarity matches."""
        if self.use_fallback and self.collection.data:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.model = TfidfVectorizer(norm='l2', sublinear_tf=True, stop_words='english')
            documents = [item["document"] for item in self.collection.data.values()]
            vectors = self.model.fit_transform(documents).toarray()
            
            # Update the vectors in memory
            item_ids = list(self.collection.data.keys())
            for idx, iid in enumerate(item_ids):
                self.collection.data[iid]["vector"] = vectors[idx].tolist()
                
            query_vector = self.model.transform([query_text]).toarray()[0].tolist()
        else:
            query_vector = self._embed([query_text], is_query=True)[0]
            
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )
        
        # Reformat results into a list of dictionaries
        formatted_results = []
        if results and 'documents' in results and results['documents']:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else []
            distances = results['distances'][0] if 'distances' in results and results['distances'] else []
            ids = results['ids'][0] if 'ids' in results and results['ids'] else []
            
            for i in range(len(documents)):
                formatted_results.append({
                    "id": ids[i] if i < len(ids) else f"chunk_{i}",
                    "document": documents[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0
                })
        return formatted_results

    def add_document_chunks(self, url: str, scheme_name: str, title: str, chunks: list[str]):
        """Saves chunks for a document after purging previous index for the same URL."""
        if not chunks:
            return
            
        # Delete existing chunks for this URL to avoid duplicates/orphans
        try:
            self.collection.delete(where={"url": url})
            logger.info(f"Purged old index for: {url}")
        except Exception as e:
            logger.debug(f"No existing index records to delete for {url}: {e}")
            
        # Generate embeddings
        embeddings_list = self._embed(chunks, is_query=False)
        
        # Prepare metadata and IDs
        metadatas = []
        ids = []
        for idx, chunk in enumerate(chunks):
            # Create a clean url-based unique ID
            clean_url = url.rstrip("/").split("/")[-1]
            ids.append(f"{clean_url}_{idx}")
            metadatas.append({
                "url": url,
                "scheme_name": scheme_name,
                "title": title,
                "chunk_index": idx
            })
            
        # Insert into collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=chunks,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks for {scheme_name}")

def build_index():
    """Reads processed JSON files and builds/populates the local Chroma index."""
    logger.info("Starting offline Vector DB indexing process...")
    store = VectorStore.get_instance()
    
    processed_dir = Config.PROCESSED_DATA_DIR
    if not processed_dir.exists():
        logger.error(f"Processed data directory {processed_dir} does not exist.")
        return
        
    json_files = list(processed_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} processed scheme files to index.")
    
    total_chunks = 0
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            url = data.get("url", "")
            scheme_name = data.get("scheme_name", "")
            title = data.get("title", "")
            chunks = data.get("chunks", [])
            
            if not url or not chunks:
                logger.warning(f"Skipping index for {json_file.name}: missing url or chunks.")
                continue
                
            store.add_document_chunks(url, scheme_name, title, chunks)
            total_chunks += len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to index scheme in file {json_file.name}: {e}")
            
    logger.info(f"Vector database indexing pipeline complete. Total indexed chunks: {total_chunks}")

if __name__ == "__main__":
    build_index()
