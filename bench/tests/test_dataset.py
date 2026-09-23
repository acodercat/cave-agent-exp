import json

from config import DATASETS_DIR
from core.data import load_expansion_table, runtime_variables
from core.dataset_layers import load_runtime_table


def test_governed_runtime_catalog_and_cutoffs():
    catalog = json.loads((DATASETS_DIR / "catalog.json").read_text())
    assert catalog["benchmark_cutoff"] == "2025-12-31"
    source_by_table = {
        "rtdsm.revisions": "philadelphia_fed_rtdsm",
        "fed_stress_tests.results": "fed_stress_tests",
        "sec_nmfp.series_filings": "sec_nmfp",
        "sec_nmfp.daily_shareholder_flows": "sec_nmfp_flows",
        "sec_nmfp.daily_liquidity": "sec_nmfp_liquidity",
        "sec_nmfp.share_class_yields": "sec_nmfp_class_yields",
        "sec_nport.fund_reports": "sec_nport",
        "sec_nport.interest_rate_risk": "sec_nport_interest_rate_risk",
        "hmda.loan_applications": "hmda",
        "sec_notes.numeric_facts": "sec_notes",
        "sec_notes.submissions": "sec_notes_submissions",
        "sec_notes.dimensional_facts": "sec_notes_dimensional",
        "sec_notes.dimensions": "sec_notes_dimensions",
        "sec_13f.filings": "sec_13f_filings",
        "sec_13f.holdings_by_cusip": "sec_13f_holdings",
        "fed_z1_vintages.series_observations": "fed_z1_vintages",
        "sec_ftd.fails_to_deliver": "sec_ftd",
        "nyfed.reference_rates": "nyfed_reference_rates",
        "treasury_auctions.auctions": "treasury_auctions",
        "treasury_rates.yield_curve": "treasury_yield_curve",
        "sec_form_c.filings": "sec_form_c",
        "sec_form_d.filings": "sec_form_d",
        "bis.credit_gap": "bis_credit_gap",
        "bis.debt_service_ratios": "bis_debt_service",
        "bis.effective_exchange_rates": "bis_effective_exchange_rates",
        "bis.global_liquidity": "bis_global_liquidity",
        "bis.otc_derivatives": "bis_otc_derivatives",
        "fdic.bank_financials": "fdic_bankfind",
        "sec_bdc.investment_schedule": "sec_bdc",
        "sec_bdc.filings": "sec_bdc_filings",
        "sba_7a_504.seven_a_loans": "sba_7a",
        "sba_7a_504.five_o_four_loans": "sba_504",
        "cftc_cot.financial_futures": "cftc_cot",
        "fhfa_hpi.house_price_indexes": "fhfa_hpi",
    }
    for table_id, source in source_by_table.items():
        assert len(load_expansion_table(source)) == catalog["tables"][table_id]["row_count"]
    assert load_expansion_table("sec_nmfp")["filing_date"].max() <= "2025-12-31"
    assert load_expansion_table("sec_nport")["filing_date"].max() <= "2025-12-31"
    assert load_expansion_table("sec_form_c")["FILING_DATE"].max() <= "2025-12-31"
    assert load_expansion_table("sec_form_d")["FILING_DATE"].max() <= "2025-12-31"
    assert load_expansion_table("sba_7a")["ApprovalFY"].max() <= 2025
    assert load_expansion_table("cftc_cot")["Report_Date_as_YYYY-MM-DD"].max() <= "2025-12-31"
    assert load_expansion_table("sec_bdc")["report_date"].max() <= "2025-12-31"
    assert load_expansion_table("fhfa_hpi")["yr"].max() <= 2025


def test_runtime_tables_are_selected_by_declared_source():
    assert [variable.name for variable in runtime_variables(["hmda"])] == ["hmda_lar_df"]
    assert [
        variable.name
        for variable in runtime_variables(["treasury_auctions", "treasury_yield_curve"])
    ] == ["treasury_auctions_df", "treasury_yield_curve_df"]
    assert [
        variable.name for variable in runtime_variables(["sec_nmfp"])
    ] == [
        "nmfp_series_filings_df", "nmfp_daily_flows_df",
        "nmfp_daily_liquidity_df", "nmfp_class_yields_df",
    ]
    assert [
        variable.name for variable in runtime_variables(["sec_nmfp_series_filings"])
    ] == ["nmfp_series_filings_df"]
    assert [variable.name for variable in runtime_variables(["sec_nport"])] == [
        "nport_fund_reports_df",
        "nport_interest_rate_risk_df",
    ]
    assert [
        variable.name for variable in runtime_variables(["ffiec_nic_structure"])
    ] == ["ffiec_nic_institutions_df", "ffiec_nic_ownership_df"]


def test_cross_source_batch_aliases_resolve_to_governed_runtime_tables():
    governed_aliases = {
        "bis_credit_gap": "bis.credit_gap",
        "bis_debt_service": "bis.debt_service_ratios",
        "cftc_cot": "cftc_cot.financial_futures",
        "fed_stress_tests": "fed_stress_tests.results",
        "ffiec_call_reports_capital": "ffiec_call_reports.bank_capital",
        "ffiec_nic_institutions": "ffiec_nic_structure.institution_identifiers_current",
        "ffiec_nic_ownership": "ffiec_nic_structure.ownership_relationships_current",
        "nyfed_reference_rates": "nyfed.reference_rates",
        "sec_nmfp_class_yields": "sec_nmfp.share_class_yields",
        "treasury_auctions": "treasury_auctions.auctions",
        "treasury_debt_to_penny": "treasury_debt.debt_to_penny",
        "treasury_marketable_securities": "treasury_debt.marketable_securities",
        "treasury_usfr_reconciliations": "treasury_usfr.reconciliations",
    }
    for source, table_id in governed_aliases.items():
        assert load_expansion_table(source).equals(load_runtime_table(table_id))
