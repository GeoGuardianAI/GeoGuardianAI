import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)


# Games must run fast and be deterministic: force the pure-Python hash-based
# embedder so tests do not load sentence-transformers / torch (several seconds
# per process) and do not depend on a locally cached BGE-M3 model.
from ai.embedding_service.bge import BGEEmbeddingModel  # noqa: E402


def _fast_initialize(self):
    self.model = None
    self.initialized = True


BGEEmbeddingModel.initialize = _fast_initialize


@pytest.fixture(scope="session")
def orchestrator():
    """A single shared orchestrator backed by a temporary seedable vector DB."""
    import shutil
    import tempfile

    from ai.orchestrator.orchestrator import GeoGuardianOrchestrator
    from ai.vector_service.qdrant import QdrantVectorDB

    orch = GeoGuardianOrchestrator()
    tmp_dir = tempfile.mkdtemp(prefix="gg_rag_db_")
    orch.db = QdrantVectorDB(db_path=os.path.join(tmp_dir, "db"))
    orch.retriever.db = orch.db
    orch.preload_default_sops()
    yield orch
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def renewed(orchestrator):
    """Return the shared orchestrator with fresh caches / memory per test."""
    orchestrator.cache.cache.clear()
    orchestrator.memory.sessions.clear()
    return orchestrator


@pytest.fixture()
def api_orchestrator(orchestrator):
    """Point the uploaded/chat routers at the shared orchestrator."""
    import ai.api.upload as upload_module

    upload_module.orchestrator = orchestrator
    return orchestrator


@pytest.fixture()
def fresh_orchestrator_factory(tmp_path):
    """Build isolated orchestrators for tests that need empty or custom DBs."""
    import ai.api.upload as upload_module

    from ai.orchestrator.orchestrator import GeoGuardianOrchestrator
    from ai.vector_service.qdrant import QdrantVectorDB

    def _make(seed: bool = True):
        orch = GeoGuardianOrchestrator()
        orch.db = QdrantVectorDB(db_path=str(tmp_path / "db.json"))
        orch.retriever.db = orch.db
        if seed:
            orch.preload_default_sops()
        upload_module.orchestrator = orch
        return orch

    return _make


@pytest.fixture(autouse=True)
def cleanup_temp_dirs():
    """Remove any residue created by upload/speech handlers between tests."""
    yield
    for dir_name in ("temp_uploads", "temp_speech"):
        if os.path.isdir(dir_name):
            for f in os.listdir(dir_name):
                try:
                    os.remove(os.path.join(dir_name, f))
                except Exception:
                    pass