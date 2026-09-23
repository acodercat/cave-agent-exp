"""A two-turn case with a fixed answer key, for tests of the harness itself.

It has the shape of a real filing case — select a filing, then read a fact from
it — but its ground truth is a constant, so evaluator and verification tests
neither read the runtime tables nor depend on which cases are imported.
"""

from cave_agent import Variable

from core.validation import turn_validator, validate_ordered_outputs


TURN_1_NAMES = ["filing_accession", "fiscal_period_end", "acceptance_datetime"]
TURN_2_NAMES = ["revenue_period_start", "revenue_usd_billions"]

SPEC = {
    "name": "filing_case",
    "module": "tests.fixtures.filing_case",
    "task_family": "retrieval",
    "data_sources": ["sec_companyfacts", "sec_submissions"],
    "conversations": [{"id": "main", "turns": [
        {"query": "Select the original annual filing and report its identifiers.",
         "validator": "validate_filing_selection", "stores": TURN_1_NAMES},
        {"query": "Using that filing, report the annual revenue fact.",
         "validator": "validate_annual_revenue", "stores": TURN_2_NAMES},
    ]}],
}


def _v(name, description):
    return Variable(name, None, description)


variables = [
    _v(TURN_1_NAMES[0], "Store the selected original filing accession as text."),
    _v(TURN_1_NAMES[1], "Store its report-date fiscal period end as an ISO YYYY-MM-DD string."),
    _v(TURN_1_NAMES[2], "Store its acceptance timestamp as an ISO YYYY-MM-DDTHH:MM:SS string."),
    _v(TURN_2_NAMES[0], "Store the annual revenue fact's start date as an ISO YYYY-MM-DD string."),
    _v(TURN_2_NAMES[1], "Store annual total revenues in USD billions rounded to 2 decimals."),
]

DECIMALS = [None, None, None, None, 2]


def ground_truth() -> tuple:
    return "0000104169-25-000037", "2025-01-31", "2025-03-14T12:00:00", "2024-02-01", 680.985


def _validate_subset(outputs, names):
    by_name = {variable.name: variable for variable in variables}
    truth = dict(zip(by_name, ground_truth()))
    decimals = dict(zip(by_name, DECIMALS))
    return validate_ordered_outputs(
        outputs,
        [by_name[name] for name in names],
        [truth[name] for name in names],
        [decimals[name] for name in names],
    )


def validate_turn_1(outputs):
    return _validate_subset(outputs, TURN_1_NAMES)


def validate_turn_2(outputs):
    return _validate_subset(outputs, TURN_2_NAMES)


def validate(outputs):
    return _validate_subset(outputs, [variable.name for variable in variables])


validators = {
    "validate_filing_selection": turn_validator(validate_turn_1),
    "validate_annual_revenue": turn_validator(validate_turn_2),
}
