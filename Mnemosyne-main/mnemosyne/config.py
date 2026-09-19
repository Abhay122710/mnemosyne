import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_CONFIG = {
    "version": "0.1.0",
    "storage_dir": ".mnemosyne",
    "hooks_installed": False,
    "max_context_diffs": 5,
    "reflection_threshold": 3,
    "cognee_api_key": None,
    "cognee_api_url": "https://api.cognee.ai",
    # LLM / embedding backend. "ollama" runs everything locally and free (no API
    # key required). "openai" uses a paid OpenAI key. See configure_llm_env().
    "llm_provider": "ollama",
    "llm_api_key": None,
    "llm_model": "llama3.1:8b",
    "embedding_model": "nomic-embed-text",
    "embedding_dimensions": 768,
    "ollama_base_url": "http://localhost:11434/v1",
    # Advanced graph extraction (typed CodeKnowledgeGraph schema + temporal event
    # tracking) needs a strong LLM that reliably emits strict structured JSON.
    # Small local models (e.g. llama3.2:3b) can't, so these default OFF and we use
    # Cognee's robust built-in extraction. Turn ON only with a strong model
    # (OpenAI, or a large local model like llama3.1:70b).
    "use_custom_graph_schema": False,
    "use_temporal_cognify": False,
    "use_cloud": False,
}

def find_project_root(start_path: Optional[Path] = None) -> Path:
    """Find the root directory of the repository (where .git or .mnemosyne resides)."""
    current = (start_path or Path.cwd()).resolve()
    for dir_path in [current] + list(current.parents):
        if (dir_path / ".git").exists() or (dir_path / ".mnemosyne").exists():
            return dir_path
    return current

def get_mnemosyne_dir(repo_root: Optional[Path] = None) -> Path:
    if os.getenv("VERCEL") == "1":
        mnemosyne_dir = Path("/tmp/.mnemosyne")
        mnemosyne_dir.mkdir(parents=True, exist_ok=True)
        # Copy initial bundled memories from /var/task/.mnemosyne if they exist
        bundled_dir = Path("/var/task/.mnemosyne")
        if bundled_dir.exists() and bundled_dir != mnemosyne_dir:
            import shutil
            for item in bundled_dir.iterdir():
                dest = mnemosyne_dir / item.name
                if item.is_file() and not dest.exists():
                    try:
                        shutil.copy2(item, dest)
                    except Exception:
                        pass
    else:
        root = repo_root or find_project_root()
        mnemosyne_dir = root / ".mnemosyne"
        mnemosyne_dir.mkdir(parents=True, exist_ok=True)
    return mnemosyne_dir

def get_config_path(repo_root: Optional[Path] = None) -> Path:
    return get_mnemosyne_dir(repo_root) / "config.json"

def load_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    config_path = get_config_path(repo_root)
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any], repo_root: Optional[Path] = None) -> None:
    config_path = get_config_path(repo_root)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def configure_llm_env(config: Optional[Dict[str, Any]] = None) -> str:
    """
    Export the environment variables that Cognee/LiteLLM and the raw OpenAI SDK
    need, based on the configured LLM provider.

    Returns the resolved provider name ("ollama" or "openai").

    Existing environment variables always win, so anything already set in .env or
    the shell overrides these defaults — this only fills in the blanks.

    - "ollama"  → fully local & free. Points chat + embeddings at a local Ollama
                  server (default http://localhost:11434). No API key required.
                  Requires: `ollama serve` running and the models pulled, e.g.
                  `ollama pull llama3.1:8b nomic-embed-text`.
    - "openai"  → uses OPENAI_API_KEY (paid).
    """
    if config is None:
        config = load_config()

    def setdefault(key: str, value: Optional[str]) -> None:
        if value is not None and not os.getenv(key):
            os.environ[key] = str(value)

    provider = (os.getenv("LLM_PROVIDER") or config.get("llm_provider") or "openai").lower()

    if provider == "ollama":
        base = os.getenv("LLM_ENDPOINT") or config.get("ollama_base_url") or "http://localhost:11434/v1"
        host = base.replace("/v1", "")
        chat_model = config.get("llm_model") or "llama3.1:8b"
        embed_model = config.get("embedding_model") or "nomic-embed-text"
        embed_dims = config.get("embedding_dimensions", 768)
        # Cognee's OllamaEmbeddingEngine posts {"input": ...} and reads "embeddings"
        # — that is Ollama's newer /api/embed batch endpoint, NOT /api/embeddings.
        embed_endpoint = host + "/api/embed"
        # The Ollama embedder loads a HuggingFace tokenizer (via `transformers`) for
        # token counting. It has no default, so we must name one that matches the
        # embedding model or Cognee queries huggingface.co/None and 401s.
        hf_tokenizer = config.get("embedding_tokenizer") or "nomic-ai/nomic-embed-text-v1.5"

        # Cognee / LiteLLM configuration
        setdefault("LLM_PROVIDER", "ollama")
        setdefault("LLM_MODEL", chat_model)
        setdefault("LLM_ENDPOINT", base)
        setdefault("LLM_API_KEY", "ollama")  # Ollama ignores the value but LiteLLM needs one
        setdefault("EMBEDDING_PROVIDER", "ollama")
        setdefault("EMBEDDING_MODEL", embed_model)
        setdefault("EMBEDDING_ENDPOINT", embed_endpoint)
        setdefault("EMBEDDING_API_KEY", "ollama")
        setdefault("EMBEDDING_DIMENSIONS", embed_dims)
        setdefault("EMBEDDING_MAX_COMPLETION_TOKENS", 8192)
        setdefault("HUGGINGFACE_TOKENIZER", hf_tokenizer)

        # Raw `openai` SDK calls (llm_helper, consolidator) route through Ollama's
        # OpenAI-compatible endpoint.
        setdefault("OPENAI_API_KEY", "ollama")
        setdefault("OPENAI_BASE_URL", base)
        setdefault("MNEMOSYNE_LLM_MODEL", chat_model)
        return provider

    # Default: OpenAI (or any OPENAI_API_KEY-compatible provider)
    llm_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or config.get("llm_api_key")
    if llm_key:
        setdefault("OPENAI_API_KEY", llm_key)
    setdefault("MNEMOSYNE_LLM_MODEL", config.get("llm_model") or "gpt-4o-mini")
    return provider
