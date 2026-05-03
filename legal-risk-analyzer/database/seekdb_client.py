from typing import List, Optional

from pyseekdb import Client, EmbeddingFunction
from openai import OpenAI

from config import Config


Documents = List[str]
Embeddings = List[List[float]]


class OpenAIEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    使用 OpenAI 兼容 API 的 Embedding 函数
    支持通义千问、DeepSeek 等 OpenAI 兼容的 Embedding API
    """

    def __init__(self):
        config = Config.get_embedding_config()
        self.model_name = config.model_name
        self.api_key = config.api_key
        self.base_url = config.base_url
        self._dimension = config.dims
        self._client = None

        if not self.api_key:
            raise ValueError("Embedding API key is required")

    def _ensure_client(self):
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def dimension(self) -> int:
        return self._dimension

    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]

        if not input:
            return []

        self._ensure_client()
        response = self._client.embeddings.create(model=self.model_name, input=input)

        return [item.embedding for item in response.data]


_client_cache = {}


def get_seekdb_client() -> Client:
    """
    获取 SeekDB 客户端
    支持嵌入式模式和服务器模式
    """
    config = Config.get_seekdb_config()
    cache_key = (config.dir, config.name)

    if cache_key not in _client_cache:
        if config.host:
            print(f"Connecting to SeekDB server: {config.host}:{config.port}")
            _client_cache[cache_key] = Client(
                host=config.host,
                port=config.port,
                database=config.name,
                user=config.user,
                password=config.password,
            )
        else:
            print(f"Connecting to embedded SeekDB: path={config.dir}, database={config.name}")
            _client_cache[cache_key] = Client(path=config.dir, database=config.name)
        print("SeekDB client connected successfully")

    return _client_cache[cache_key]


def get_embedding_function() -> OpenAIEmbeddingFunction:
    """获取 Embedding 函数"""
    return OpenAIEmbeddingFunction()


def get_or_create_legal_collection(client: Client, collection_name: str, drop_if_exists: bool = False):
    """
    获取或创建法律文档 Collection

    Args:
        client: SeekDB 客户端
        collection_name: Collection 名称
        drop_if_exists: 是否删除已存在的 Collection

    Returns:
        Collection 对象
    """
    embedding_function = get_embedding_function()

    if drop_if_exists and client.has_collection(collection_name):
        print(f"Collection '{collection_name}' already exists, deleting old data...")
        client.delete_collection(collection_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )

    print(f"Collection '{collection_name}' ready!")
    return collection
