"""Leveraged fund futures positions, asked at six sizes.

Leveraged funds' net position in each financial futures contract on each weekly
report date, and that position as a fraction of open interest, from the CFTC
futures-only reports through 2024-12-31. The smallest scope is ten weeks of the
Canadian dollar contract; the others are every contract from a report date
between 2024-12-24 (125 rows) and 2021-07-06 (10,006).

Net positions are signed, three contract codes in ten begin with a zero, market
names carry hyphens and commas, and a row is identified by contract and date
together. Open interest is never zero here. Taking short minus long, or giving
the share as a percentage, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


END = "2024-12-31"


def load():
    reports = load_expansion_table("cftc_cot")
    return reports.loc[
        reports["report_scope"].eq("futures_only")
        & reports["Report_Date_as_YYYY-MM-DD"].le(END)
    ]


def build(reports, *, since, contract=None):
    rows = reports.loc[reports["Report_Date_as_YYYY-MM-DD"].ge(since)]
    if contract:
        rows = rows.loc[rows["CFTC_Contract_Market_Code"].eq(contract)]
    net = rows["Lev_Money_Positions_Long_All"] - rows["Lev_Money_Positions_Short_All"]
    return rows.assign(
        contract_code=rows["CFTC_Contract_Market_Code"],
        report_date=rows["Report_Date_as_YYYY-MM-DD"],
        market_name=rows["Market_and_Exchange_Names"],
        open_interest=rows["Open_Interest_All"],
        net_position=net,
        net_share_of_open_interest=net / rows["Open_Interest_All"],
    )[["contract_code", "report_date", "market_name", "open_interest", "net_position",
       "net_share_of_open_interest"]]


TASK = TableTask(
    name="leveraged_fund_positions",
    title="Leveraged fund futures positions",
    data_sources=("cftc_cot",),
    financial_domain="capital_markets",
    query=(
        "Track how leveraged funds were positioned in financial futures, using the CFTC "
        "Traders in Financial Futures futures-only reports: {scope} through 2024-12-31. For "
        "each contract and report date give the contract market code, the report date, the "
        "market and exchange name, open interest, the leveraged funds' net position (long "
        "minus short, so negative when net short), and that net position over open interest."
    ),
    output="position_table",
    row_noun="contract and report date",
    key=("contract_code", "report_date"),
    columns=(
        Column("contract_code", CellKind.PADDED_IDENTIFIER,
               "text, exactly as in the source, keeping leading zeros"),
        Column("report_date", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("market_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("open_interest", CellKind.INTEGER, "integer, contracts"),
        Column("net_position", CellKind.INTEGER, "integer, contracts, negative when net short"),
        Column("net_share_of_open_interest", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "the Canadian dollar contract (code 090741) from 2024-10-29", 10,
             {"since": "2024-10-29", "contract": "090741"}),
        Size("100", "every contract from 2024-12-24", 125, {"since": "2024-12-24"}),
        Size("250", "every contract from 2024-12-10", 262, {"since": "2024-12-10"}),
        Size("500", "every contract from 2024-11-12", 513, {"since": "2024-11-12"}),
        Size("1k", "every contract from 2024-09-17", 983, {"since": "2024-09-17"}),
        Size("10k", "every contract from 2021-07-06", 10006, {"since": "2021-07-06"}),
    ),
    load=load,
    build=build,
    near_misses={
        "net position as short minus long": changing(net_position=lambda net: -net),
        "share as a percentage": changing(net_share_of_open_interest=lambda share: share * 100),
    },
)
