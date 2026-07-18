import logging
from roadmaps.engine import RecommendationEngineOrchestrator

logger = logging.getLogger(__name__)

class RecommendationEngine(RecommendationEngineOrchestrator):
    """
    Subclass of RecommendationEngineOrchestrator to maintain 100% backward compatibility.
    """
    pass
