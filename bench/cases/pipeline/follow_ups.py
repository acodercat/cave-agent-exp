"""What the second agent is asked, once the first agent's table has reached it.

The first agent's question is never written here: it is a delivery task the suite
already has, asked unchanged (``cases/table_delivery`` and
``cases/table_control``). Reusing them means the first stage is a question whose
validator has already been shown to separate a right answer from a plausible
wrong one, and that the pipeline's first hop can be read against the delivery
study's single hop on the same question.

What is written here is the second question — one per task, about the table the
first agent produced.

Three rules decide what it may ask for, and ``test_pipeline_cases.py`` enforces
the first two:

* **At least one answer moves when the table is short at the end** — a sum over
  the whole table, a count of a class that spans it, or a distinct count.

  This is weaker than "every row changes the answer", which an independent check
  disproved: a conditional count, a distinct count and a sum with zero terms can
  all be blind to one particular row. Measured over the narrowed tables, three of
  the twenty-four are blind to at least one row; the counts are pinned in
  ``tests/test_pipeline_cases.py`` (``BLIND_ROWS``), where they are checked rather
  than quoted. The channel failures this study
  measures are gross — a table that never arrived, or one cut off at an output
  limit — so the sensitivity that matters is to the missing tail, which every
  question has. The blindness is reported as a limit, not papered over.
* **Every answer is exact**: sums of integer columns, counts, and labels chosen
  by an extremum with the tie broken by name. A sum of the decimal columns would
  accumulate a difference between a channel that carried full precision and one
  that carried the rounded text of it, and would separate the arms for a reason
  that has nothing to do with whether the table crossed.
* **Nothing is asked whose answer the table does not move.** A grouping the
  table holds one of, or a threshold one row in 250 crosses, is the same answer
  at every size; the counts and base rates below were read off the data before
  the question was written.

The shapes are the analytical families the suite already names in
``metadata/case_taxonomy.json`` — reconciliation, comparison and ranking, risk
screening, scenario analysis, a temporal path — so that no two of these read as
the same question with the nouns changed.

``market_growth_drawdown`` is left out: its reference has a rounding tie, and a
question built on its rows would inherit it.
"""

from __future__ import annotations

from collections import Counter
from typing import Callable

from cases.table_control._branch_top_deposits import TASK as BRANCH_TOP_DEPOSITS
from cases.table_control._crowdfunding_top_offerings import TASK as CROWDFUNDING_TOP_OFFERINGS
from cases.table_control._flood_claim_top_payments import TASK as FLOOD_CLAIM_TOP_PAYMENTS
from cases.table_control._market_quality_top_securities import (
    TASK as MARKET_QUALITY_TOP_SECURITIES,
)
from cases.table_control._short_volume_top_symbols import TASK as SHORT_VOLUME_TOP_SYMBOLS
from cases.table_delivery import tasks as delivery_tasks
from core.pipeline import Answer, FollowUp
from core.table_delivery import TableTask
from core.validation import select_extreme_key


THIRD_QUARTER = {"07", "08", "09"}


# ----- reading the delivered rows ---------------------------------------------
#
# Every follow-up computes its answers through these, so that a missing cell is
# treated the same way everywhere: it contributes nothing to a total and is not
# counted as a value.

def _total(rows: list[dict], column: str) -> int:
    return sum(row[column] for row in rows if row[column] is not None)


def _count(rows: list[dict], holds: Callable[[dict], bool]) -> int:
    return sum(1 for row in rows if holds(row))


def _distinct(rows: list[dict], column: str) -> int:
    return len({row[column] for row in rows if row[column] is not None})


def _totalled_by(rows: list[dict], key: str, weight: str) -> Counter:
    totals: Counter = Counter()
    for row in rows:
        if row[key] is not None and row[weight] is not None:
            totals[row[key]] += row[weight]
    return totals


def _tally(rows: list[dict], column: str) -> Counter:
    return Counter(row[column] for row in rows if row[column] is not None)


def _leading(totals: Counter):
    """The key that totals highest, with the tie broken by the key itself."""
    return select_extreme_key(dict(totals))


def _at_least(row: dict, part: str, whole: str, numerator: int, denominator: int) -> bool:
    """``part/whole >= numerator/denominator``, in integers so it is exact."""
    if row[part] is None or row[whole] is None:
        return False
    return row[part] * denominator >= row[whole] * numerator


def _month(row: dict, column: str) -> str:
    """The month of an ISO date, whether or not a time of day follows it."""
    return (row[column] or "")[5:7]


# ==============================================================================
# The delivery-control family: five tasks whose sizes differ only in how many
# of the same ranked rows the question asks for.
# ==============================================================================

def _branch_deposits(rows: list[dict]) -> tuple:
    # The state holding the largest deposit total is New York at every size, so
    # the question asks how many states are in play rather than which leads.
    return (
        _total(rows, "branch_deposits_thousand_usd"),
        _distinct(rows, "branch_state"),
        _count(rows, lambda row: row["main_office_indicator"] == "1"),
    )


BRANCH_DEPOSITS = FollowUp(
    query=(
        "Add up the deposits of every branch in this table, in thousands of dollars, "
        "and tell me how many states those branches are spread across. I also want a "
        "count of how many of them the main-office indicator marks as a main office, "
        "that is, writes as 1."
    ),
    answers=(
        Answer("total_deposits_thousand_usd",
               "Deposits summed over every branch in the table, in thousands of dollars.",
               decimals=0),
        Answer("distinct_state_count",
               "How many states the branches are spread across.", decimals=0),
        Answer("main_office_count",
               "How many of the branches have a main-office indicator of 1.", decimals=0),
    ),
    compute=_branch_deposits,
)


def _crowdfunding_offerings(rows: list[dict]) -> tuple:
    by_month = Counter(row["filing_date"][:7] for row in rows if row["filing_date"])
    return len(rows), _leading(by_month), _distinct(rows, "issuer_name")


# The table's submission_type column holds "C", "C/A" and "C-U": the original
# filing and its amendments and updates, all of them Regulation Crowdfunding
# filings. A question that called them "Form C filings" read, to most agents, as
# asking for the rows typed exactly "C", and the answer was scored against every
# row. The question now asks about the rows, and says so.
CROWDFUNDING_OFFERINGS = FollowUp(
    query=(
        "Start by telling me how many rows the table holds — count every filing in "
        "it, whatever its submission type. Then group those rows by the calendar "
        "month they were filed in and say which month has the most, written as "
        "YYYY-MM, taking the earlier month where two are level. Last, how many "
        "distinct issuer names appear anywhere in the table?"
    ),
    answers=(
        Answer("filing_count", "How many filings the table holds.", decimals=0),
        Answer("busiest_month", "The calendar month with the most filings, as YYYY-MM."),
        Answer("distinct_issuer_count",
               "How many distinct issuer names the table holds.", decimals=0),
    ),
    compute=_crowdfunding_offerings,
)


def _flood_claims(rows: list[dict]) -> tuple:
    return (
        _count(rows, lambda row: row["state_usps"] == "FL"),
        _distinct(rows, "state_usps"),
        _count(rows, lambda row: _month(row, "date_of_loss") in THIRD_QUARTER),
    )


FLOOD_CLAIMS = FollowUp(
    query=(
        "How many of these flood claims are Florida's, and how many states appear in "
        "the table at all? I also need to know how many of the claims have a date of "
        "loss in July, August or September."
    ),
    answers=(
        Answer("florida_claim_count", "How many of the claims are in Florida.", decimals=0),
        Answer("distinct_state_count", "How many distinct states the table covers.", decimals=0),
        Answer("third_quarter_claim_count",
               "How many claims have a date of loss in July, August or September.", decimals=0),
    ),
    compute=_flood_claims,
)


def _market_quality(rows: list[dict]) -> tuple:
    return (
        _total(rows, "trades"),
        _count(rows, lambda row: row["security_type"] == "ETF"),
        _total([row for row in rows if row["security_type"] == "Stock"], "trades"),
    )


MARKET_QUALITY = FollowUp(
    query=(
        "Add up the trades across every row of this table. Then split the table by "
        "security type: how many of the rows are ETFs, and how many trades do the rows "
        "typed as Stock account for between them?"
    ),
    answers=(
        Answer("total_trades", "The number of trades summed over every row.", decimals=0),
        Answer("etf_count", "How many of the rows have a security type of ETF.", decimals=0),
        Answer("stock_trades", "Trades summed over the rows typed as Stock.", decimals=0),
    ),
    compute=_market_quality,
)


def _short_volume(rows: list[dict]) -> tuple:
    return (
        _total(rows, "short_volume"),
        _total(rows, "total_volume"),
        _count(rows, lambda row: _at_least(row, "short_volume", "total_volume", 1, 2)),
    )


SHORT_VOLUME = FollowUp(
    query=(
        "Summed over every symbol in this table, what are the short volume and the "
        "total volume? And how many of the symbols had at least half their volume sold "
        "short — that is, twice the short volume reaches the total volume?"
    ),
    answers=(
        Answer("summed_short_volume", "Short volume summed over every symbol.", decimals=0),
        Answer("summed_total_volume", "Total volume summed over every symbol.", decimals=0),
        Answer("majority_short_symbol_count",
               "How many symbols had at least half their volume sold short.", decimals=0),
    ),
    compute=_short_volume,
)


# ==============================================================================
# The delivery family: nineteen tasks whose sizes widen the scope the question
# covers. Base rates quoted in the comments were read off the 250-row size.
# ==============================================================================

# ----- banking and credit -----------------------------------------------------

def _bank_capital(rows: list[dict]) -> tuple:
    return (
        _total(rows, "cet1_capital_thousand_usd"),
        _total(rows, "risk_weighted_assets_thousand_usd"),
        # 132 of 241 at the 250-row size: a threshold the table moves either side of.
        _count(rows, lambda row: _at_least(
            row, "cet1_capital_thousand_usd", "risk_weighted_assets_thousand_usd", 15, 100,
        )),
    )


BANK_CAPITAL = FollowUp(
    query=(
        "Add up the CET1 capital and the risk-weighted assets across the whole table, "
        "both in thousands of dollars. Then, working from those two columns rather "
        "than the reported ratio, count the banks whose CET1 capital is at least "
        "fifteen per cent of their risk-weighted assets."
    ),
    answers=(
        Answer("total_cet1_capital_thousand_usd",
               "CET1 capital summed over every bank, in thousands of dollars.", decimals=0),
        Answer("total_risk_weighted_assets_thousand_usd",
               "Risk-weighted assets summed over every bank, in thousands of dollars.",
               decimals=0),
        Answer("banks_at_or_above_fifteen_percent",
               "How many banks hold CET1 capital of at least 15% of risk-weighted assets.",
               decimals=0),
    ),
    compute=_bank_capital,
)


def _bank_footprint(rows: list[dict]) -> tuple:
    return (
        _total(rows, "branches_in_area"),
        _total(rows, "deposits_in_area_thousand_usd"),
        _leading(_totalled_by(rows, "fdic_certificate", "branches_in_area")),
    )


BANK_FOOTPRINT = FollowUp(
    query=(
        "Across the whole table, how many branches are there in the area, and what do "
        "their deposits come to in thousands of dollars? Then tell me which bank has "
        "the most branches there, by FDIC certificate number, taking the certificate "
        "that sorts first as text if two banks are level."
    ),
    answers=(
        Answer("total_branches_in_area",
               "Branches in the area summed over every bank.", decimals=0),
        Answer("total_deposits_in_area_thousand_usd",
               "Deposits in the area summed over every bank, in thousands of dollars.",
               decimals=0),
        Answer("leading_fdic_certificate",
               "The FDIC certificate number of the bank with the most branches in the area."),
    ),
    compute=_bank_footprint,
)


def _branch_shares(rows: list[dict]) -> tuple:
    by_county = _tally(rows, "county_fips")
    busiest = _leading(by_county)
    return _total(rows, "deposits_thousand_usd"), _distinct(rows, "county_fips"), by_county[busiest]


BRANCH_SHARES = FollowUp(
    query=(
        "What do the deposits of every branch in this table come to, in thousands of "
        "dollars? How many distinct county FIPS codes does the table cover? And how "
        "many branches fall in whichever of those counties holds the most, breaking a "
        "tie by taking the county code that sorts first."
    ),
    answers=(
        Answer("total_deposits_thousand_usd",
               "Deposits summed over every branch, in thousands of dollars.", decimals=0),
        Answer("distinct_county_count",
               "How many distinct county FIPS codes the table covers.", decimals=0),
        Answer("branches_in_the_largest_county",
               "How many branches fall in the county holding the most.", decimals=0),
    ),
    compute=_branch_shares,
)


def _credit_union_delinquency(rows: list[dict]) -> tuple:
    return (
        _total(rows, "loans_usd"),
        _total(rows, "delinquent_loans_usd"),
        # 18 of 251 at the 250-row size. Ten per cent would have been 1 of 251.
        _count(rows, lambda row: _at_least(row, "delinquent_loans_usd", "loans_usd", 2, 100)),
    )


CREDIT_UNION_DELINQUENCY = FollowUp(
    query=(
        "Total the loans and the delinquent loans over this whole table, in dollars. "
        "Then screen it: how many of these credit unions have delinquent loans running "
        "at two per cent of their loans or more? Work that out from the two dollar "
        "columns, not from the reported ratio."
    ),
    answers=(
        Answer("total_loans_usd", "Loans summed over every credit union.", decimals=0),
        Answer("total_delinquent_loans_usd",
               "Delinquent loans summed over every credit union.", decimals=0),
        Answer("credit_unions_at_or_above_two_percent",
               "How many credit unions are delinquent on 2% of loans or more.", decimals=0),
    ),
    compute=_credit_union_delinquency,
)


def _sba_lending(rows: list[dict]) -> tuple:
    return (
        _total(rows, "loans"),
        _distinct(rows, "naics_code"),
        _leading(_totalled_by(rows, "naics_code", "loans")),
    )


SBA_LENDING = FollowUp(
    query=(
        "How many loans does this table account for in total, and how many distinct "
        "NAICS codes does it span? Then, totalling loans by NAICS code, which code "
        "lends the most — the lower code if two are level?"
    ),
    answers=(
        Answer("total_loans", "Loans summed over every row.", decimals=0),
        Answer("distinct_naics_count", "How many distinct NAICS codes appear.", decimals=0),
        Answer("leading_naics_code", "The NAICS code with the most loans once totalled."),
    ),
    compute=_sba_lending,
)


# ----- capital markets --------------------------------------------------------

def _fails_to_deliver(rows: list[dict]) -> tuple:
    return (
        _total(rows, "quantity_fails"),
        _distinct(rows, "symbol"),
        _leading(_totalled_by(rows, "symbol", "quantity_fails")),
    )


FAILS_TO_DELIVER = FollowUp(
    query=(
        "Add up the failed quantities across this table and tell me how many distinct "
        "symbols it covers. Which symbol fails the most once the quantities are "
        "totalled per symbol? Where two symbols are level, take the one that sorts "
        "first alphabetically."
    ),
    answers=(
        Answer("total_quantity_fails", "Failed quantity summed over every row.", decimals=0),
        Answer("distinct_symbol_count", "How many distinct symbols appear.", decimals=0),
        Answer("leading_symbol", "The symbol with the largest total failed quantity."),
    ),
    compute=_fails_to_deliver,
)


def _leveraged_positions(rows: list[dict]) -> tuple:
    return (
        _total(rows, "open_interest"),
        # 74 of 262 at the 250-row size.
        _count(rows, lambda row: (row["net_position"] or 0) > 0),
        _distinct(rows, "market_name"),
    )


LEVERAGED_POSITIONS = FollowUp(
    query=(
        "Sum the open interest over every row of this table. Then separate the rows "
        "that are net long — a net position above zero — and count them. How many "
        "distinct markets does the table name?"
    ),
    answers=(
        Answer("total_open_interest", "Open interest summed over every row.", decimals=0),
        Answer("net_long_row_count", "How many rows carry a net position above zero.",
               decimals=0),
        Answer("distinct_market_count", "How many distinct markets the table names.",
               decimals=0),
    ),
    compute=_leveraged_positions,
)


def _short_volume_ratios(rows: list[dict]) -> tuple:
    return (
        _total(rows, "short_volume_shares"),
        _total(rows, "total_volume_shares"),
        # 149 of 208 at the 250-row size.
        _count(rows, lambda row: _at_least(
            row, "short_volume_shares", "total_volume_shares", 40, 100,
        )),
    )


SHORT_VOLUME_RATIOS = FollowUp(
    query=(
        "Give me the short volume and the total volume summed over the whole table, in "
        "shares. Then screen for heavy shorting: how many symbols have short volume of "
        "forty per cent of total volume or more? Use the two share columns rather than "
        "the ratio column."
    ),
    answers=(
        Answer("total_short_volume_shares", "Short volume summed over every symbol.",
               decimals=0),
        Answer("total_volume_shares", "Total volume summed over every symbol.", decimals=0),
        Answer("symbols_at_or_above_forty_percent",
               "How many symbols are shorted on 40% of their volume or more.", decimals=0),
    ),
    compute=_short_volume_ratios,
)


# ----- investment funds -------------------------------------------------------

def _fund_leverage(rows: list[dict]) -> tuple:
    by_registrant = _tally(rows, "registrant_name")
    # 40 of 123 registrants at the 250-row size file more than one series.
    return (
        len(rows),
        len(by_registrant),
        sum(1 for count in by_registrant.values() if count > 1),
    )


FUND_LEVERAGE = FollowUp(
    query=(
        "How many fund series does this table report on, and how many distinct "
        "registrants do they belong to? Of those registrants, how many appear with "
        "more than one series in the table?"
    ),
    answers=(
        Answer("series_count", "How many rows, that is series, the table holds.", decimals=0),
        Answer("distinct_registrant_count", "How many distinct registrants appear.",
               decimals=0),
        Answer("registrants_with_several_series",
               "How many registrants appear with more than one series.", decimals=0),
    ),
    compute=_fund_leverage,
)


def _holdings_changes(rows: list[dict]) -> tuple:
    return (
        _total(rows, "value_change_usd"),
        # 137 of 250 at the 250-row size.
        _count(rows, lambda row: (row["value_change_usd"] or 0) < 0),
        _distinct(rows, "issuer_name"),
    )


HOLDINGS_CHANGES = FollowUp(
    query=(
        "Over the whole table, what is the net change in value between the two "
        "quarters, in dollars? How many of the holdings fell — a change below zero? "
        "And how many distinct issuers does the table name?"
    ),
    answers=(
        Answer("total_value_change_usd", "The change in value summed over every holding.",
               decimals=0),
        Answer("holdings_that_fell_count", "How many holdings fell in value.", decimals=0),
        Answer("distinct_issuer_count", "How many distinct issuers the table names.",
               decimals=0),
    ),
    compute=_holdings_changes,
)


# ----- macro, rates, FX and trade ---------------------------------------------

def _county_employment(rows: list[dict]) -> tuple:
    return (
        _total(rows, "employment"),
        _total(rows, "establishments"),
        _distinct(rows, "area_fips"),
    )


COUNTY_EMPLOYMENT = FollowUp(
    query=(
        "Sum the employment and the establishments over this whole table, and tell me "
        "how many distinct county FIPS areas it covers."
    ),
    answers=(
        Answer("total_employment", "Employment summed over every row.", decimals=0),
        Answer("total_establishments", "Establishments summed over every row.", decimals=0),
        Answer("distinct_area_count", "How many distinct county FIPS areas appear.",
               decimals=0),
    ),
    compute=_county_employment,
)


def _exchange_rates(rows: list[dict]) -> tuple:
    # A wider scope adds areas, not months: the month range is the same from the
    # 250-row size up, so the question asks about the areas and the series start.
    months = sorted({row["month"] for row in rows if row["month"]})
    return len(rows), _distinct(rows, "area_code"), months[0]


EXCHANGE_RATES = FollowUp(
    query=(
        "This table is a monthly series over several areas. How many observations "
        "does it hold altogether, and how many distinct areas do they belong to? Which "
        "month does the series start in — written exactly as the table writes it?"
    ),
    answers=(
        Answer("observation_count", "How many rows the table holds.", decimals=0),
        Answer("distinct_area_count", "How many distinct areas the table covers.",
               decimals=0),
        Answer("earliest_month", "The earliest month in the table, written as it appears."),
    ),
    compute=_exchange_rates,
)


# ----- insurance and disaster -------------------------------------------------

def _flood_payments(rows: list[dict]) -> tuple:
    return (
        len(rows),
        _distinct(rows, "county_code"),
        _count(rows, lambda row: _month(row, "date_of_loss") in THIRD_QUARTER),
    )


FLOOD_PAYMENTS = FollowUp(
    query=(
        "How many claims are in this table, and how many distinct county codes do they "
        "fall in? Then: how many of the claims have a date of loss in July, August or "
        "September?"
    ),
    answers=(
        Answer("claim_count", "How many claims the table holds.", decimals=0),
        Answer("distinct_county_count", "How many distinct county codes appear.", decimals=0),
        Answer("third_quarter_claim_count",
               "How many claims have a date of loss in July, August or September.", decimals=0),
    ),
    compute=_flood_payments,
)


def _storm_damages(rows: list[dict]) -> tuple:
    by_type = _tally(rows, "event_type")
    commonest = _leading(by_type)
    return len(rows), commonest, by_type[commonest]


STORM_DAMAGES = FollowUp(
    query=(
        "How many storm events does the table record? Which event type occurs most "
        "often in it — the type that sorts first alphabetically if two are level — and "
        "how many of the events are of that type?"
    ),
    answers=(
        Answer("event_count", "How many events the table records.", decimals=0),
        Answer("most_common_event_type", "The event type occurring on the most rows."),
        Answer("events_of_that_type", "How many events are of that type.", decimals=0),
    ),
    compute=_storm_damages,
)


# ----- households and housing -------------------------------------------------

def _pension_returns(rows: list[dict]) -> tuple:
    return (
        _total(rows, "participants"),
        # 43 of 263 at the 250-row size.
        _count(rows, lambda row: (row["net_income_usd"] or 0) < 0),
        _distinct(rows, "sponsor_ein"),
    )


PENSION_RETURNS = FollowUp(
    query=(
        "How many participants do these plans cover between them? How many of the "
        "plans ran a negative net income? And how many distinct sponsor EINs does the "
        "table name?"
    ),
    answers=(
        Answer("total_participants", "Participants summed over every plan.", decimals=0),
        Answer("plans_with_negative_net_income",
               "How many plans reported a net income below zero.", decimals=0),
        Answer("distinct_sponsor_count", "How many distinct sponsor EINs appear.", decimals=0),
    ),
    compute=_pension_returns,
)


def _house_prices(rows: list[dict]) -> tuple:
    quarters = sorted({row["quarter"] for row in rows if row["quarter"]})
    return (
        len(rows),
        quarters[0],
        # A four-quarter change is missing on the first year of any series.
        _count(rows, lambda row: row["change_over_four_quarters"] is None),
    )


HOUSE_PRICES = FollowUp(
    query=(
        "How many observations does this house-price series hold, and which quarter "
        "does it start in — written exactly as the table writes it? Some rows carry no "
        "four-quarter change at all: how many?"
    ),
    answers=(
        Answer("observation_count", "How many rows the table holds.", decimals=0),
        Answer("earliest_quarter", "The earliest quarter, written as it appears."),
        Answer("rows_missing_a_change",
               "How many rows have no four-quarter change.", decimals=0),
    ),
    compute=_house_prices,
)


def _zcta_land(rows: list[dict]) -> tuple:
    return (
        _total(rows, "land_area_sq_m"),
        _distinct(rows, "zcta"),
        _distinct(rows, "county_fips"),
    )


ZCTA_LAND = FollowUp(
    query=(
        "Add up the land area over every row of this table, in square metres. Then "
        "tell me how many distinct ZCTAs and how many distinct county FIPS codes it "
        "covers."
    ),
    answers=(
        Answer("total_land_area_sq_m", "Land area summed over every row, in square metres.",
               decimals=0),
        Answer("distinct_zcta_count", "How many distinct ZCTAs appear.", decimals=0),
        Answer("distinct_county_count", "How many distinct county FIPS codes appear.",
               decimals=0),
    ),
    compute=_zcta_land,
)


# ----- corporate reporting ----------------------------------------------------

def _private_offerings(rows: list[dict]) -> tuple:
    return (
        _total(rows, "amount_sold_usd"),
        # 82 of 250 at the 250-row size.
        _count(rows, lambda row: (
            row["amount_sold_usd"] is not None
            and row["amount_sold_usd"] == row["total_offering_usd"]
        )),
        _distinct(rows, "cik"),
    )


PRIVATE_OFFERINGS = FollowUp(
    query=(
        "What do the amounts sold come to across this whole table, in dollars? How "
        "many of the offerings sold out entirely — amount sold equal to the total "
        "offering? And how many distinct CIKs filed them?"
    ),
    answers=(
        Answer("total_amount_sold_usd", "Amount sold summed over every offering.",
               decimals=0),
        Answer("fully_sold_offering_count",
               "How many offerings sold their full amount.", decimals=0),
        Answer("distinct_cik_count", "How many distinct CIKs appear.", decimals=0),
    ),
    compute=_private_offerings,
)


# ----- public finance ---------------------------------------------------------

def _treasury_outstanding(rows: list[dict]) -> tuple:
    return (
        _total(rows, "issues"),
        # 28 of 243 at the 250-row size.
        _count(rows, lambda row: (row["maturity_date"] or "")[:4] > "2030"),
        _distinct(rows, "record_date"),
    )


TREASURY_OUTSTANDING = FollowUp(
    query=(
        "Sum the issues over the whole table. How many of these securities mature "
        "after 2030 — that is, in 2031 or later? And how many distinct record dates "
        "does the table carry?"
    ),
    answers=(
        Answer("total_issues", "Issues summed over every row.", decimals=0),
        Answer("securities_maturing_after_2030",
               "How many securities mature in 2031 or later.", decimals=0),
        Answer("distinct_record_date_count", "How many distinct record dates appear.",
               decimals=0),
    ),
    compute=_treasury_outstanding,
)


# ==============================================================================

_DELIVERY_FOLLOW_UPS = {
    "bank_capital_ratios": BANK_CAPITAL,
    "bank_state_footprint": BANK_FOOTPRINT,
    "branch_deposit_shares": BRANCH_SHARES,
    "county_sector_employment": COUNTY_EMPLOYMENT,
    "credit_union_delinquency": CREDIT_UNION_DELINQUENCY,
    "effective_exchange_rates": EXCHANGE_RATES,
    "fails_to_deliver_values": FAILS_TO_DELIVER,
    "flood_claim_payments": FLOOD_PAYMENTS,
    "fund_report_leverage": FUND_LEVERAGE,
    "holdings_value_changes": HOLDINGS_CHANGES,
    "leveraged_fund_positions": LEVERAGED_POSITIONS,
    "pension_plan_returns": PENSION_RETURNS,
    "private_offerings": PRIVATE_OFFERINGS,
    "sba_industry_lending": SBA_LENDING,
    "short_volume_ratios": SHORT_VOLUME_RATIOS,
    "state_house_prices": HOUSE_PRICES,
    "storm_event_damages": STORM_DAMAGES,
    "treasury_securities_outstanding": TREASURY_OUTSTANDING,
    "zcta_county_land": ZCTA_LAND,
}


def _delivery_pairs() -> tuple[tuple[TableTask, FollowUp], ...]:
    """The delivery tasks that have a follow-up, in the family's own order.

    A task without one is left out deliberately and a follow-up naming a task
    that does not exist is a mistake, so the second is an error and the first is
    not.
    """
    by_name = {task.name: task for task in delivery_tasks()}
    unknown = sorted(set(_DELIVERY_FOLLOW_UPS) - set(by_name))
    if unknown:
        raise ValueError(f"follow-ups name no such delivery task: {unknown}")
    return tuple(
        (by_name[name], follow_up) for name, follow_up in _DELIVERY_FOLLOW_UPS.items()
    )


# Pairs rather than a mapping: a task carries the dicts of near misses and
# misreadings its validator is tested against, so it is not hashable.
FOLLOW_UPS: tuple[tuple[TableTask, FollowUp], ...] = (
    (BRANCH_TOP_DEPOSITS, BRANCH_DEPOSITS),
    (CROWDFUNDING_TOP_OFFERINGS, CROWDFUNDING_OFFERINGS),
    (FLOOD_CLAIM_TOP_PAYMENTS, FLOOD_CLAIMS),
    (MARKET_QUALITY_TOP_SECURITIES, MARKET_QUALITY),
    (SHORT_VOLUME_TOP_SYMBOLS, SHORT_VOLUME),
) + _delivery_pairs()
