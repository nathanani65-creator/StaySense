from ..config import get_settings

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # lazy import: heavy dep, only needed for search
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model_name)
    return _model


def encode(texts: list[str]):
    """Returns L2-normalized embeddings, ready for inner-product (cosine) search."""
    model = get_model()
    # multilingual-e5 models expect a "query: " / "passage: " prefix for best results
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.astype("float32")
