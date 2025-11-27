"""Tests for backward compatibility of refactored code."""
import pytest

from humancheck import (
    Review,
    Decision,
    Feedback,
    ReviewAssignment,
    Attachment,
    ReviewStatus,
    DecisionType,
    UrgencyLevel,
    ContentCategory,
    Database,
    get_db,
    init_db,
    HumancheckConfig,
    get_config,
    init_config,
    RoutingEngine,
    ConditionEvaluator,
    ReviewAdapter,
    UniversalReview,
    RestAdapter,
    ReviewCreate,
    ReviewResponse,
    DecisionCreate,
    DecisionResponse,
    FeedbackCreate,
    FeedbackResponse,
)


def test_models_import_from_top_level():
    """Test that models can be imported from top level."""
    assert Review is not None
    assert Decision is not None
    assert Feedback is not None
    assert ReviewAssignment is not None
    assert Attachment is not None
    assert ReviewStatus is not None
    assert DecisionType is not None
    assert UrgencyLevel is not None
    assert ContentCategory is not None


def test_models_import_from_models_module():
    """Test that models can be imported from models module."""
    from humancheck.models import (
        Review,
        Decision,
        Feedback,
        ReviewStatus,
        DecisionType,
        UrgencyLevel,
    )
    assert Review is not None
    assert Decision is not None


def test_database_import_from_top_level():
    """Test that database can be imported from top level."""
    assert Database is not None
    assert get_db is not None
    assert init_db is not None


def test_database_import_from_database_module():
    """Test that database can be imported from database module."""
    from humancheck.database import Database, get_db, init_db, Base
    assert Database is not None
    assert Base is not None


def test_config_import_from_top_level():
    """Test that config can be imported from top level."""
    assert HumancheckConfig is not None
    assert get_config is not None
    assert init_config is not None


def test_config_import_from_config_module():
    """Test that config can be imported from config module."""
    from humancheck.config import HumancheckConfig, get_config, init_config
    assert HumancheckConfig is not None


def test_routing_import_from_top_level():
    """Test that routing can be imported from top level."""
    assert RoutingEngine is not None
    assert ConditionEvaluator is not None


def test_routing_import_from_routing_module():
    """Test that routing can be imported from routing module."""
    from humancheck.routing import RoutingEngine, ConditionEvaluator
    assert RoutingEngine is not None
    assert ConditionEvaluator is not None


def test_adapters_import_from_top_level():
    """Test that adapters can be imported from top level."""
    assert ReviewAdapter is not None
    assert UniversalReview is not None
    assert RestAdapter is not None


def test_adapters_import_from_adapters_module():
    """Test that adapters can be imported from adapters module."""
    from humancheck.adapters import (
        ReviewAdapter,
        UniversalReview,
        RestAdapter,
    )
    assert ReviewAdapter is not None
    assert UniversalReview is not None


def test_connectors_import_from_connectors_module():
    """Test that connectors can be imported from connectors module."""
    from humancheck.connectors import ReviewConnector, SlackConnector
    assert ReviewConnector is not None
    assert SlackConnector is not None


def test_storage_import_from_storage_module():
    """Test that storage can be imported from storage module."""
    from humancheck.storage import get_storage_manager
    assert get_storage_manager is not None


def test_security_import_from_security_module():
    """Test that security can be imported from security module."""
    from humancheck.security import validate_file
    assert validate_file is not None


def test_storage_and_security_imports():
    """Test storage and security imports work."""
    from humancheck.storage import get_storage_manager
    from humancheck.security import validate_file
    assert get_storage_manager is not None
    assert validate_file is not None


def test_schemas_import_from_top_level():
    """Test that schemas can be imported from top level."""
    assert ReviewCreate is not None
    assert ReviewResponse is not None
    assert DecisionCreate is not None
    assert DecisionResponse is not None
    assert FeedbackCreate is not None
    assert FeedbackResponse is not None


def test_schemas_import_from_schemas_module():
    """Test that schemas can be imported from schemas module."""
    from humancheck.schemas import (
        ReviewCreate,
        ReviewResponse,
        DecisionCreate,
        DecisionResponse,
    )
    assert ReviewCreate is not None
    assert ReviewResponse is not None


def test_core_module_accessible():
    """Test that core module is accessible."""
    from humancheck import core
    assert core is not None
    assert hasattr(core, 'models')
    assert hasattr(core, 'schemas')
    assert hasattr(core, 'storage')
    assert hasattr(core, 'routing')
    assert hasattr(core, 'integrations')
    assert hasattr(core, 'adapters')


def test_core_models_importable():
    """Test that core models can be imported directly."""
    from humancheck.core.models import Review, Decision, ReviewStatus
    assert Review is not None
    assert Decision is not None
    assert ReviewStatus is not None


def test_core_repositories_importable():
    """Test that core repositories can be imported."""
    from humancheck.core.storage.repositories import (
        ReviewRepository,
        DecisionRepository,
        FeedbackRepository,
    )
    assert ReviewRepository is not None
    assert DecisionRepository is not None
    assert FeedbackRepository is not None


def test_api_import_from_api_module():
    """Test that API can be imported from api module."""
    from humancheck.api import app, create_app
    assert app is not None
    assert create_app is not None


def test_api_import_from_api_py():
    """Test that API can be imported from api.py (backward compatibility)."""
    from humancheck import api
    assert hasattr(api, 'app')
    assert api.app is not None

