"""
pytest configuration and fixtures for RecRadiko tests

Global fixtures for real environment testing with minimal mock usage.
"""

import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


@pytest.fixture
def temp_env():
    """一時テスト環境fixture"""
    # テスト実行環境設定
    os.environ["RECRADIKO_TEST_MODE"] = "true"
    os.environ["RECRADIKO_CONSOLE_OUTPUT"] = "true"
    os.environ["RECRADIKO_LOG_LEVEL"] = "DEBUG"
    
    with TemporaryTestEnvironment() as env:
        yield env


@pytest.fixture
def real_test_base():
    """実環境テストベースfixture"""
    return RealEnvironmentTestBase()


@pytest.fixture(scope="session")
def setup_test_environment():
    """テストセッション全体の環境設定"""
    # テスト実行時の環境変数設定
    os.environ["RECRADIKO_TEST_MODE"] = "true"
    os.environ["RECRADIKO_CONSOLE_OUTPUT"] = "true"
    os.environ["RECRADIKO_LOG_LEVEL"] = "DEBUG"
    
    # pytest-asyncio設定
    import asyncio
    if hasattr(asyncio, 'set_event_loop_policy'):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    yield
    
    # クリーンアップ
    test_env_vars = [
        "RECRADIKO_TEST_MODE",
        "RECRADIKO_CONSOLE_OUTPUT", 
        "RECRADIKO_LOG_LEVEL"
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture(autouse=True)
def enable_logging():
    """テスト実行時のログ出力を有効化"""
    import logging
    import warnings
    import gc
    
    # ログ設定
    logging.basicConfig(level=logging.DEBUG)
    
    # ResourceWarningを無視
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", message="unclosed database")
    warnings.filterwarnings("ignore", message="unclosed <socket")
    
    yield
    
    # ガベージコレクション強制実行
    gc.collect()