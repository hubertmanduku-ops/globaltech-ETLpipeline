# ================================================================
# tests/test_pipeline.py — Unit Tests for the ETL Pipeline
# ================================================================
# WHAT ARE UNIT TESTS?
# ─────────────────────
# Unit tests are small, fast, automated checks that verify your code
# works correctly. Each test focuses on ONE specific behaviour.
#
# WHY WRITE TESTS?
# ─────────────────
# Without tests: you change something, run the pipeline, look at the
# output, and hope it looks right. This takes minutes and misses edge cases.
#
# With tests: you change something, type "pytest" in the terminal, and
# 20 checks run in 2 seconds. Any breakage is immediately highlighted.
#
# In professional data engineering:
#   - Tests run automatically every time code is pushed to GitHub (CI/CD)
#   - A test failure blocks the deployment
#   - No code goes to production without passing all tests
#
# HOW TO RUN THESE TESTS:
# ─────────────────────────
# Option A: Run all tests with pytest
#   pytest tests/
#
# Option B: Run this file directly (our own test runner at the bottom)
#   python tests/test_pipeline.py
#
# UNDERSTANDING TEST NAMES:
# ──────────────────────────
# Convention: test functions start with test_
# pytest finds them automatically by scanning for this prefix.
# Names describe WHAT they test and WHAT SHOULD HAPPEN:
#   test_validator_PASSES_on_CLEAN_data
#   test_validator_FAILS_on_EMPTY_dataframe
#   test_transformer_FILLS_nulls_with_MEDIAN
# ================================================================

import sys
import pathlib

_root = pathlib.Path(__file__).resolve().parent.parent   # go up from tests/ to project root
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd                        # for creating test DataFrames
from src.validator   import DataValidator  # the class we are testing
from src.transformer import DataTransformer  # the class we are testing


# ================================================================
# TEST DATA FACTORY
# ================================================================
# A "factory function" creates reusable test data.
# Every test that needs a DataFrame calls this function
# instead of building the DataFrame from scratch each time.
# If the schema changes, we update only this function.
# ================================================================

def make_clean_df(rows: int = 10) -> pd.DataFrame:
    """
    Create a small, clean DataFrame for use in tests.

    Clean means: no nulls, no duplicates, all values make sense.
    Tests that verify "passing behaviour" start with this DataFrame.
    Tests that verify "failing behaviour" modify a copy of it.
    """
    return pd.DataFrame({
        "employee_id": range(1, rows + 1),              # unique integers 1..N
        "name":        [f"Employee_{i}" for i in range(1, rows + 1)],  # unique text names
        "salary":      [50000 + i * 5000 for i in range(rows)],        # clean salaries
        "department":  (["Engineering", "Sales", "Data"] * rows)[:rows], # repeating categories
        "is_active":   [True] * rows,                   # all employees active
    })


# ================================================================
# DATAVALIDATOR TESTS
# ================================================================

def test_validator_passes_on_clean_data():
    """
    Clean data with no nulls and no duplicates should PASS all checks.

    This is the "happy path" — the ideal scenario.
    If this test fails, something is fundamentally wrong with the validator.
    """
    df = make_clean_df()

    # Create the validator with the clean DataFrame
    v = DataValidator(df)

    # Run all checks (method chaining)
    v.check_not_empty().check_nulls().check_duplicates().compute_stats()

    # assert raises AssertionError if the condition is False
    # The message after the comma shows when the test fails — it helps you debug
    assert v._passed == True,         "Validator should PASS on clean data with no nulls or duplicates"

    # Verify no CRITICAL issues were recorded
    critical_issues = [i for i in v.issues if i["severity"] == "CRITICAL"]
    assert len(critical_issues) == 0,         f"Expected 0 CRITICAL issues on clean data, got: {critical_issues}"

    print("  PASS: test_validator_passes_on_clean_data")


def test_validator_fails_on_empty_dataframe():
    """
    An empty DataFrame (0 rows) should be caught immediately and FAIL.

    An empty DataFrame means Module 03 extraction returned nothing.
    We must stop the pipeline — there is nothing to process.
    """
    empty_df = pd.DataFrame()   # completely empty — no rows, no columns

    v = DataValidator(empty_df)
    v.check_not_empty()   # only run this one check — the others would crash on empty data

    assert v._passed == False,         "Validator should FAIL when given an empty DataFrame"

    assert any(i["severity"] == "CRITICAL" for i in v.issues),         "Should have at least one CRITICAL issue on empty data"

    print("  PASS: test_validator_fails_on_empty_dataframe")


def test_validator_detects_nulls():
    """
    Null values should be detected and recorded in validator.issues.
    """
    df = make_clean_df()

    # Introduce null values into the salary column
    # .loc[0:2, "salary"] selects rows 0, 1, 2 in the salary column
    df.loc[0:2, "salary"] = None   # 3 nulls out of 10 rows = 30% null

    v = DataValidator(df)
    v.check_not_empty().check_nulls()

    # There should be at least one issue recorded for the salary column
    salary_issues = [i for i in v.issues if i["column"] == "salary"]
    assert len(salary_issues) > 0,         "Expected at least one issue recorded for column with nulls"

    print("  PASS: test_validator_detects_nulls")


def test_validator_detects_duplicates():
    """
    Duplicate rows should be detected and recorded.
    """
    df = make_clean_df()

    # Create a duplicate by appending the first row to the end
    # pd.concat() stacks DataFrames vertically
    # ignore_index=True resets the row numbers after concatenation
    df_with_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)

    v = DataValidator(df_with_dup)
    v.check_not_empty().check_duplicates()

    dup_issues = [i for i in v.issues if i["column"] == "duplicates"]
    assert len(dup_issues) > 0,         "Expected a duplicate issue when the DataFrame has a duplicate row"

    print("  PASS: test_validator_detects_duplicates")


def test_validator_stats_populated_after_compute_stats():
    """
    After compute_stats(), validator.stats should contain key metrics.
    """
    df = make_clean_df()
    v  = DataValidator(df)
    v.check_not_empty().check_nulls().compute_stats()

    # Verify all expected keys exist in the stats dictionary
    expected_keys = ["rows", "columns", "total_nulls", "passed", "duplicates"]
    for key in expected_keys:
        assert key in v.stats, f"Expected '{key}' in validator.stats, but it is missing"

    # Verify the row count is correct
    assert v.stats["rows"] == len(df),         f"Stats row count should be {len(df)}, got {v.stats['rows']}"

    print("  PASS: test_validator_stats_populated_after_compute_stats")


# ================================================================
# DATATRANSFORMER TESTS
# ================================================================

def test_transformer_fills_numeric_nulls_with_median():
    """
    Null values in numeric columns should be filled with the column median.

    We verify:
    1. Before fill_nulls(): the column has nulls
    2. After fill_nulls(): the column has zero nulls
    3. The filled value equals the median of the non-null values
    """
    df = make_clean_df()

    # Before: introduce exactly 1 null in the salary column
    original_salary_median = df["salary"].median()   # save the median before introducing null
    df.loc[0, "salary"] = None   # set the first row's salary to null

    # Create transformer and run fill_nulls()
    t = DataTransformer(df)
    t.fill_nulls()

    # After: the column should have zero nulls
    nulls_after = int(t.df["salary"].isna().sum())
    assert nulls_after == 0,         f"Expected 0 nulls after fill_nulls(), got {nulls_after}"

    # The filled value should be the median of the NON-null values
    # (which is the same as the original median since we removed one value)
    filled_value = t.df.loc[0, "salary"]
    # We use a tolerance check (not exact equality) for floating point
    assert abs(filled_value - original_salary_median) < 0.01,         f"Expected filled value ≈ {original_salary_median}, got {filled_value}"

    print("  PASS: test_transformer_fills_numeric_nulls_with_median")


def test_transformer_fills_text_nulls_with_unknown():
    """
    Null values in text columns should be filled with the string "Unknown".
    """
    df = make_clean_df()
    df.loc[0, "department"] = None   # introduce null in text column

    t = DataTransformer(df)
    t.fill_nulls()

    # Verify the null is gone
    assert t.df["department"].isna().sum() == 0,         "Text column should have no nulls after fill_nulls()"

    # Verify it was filled with "Unknown"
    filled_value = t.df.loc[0, "department"]
    assert filled_value == "Unknown",         f"Expected 'Unknown' in text column, got '{filled_value}'"

    print("  PASS: test_transformer_fills_text_nulls_with_unknown")


def test_transformer_removes_exact_duplicates():
    """
    Exact duplicate rows should be removed.

    An "exact duplicate" is a row where EVERY column value is identical
    to another row in the same DataFrame.
    """
    df = make_clean_df(10)   # 10 clean rows

    # Add one duplicate: row 0 copied and appended
    df_with_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)

    before_count = len(df_with_dup)   # should be 11

    t = DataTransformer(df_with_dup)
    t.drop_duplicates()

    after_count = len(t.df)   # should be 10

    assert after_count < before_count,         f"Row count should decrease after removing duplicates: {before_count} → {after_count}"

    assert after_count == 10,         f"Expected 10 rows after removing 1 duplicate, got {after_count}"

    print("  PASS: test_transformer_removes_exact_duplicates")


def test_transformer_adds_metadata_columns():
    """
    add_metadata() should add three metadata columns to the DataFrame.

    We verify:
    1. _industry column exists
    2. _processed_at column exists
    3. _pipeline_version column exists
    """
    df = make_clean_df()
    t  = DataTransformer(df)
    t.add_metadata()

    expected_cols = ["_industry", "_processed_at", "_pipeline_version"]
    for col in expected_cols:
        assert col in t.df.columns,             f"Expected metadata column '{col}' in DataFrame after add_metadata()"

    print("  PASS: test_transformer_adds_metadata_columns")


def test_transformer_adds_outlier_flags():
    """
    add_derived_columns() should create outlier flag boolean columns.

    We add an obvious outlier (salary = 1,000,000) and verify
    that the outlier flag for that column is True for that row.
    """
    df = make_clean_df(20)   # need at least ~10 rows for IQR to work meaningfully

    # Add a dramatic outlier: one salary that is 10× higher than all others
    df.loc[0, "salary"] = 1_000_000   # clear outlier

    t = DataTransformer(df)
    t.add_derived_columns()

    # The salary_is_outlier column should exist
    assert "salary_is_outlier" in t.df.columns,         "Expected 'salary_is_outlier' column after add_derived_columns()"

    # The row with the extreme value should be flagged True
    assert t.df.loc[0, "salary_is_outlier"] == True,         "The dramatic outlier row should have salary_is_outlier = True"

    # The combined flag should also exist
    assert "is_any_outlier" in t.df.columns,         "Expected 'is_any_outlier' combined flag column"

    print("  PASS: test_transformer_adds_outlier_flags")


def test_transformer_method_chaining_returns_self():
    """
    Every transformer method should return the same transformer object (self).

    This verifies the method chaining pattern works correctly.
    transformer.fill_nulls().drop_duplicates()  ← this should work.
    """
    df = make_clean_df()
    t  = DataTransformer(df)

    # Run the full chain and capture what each method returns
    result = (
        t
        .fill_nulls()
        .drop_duplicates()
        .fix_types()
        .add_derived_columns()
        .add_metadata()
    )

    # result should be the SAME object as t (same memory address)
    # 'is' checks object identity (same object), not just equality
    assert result is t,         "Method chaining should return the same transformer object (self)"

    print("  PASS: test_transformer_method_chaining_returns_self")


def test_transformer_original_data_unchanged():
    """
    The original DataFrame passed to DataTransformer should never be modified.

    DataTransformer works on a copy. The caller's data must remain intact.
    """
    df = make_clean_df()
    df.loc[0, "salary"] = None   # introduce a null

    original_null_count = int(df["salary"].isna().sum())   # 1 null

    # Create transformer (which copies the df) and fill nulls on the copy
    t = DataTransformer(df)
    t.fill_nulls()

    # The ORIGINAL df should still have 1 null — the transformer should not have touched it
    current_null_count = int(df["salary"].isna().sum())

    assert current_null_count == original_null_count,         (
            f"Original DataFrame was modified! "
            f"Nulls before: {original_null_count}, after: {current_null_count}. "
            f"DataTransformer must work on a copy, never the original."
        )

    print("  PASS: test_transformer_original_data_unchanged")


# ================================================================
# TEST RUNNER
# ================================================================
# This runs when you execute: python tests/test_pipeline.py
# It runs every test function and reports pass/fail.
# ================================================================

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  MODULE 05 — ETL PIPELINE UNIT TESTS")
    print("=" * 60)
    print()

    # Collect all test functions
    tests = [
        test_validator_passes_on_clean_data,
        test_validator_fails_on_empty_dataframe,
        test_validator_detects_nulls,
        test_validator_detects_duplicates,
        test_validator_stats_populated_after_compute_stats,
        test_transformer_fills_numeric_nulls_with_median,
        test_transformer_fills_text_nulls_with_unknown,
        test_transformer_removes_exact_duplicates,
        test_transformer_adds_metadata_columns,
        test_transformer_adds_outlier_flags,
        test_transformer_method_chaining_returns_self,
        test_transformer_original_data_unchanged,
    ]

    passed = 0
    failed = 0

    print("  DATAVALIDATOR TESTS:")
    for i, test_fn in enumerate(tests[:5], 1):
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}")
            print(f"    Reason: {e}")
            failed += 1

    print()
    print("  DATATRANSFORMER TESTS:")
    for i, test_fn in enumerate(tests[5:], 6):
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}")
            print(f"    Reason: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed | {failed} failed")
    if failed == 0:
        print("  All tests passed ✓")
    else:
        print(f"  {failed} test(s) failed ✗ — fix the issues above")
    print("=" * 60)
