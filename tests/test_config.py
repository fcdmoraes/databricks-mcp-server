"""
Unit tests for src/core/config.py — get_genie_spaces registry loader.
"""

import os
from unittest.mock import patch

import pytest

from src.core.config import get_genie_spaces


def _env(**kwargs):
    """Helper: returns a clean environment dict with only the provided vars."""
    base = {k: v for k, v in os.environ.items() if not k.startswith("GENIE_SPACE_")}
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Basic cases
# ---------------------------------------------------------------------------

def test_returns_empty_when_no_vars():
    with patch.dict(os.environ, _env(), clear=True):
        assert get_genie_spaces() == []


def test_single_space_without_description():
    env = _env(
        GENIE_SPACE_1_ID="id-abc",
        GENIE_SPACE_1_NAME="vendas",
    )
    with patch.dict(os.environ, env, clear=True):
        spaces = get_genie_spaces()
        assert len(spaces) == 1
        assert spaces[0]["id"] == "id-abc"
        assert spaces[0]["name"] == "vendas"
        assert spaces[0]["description"] == ""


def test_single_space_with_description():
    env = _env(
        GENIE_SPACE_1_ID="id-abc",
        GENIE_SPACE_1_NAME="vendas",
        GENIE_SPACE_1_DESCRIPTION="Dados de vendas B2C e B2B",
    )
    with patch.dict(os.environ, env, clear=True):
        spaces = get_genie_spaces()
        assert spaces[0]["description"] == "Dados de vendas B2C e B2B"


def test_multiple_spaces_ordered_by_number():
    env = _env(
        GENIE_SPACE_2_ID="id-2",
        GENIE_SPACE_2_NAME="logistica",
        GENIE_SPACE_1_ID="id-1",
        GENIE_SPACE_1_NAME="vendas",
    )
    with patch.dict(os.environ, env, clear=True):
        spaces = get_genie_spaces()
        assert len(spaces) == 2
        assert spaces[0]["name"] == "vendas"   # N=1 first
        assert spaces[1]["name"] == "logistica"  # N=2 next


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_entry_without_name_is_ignored():
    """An entry without NAME should not appear in the result."""
    env = _env(
        GENIE_SPACE_1_ID="id-abc",
        # no GENIE_SPACE_1_NAME
    )
    with patch.dict(os.environ, env, clear=True):
        assert get_genie_spaces() == []


def test_entry_without_id_is_ignored():
    """An entry without ID should not appear in the result."""
    env = _env(
        GENIE_SPACE_1_NAME="vendas",
        # no GENIE_SPACE_1_ID
    )
    with patch.dict(os.environ, env, clear=True):
        assert get_genie_spaces() == []


def test_gaps_in_numbering_are_handled():
    """A gap in numbering (1 and 3, no 2) should return both valid entries."""
    env = _env(
        GENIE_SPACE_1_ID="id-1",
        GENIE_SPACE_1_NAME="vendas",
        GENIE_SPACE_3_ID="id-3",
        GENIE_SPACE_3_NAME="financeiro",
    )
    with patch.dict(os.environ, env, clear=True):
        spaces = get_genie_spaces()
        assert len(spaces) == 2
        names = [s["name"] for s in spaces]
        assert "vendas" in names
        assert "financeiro" in names


def test_returned_dict_has_required_keys():
    env = _env(
        GENIE_SPACE_1_ID="id-abc",
        GENIE_SPACE_1_NAME="vendas",
        GENIE_SPACE_1_DESCRIPTION="Desc",
    )
    with patch.dict(os.environ, env, clear=True):
        spaces = get_genie_spaces()
        assert set(spaces[0].keys()) == {"id", "name", "description"}
