import sys
from pathlib import Path

from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_huggingface import HuggingFaceEndpointEmbeddings

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: HuggingFaceEndpointEmbeddings | None = None
        self.config: EmbeddingConfig = config

    def _get_url(self) -> str:
        # noinspection HttpUrlsUsage
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> None:
        self.client = HuggingFaceEndpointEmbeddings(model=self.config.model)
        self.client.client = InferenceClient(base_url=self._get_url())
        self.client.async_client = AsyncInferenceClient(base_url=self._get_url())


# singleton
embedding_client_manager = EmbeddingClientManager(app_config.embedding)


if __name__ == "__main__":
    print("Initializing embedding client...")
    test_text = "What is Deep Learning?"

    try:
        embedding_client_manager.init()
        if embedding_client_manager.client is None:
            raise RuntimeError("Embedding client was not initialized.")

        vector_result = embedding_client_manager.client.embed_query(test_text)
        print("Embedding test succeeded.")
        print(f"Service URL: {embedding_client_manager._get_url()}")
        print(f"Model: {embedding_client_manager.config.model}")
        print(f"Vector dimensions: {len(vector_result)}")
        print(f"Vector preview: {vector_result[:5]}")
    except Exception as exc:
        print(f"Embedding test failed. Please check service: {embedding_client_manager._get_url()}")
        print(f"Error: {exc}")
