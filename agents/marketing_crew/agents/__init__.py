"""
Marketing Agents

This module contains all agent implementations for the marketing crew.
"""

from .corn_flakes_worker import CornFlakesWorker
from .inventory_execution_worker import InventoryExecutionWorker
from .inventory_translation_worker import InventoryTranslationWorker
from .promotion_execution_worker import PromotionExecutionWorker
from .promotional_translation_worker import PromotionalTranslationWorker

__all__ = [
    'CornFlakesWorker',
    'InventoryExecutionWorker',
    'InventoryTranslationWorker',
    'PromotionExecutionWorker',
    'PromotionalTranslationWorker'
]
