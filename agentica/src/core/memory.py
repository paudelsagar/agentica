import os
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.core.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """
    Manages long-term memory using ChromaDB and Google Embeddings.
    """

    def __init__(self, collection_name: str = "agent_memory"):
        self.collection_name = collection_name
        self.embeddings = None
        self.vector_store = None

        # Persist directory
        self.persist_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "chroma_db",
        )

    def _ensure_initialized(self) -> bool:
        if self.vector_store is not None:
            return True
        if not os.getenv("GOOGLE_API_KEY"):
            logger.warning(
                "GOOGLE_API_KEY not found. Memory features will be disabled."
            )
            return False

        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001"
            )
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            return True
        except Exception as e:
            logger.error("failed_to_initialize_chroma", error=str(e))
            self.vector_store = None
            return False

    def add_memory(self, text: str, metadata: Optional[dict] = None) -> str:
        """
        Adds a text to the memory.
        """
        if not self._ensure_initialized():
            return "Memory unavailable. GOOGLE_API_KEY required."

        logger.info("adding_memory", text_preview=text[:50])
        try:
            doc = Document(page_content=text, metadata=metadata or {})
            ids = self.vector_store.add_documents([doc])
            return f"Memory saved with ID: {ids[0]}"
        except Exception as e:
            logger.error("add_memory_failed", error=str(e))
            return f"Failed to save memory: {str(e)}"

    def search_memory(self, query: str, k: int = 3) -> List[str]:
        """
        Retrieves relevant memories.
        """
        if not self.vector_store:
            return []

        logger.info("searching_memory", query=query)
        try:
            results = self.vector_store.similarity_search(query, k=k)
            logger.info("memory_search_results", count=len(results))
            return [doc.page_content for doc in results]
        except Exception as e:
            logger.error("search_memory_failed", error=str(e))
            return []
