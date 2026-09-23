"""The slices of the source tables the fidelity tasks are built on.

Each task's ``build`` receives the loaded runtime tables, keyed by their runtime
names, and cuts its slice here; a slice is defined once so that two tasks over
the same rows (the linear and the log-target model) are over the same rows.
"""

from __future__ import annotations

import pandas as pd

CAPITAL = "ffiec_bank_capital_df"
BALANCE = "ffiec_bank_balance_sheets_df"
SBA = "sba_seven_a_loans_df"
HMDA = "hmda_lar_df"
BRANCHES = "fdic_sod_branches_df"

REPORT_DATE = "2024-12-31"
SBA_FEATURES = ["TermInMonths", "JobsSupported", "InitialInterestRate"]
HMDA_FEATURES = ["loan_amount", "income", "property_value", "loan_to_value_ratio"]


def capital(tables, state: str) -> pd.DataFrame:
    frame = tables[CAPITAL]
    return frame.loc[frame["report_date"].eq(REPORT_DATE) & frame["bank_state"].eq(state)] \
        .sort_values("bank_id").reset_index(drop=True)


def balance(tables, state: str) -> pd.DataFrame:
    frame = tables[BALANCE]
    return frame.loc[frame["report_date"].eq(REPORT_DATE) & frame["bank_state"].eq(state)] \
        .sort_values("bank_rssd_id").reset_index(drop=True)


def sba_texas(tables, fiscal_year: int) -> pd.DataFrame:
    """Texas 7(a) loans approved in one fiscal year, with the model's columns present."""
    frame = tables[SBA]
    rows = frame.loc[frame["ProjectState"].eq("TX") & frame["ApprovalFY"].eq(fiscal_year)]
    rows = rows.dropna(subset=SBA_FEATURES + ["GrossApproval"])
    return rows.sort_values(["ApprovalDate", "LocationID"]).reset_index(drop=True)


def sba_probes(tables) -> pd.DataFrame:
    """Twenty loans a model of the 2020 cohort is compared on: the first of 2021."""
    return sba_texas(tables, 2021).head(20)[SBA_FEATURES].astype(float)


def hmda_decided(tables, state: str) -> pd.DataFrame:
    """One state's 2024 applications that were originated (1) or denied (3), features present."""
    frame = tables[HMDA]
    rows = frame.loc[frame["state_code"].eq(state) & frame["action_taken"].isin(["1", "3"])]
    rows = rows.dropna(subset=HMDA_FEATURES)
    return rows.sort_values(HMDA_FEATURES + ["lei"]).reset_index(drop=True)


def hmda_probes(tables) -> pd.DataFrame:
    """Twenty New Hampshire applications a Vermont model is compared on."""
    return hmda_decided(tables, "NH").sample(n=20, random_state=0)[HMDA_FEATURES].astype(float)


def branches_on(tables, report_date: str) -> pd.DataFrame:
    frame = tables[BRANCHES]
    return frame.loc[frame["report_date"].eq(report_date)]
