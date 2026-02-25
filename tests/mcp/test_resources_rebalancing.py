"""Tests for rebalancing context resource - profile-based target allocation.

Covers Issue #54: Make rebalancing target allocation configurable via user profile.
"""

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

# Default allocation constants for assertions
DEFAULT_BOND = Decimal("60.0")
DEFAULT_STK = Decimal("35.0")
DEFAULT_CASH = Decimal("5.0")


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    """Create a notes directory in tmp_path."""
    notes = tmp_path / "notes"
    notes.mkdir()
    return notes


@pytest.fixture
def profile_path(notes_dir: Path) -> Path:
    """Return the path where the investor profile YAML would be written."""
    return notes_dir / "investor-profile.yaml"


def write_profile(profile_path: Path, data: dict) -> None:
    """Helper to write profile data to YAML file."""
    with open(profile_path, "w") as f:
        yaml.dump(data, f)


class TestGetTargetAllocationDefault:
    """Tests for default fallback behavior when no profile is configured."""

    def test_no_profile_file_returns_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """When notes/investor-profile.yaml does not exist, return 60/35/5 default."""
        monkeypatch.chdir(tmp_path)

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH

    def test_default_values_are_decimal_type(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Default allocation values must be Decimal, not float."""
        monkeypatch.chdir(tmp_path)

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert isinstance(result["BOND"], Decimal)
        assert isinstance(result["STK"], Decimal)
        assert isinstance(result["CASH"], Decimal)

    def test_empty_yaml_file_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """An empty YAML file (yaml.safe_load returns None) should fall back to defaults."""
        monkeypatch.chdir(tmp_path)
        profile_path.write_text("")

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH

    def test_malformed_yaml_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """Malformed YAML content should fall back to defaults without raising."""
        monkeypatch.chdir(tmp_path)
        profile_path.write_text("key: [invalid: yaml: {\n")

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH

    def test_profile_without_allocation_keys_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """Profile YAML with unrelated keys (no type or allocation_targets) uses defaults."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"residency": {"country": "Malaysia"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH

    def test_unknown_profile_type_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """An unrecognized investment_profile.type falls back to defaults."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "aggressive"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH


class TestGetTargetAllocationProfileTypes:
    """Tests for predefined profile type mappings."""

    def test_balanced_profile_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """balanced profile: STK=50%, BOND=40%, CASH=10%."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "balanced"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == Decimal("50.0")
        assert result["BOND"] == Decimal("40.0")
        assert result["CASH"] == Decimal("10.0")

    def test_growth_profile_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """growth profile: STK=75%, BOND=15%, CASH=10%."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "growth"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == Decimal("75.0")
        assert result["BOND"] == Decimal("15.0")
        assert result["CASH"] == Decimal("10.0")

    def test_conservative_profile_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """conservative profile: STK=25%, BOND=60%, CASH=15%."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "conservative"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == Decimal("25.0")
        assert result["BOND"] == Decimal("60.0")
        assert result["CASH"] == Decimal("15.0")

    def test_income_profile_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """income profile: STK=40%, BOND=50%, CASH=10%."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "income"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == Decimal("40.0")
        assert result["BOND"] == Decimal("50.0")
        assert result["CASH"] == Decimal("10.0")

    @pytest.mark.parametrize(
        "profile_type,expected_stk,expected_bond,expected_cash",
        [
            ("balanced", Decimal("50.0"), Decimal("40.0"), Decimal("10.0")),
            ("growth", Decimal("75.0"), Decimal("15.0"), Decimal("10.0")),
            ("conservative", Decimal("25.0"), Decimal("60.0"), Decimal("15.0")),
            ("income", Decimal("40.0"), Decimal("50.0"), Decimal("10.0")),
        ],
    )
    def test_all_profile_types_parametrized(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        profile_path: Path,
        profile_type: str,
        expected_stk: Decimal,
        expected_bond: Decimal,
        expected_cash: Decimal,
    ):
        """Parametrized test for all four profile types."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": profile_type}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == expected_stk
        assert result["BOND"] == expected_bond
        assert result["CASH"] == expected_cash

    def test_profile_type_values_are_decimal(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """Profile type allocation values must be Decimal instances."""
        monkeypatch.chdir(tmp_path)
        write_profile(profile_path, {"investment_profile": {"type": "growth"}})

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert isinstance(result["STK"], Decimal)
        assert isinstance(result["BOND"], Decimal)
        assert isinstance(result["CASH"], Decimal)


class TestGetTargetAllocationExplicitTargets:
    """Tests for explicit allocation_targets in YAML profile."""

    def test_explicit_allocation_targets_used(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """When allocation_targets is present, use those values."""
        monkeypatch.chdir(tmp_path)
        write_profile(
            profile_path,
            {"allocation_targets": {"stocks": 45, "bonds": 45, "cash": 10}},
        )

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert result["STK"] == Decimal("45")
        assert result["BOND"] == Decimal("45")
        assert result["CASH"] == Decimal("10")

    def test_explicit_targets_override_profile_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """When both allocation_targets and investment_profile.type are present,
        explicit allocation_targets take precedence."""
        monkeypatch.chdir(tmp_path)
        write_profile(
            profile_path,
            {
                "investment_profile": {"type": "growth"},
                "allocation_targets": {"stocks": 30, "bonds": 60, "cash": 10},
            },
        )

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        # Should use explicit targets, not growth profile (75/15/10)
        assert result["STK"] == Decimal("30")
        assert result["BOND"] == Decimal("60")
        assert result["CASH"] == Decimal("10")

    def test_explicit_targets_are_decimal_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """Explicit allocation values must be Decimal instances."""
        monkeypatch.chdir(tmp_path)
        write_profile(
            profile_path,
            {"allocation_targets": {"stocks": 50, "bonds": 40, "cash": 10}},
        )

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        assert isinstance(result["STK"], Decimal)
        assert isinstance(result["BOND"], Decimal)
        assert isinstance(result["CASH"], Decimal)

    def test_partial_allocation_targets_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_path: Path
    ):
        """Incomplete allocation_targets (missing keys) falls back to default."""
        monkeypatch.chdir(tmp_path)
        write_profile(
            profile_path,
            {"allocation_targets": {"stocks": 50}},  # Missing bonds and cash
        )

        from ib_sec_mcp.mcp.resources import _get_target_allocation

        result = _get_target_allocation()

        # Incomplete allocation_targets → fall back to default
        assert result["BOND"] == DEFAULT_BOND
        assert result["STK"] == DEFAULT_STK
        assert result["CASH"] == DEFAULT_CASH
