"""The rounds study's metadata-parity arms, and the per-run record every arm now keeps.

The parity arms differ from the original four in three things only: every
worker handed an object reads the same host note on what reached it, every
worker description says the instruction must carry everything else, and every
orchestrator may look at what it passes on. The original arms' prompts must not
change at all, so their stored runs stay comparable; and a worker run twice must
be judged on each run, so a first attempt can be told apart from the last.
"""

import json
import tempfile
from pathlib import Path

from core.fidelity import INPUT_SLOT, RECEIVED, ObjectKind, to_jsonable
from core.orchestration import ARMS, Medium, describe_worker, worker_specs
from core.prompts import ORCHESTRATOR_DATA_RULE, orchestrator_instructions
from core.rounds import CARRIED
from core.rounds_evaluator import _instruction_json, _named_file
from tests.test_agents import fenced_reply, text_reply
from tests.test_rounds import (
    CASE, FINAL, PRODUCER_CODE, _cave_script, _consume, _revise, _run, _standards,
)


PARITY = [name for name, arm in ARMS.items() if arm.parity]


# ----- the prompts -------------------------------------------------------------

def test_there_is_one_parity_arm_per_original_medium():
    assert sorted(ARMS[name].medium.value for name in PARITY) == ["cave", "file", "json", "text"]
    assert not any(arm.parity for name, arm in ARMS.items() if name not in PARITY)


def test_the_original_arms_prompts_are_unchanged_by_parity():
    assert orchestrator_instructions(answerer="consumer") == \
        orchestrator_instructions(answerer="consumer", may_inspect=False)
    assert ORCHESTRATOR_DATA_RULE.format(answerer="consumer") in \
        orchestrator_instructions(answerer="consumer")
    for spec in worker_specs(CASE):
        assert "Apart from" not in describe_worker(spec, ARMS["cave"], noun="object")


def test_every_parity_orchestrator_reads_the_same_prompt_and_may_look():
    prompt = orchestrator_instructions(answerer="consumer", may_inspect=True)
    assert "You may look at what a worker hands on" in prompt
    assert "Do not read files" not in prompt


def test_the_parity_cave_description_adds_the_other_arms_closing_sentence():
    for spec in worker_specs(CASE):
        plain = describe_worker(spec, ARMS["cave"], noun="object")
        parity = describe_worker(spec, ARMS["cave_parity"], noun="object")
        assert parity.startswith(plain)
        closing = "everything it needs must be in the instruction" if spec.takes_input \
            else "It reads the source data itself."
        assert closing in parity
        if spec.takes_input:
            assert closing in describe_worker(spec, ARMS["text"], noun="object")


# ----- reading what reached a worker ------------------------------------------

def test_the_instruction_s_json_is_its_last_fenced_block_else_its_longest_value():
    assert _instruction_json('a\n```json\n{"x": 1}\n```\nb\n```json\n{"y": [1, 2]}\n```') == \
        (True, {"y": [1, 2]})
    assert _instruction_json('take {"a": 1} and then [1, 2, 3, 4, 5, 6]') == (True, [1, 2, 3, 4, 5, 6])
    assert _instruction_json("nothing here") == (False, None)


def test_a_named_file_is_read_only_if_it_exists():
    standards = _standards()
    with tempfile.TemporaryDirectory() as workdir:
        path = Path(workdir) / "obj.parquet"
        standards[0].to_parquet(path)
        found, value = _named_file(f"work from '{path}', not {workdir}/gone.parquet", ObjectKind.TABLE)
        assert found == path and list(value.columns) == list(standards[0].columns)
        assert _named_file(f"work from {workdir}/gone.parquet", ObjectKind.TABLE) == (None, None)


# ----- the arms end to end -----------------------------------------------------

def _turns(record, kind: str = "UserMessage") -> str:
    return "\n".join(
        str(getattr(message, "content", "")) for message in record["messages"]
        if type(message).__name__ == kind
    )


def test_the_parity_cave_arm_reads_the_slot_into_the_turn_not_the_description():
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("cave_parity", _cave_script(codes), Path(workdir))
    assert result.success and not provider.replies
    assert result.chain == [0, 1, 2, 3, 3]
    producer, *rest = result.workers
    assert "Host reading" not in _turns(producer) and "note" not in producer["invocations"][0]
    for record in rest:
        note = record["invocations"][0]["note"]
        assert note.startswith("Host reading of what you were handed — the object in your runtime")
        assert "branch_deposits_thousand_usd: Int64" in note and note in _turns(record)
        assert "rows and these columns" not in _turns(record, "SystemMessage")


def test_the_parity_file_arm_reads_the_file_the_instruction_names():
    standards = _standards()
    names = ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions)]
    with tempfile.TemporaryDirectory() as workdir:
        paths = [Path(workdir) / name / f"{output}.parquet" for name, output in zip(names, outputs)]
        replies = []
        for index, name in enumerate(names):
            step = (f"r{index} = await {name}.run('work from {paths[index - 1]}')\nprint('ok')"
                    if index else f"r0 = await {name}.run('build it')\nprint('ok')")
            rebuilt = repr(to_jsonable(standards[min(index, len(standards) - 1)]))
            if name == "consumer":
                code = f"import pandas as pd\n{RECEIVED} = pd.read_parquet('{paths[index - 1]}')"
            else:
                code = (f"import pandas as pd\n{outputs[index]} = pd.DataFrame({rebuilt})\n"
                        + (f"{CARRIED} = pd.read_parquet('{paths[index - 1]}')\n" if index else "")
                        + f"{outputs[index]}.to_parquet('{paths[index]}')")
            replies += [fenced_reply(step), fenced_reply(code), text_reply("done")]
        result, _ = _run("file_parity", replies + [FINAL], Path(workdir))
        for index, record in enumerate(result.workers[1:], start=1):
            note = record["invocations"][0]["note"]
            assert f"the file {paths[index - 1]} named in your instruction" in note
            assert "rows and these columns" in note


def test_the_parity_text_arm_reads_the_payload_as_written():
    standards = _standards()
    names = ["producer", "reviser_1"]
    payload = json.dumps({CASE.task.output: to_jsonable(standards[0])})
    replies = [
        fenced_reply("r0 = await producer.run('build it')\nprint('ok')"),
        fenced_reply(f"import pandas as pd\n{CASE.task.output} = pd.DataFrame({to_jsonable(standards[0])!r})"),
        text_reply(f"Here.\n```json\n{payload}\n```"),
        fenced_reply("r1 = await reviser_1.run('Here it is:\\n' + r0.content)\nprint('ok')"),
        fenced_reply(f"{CARRIED} = 1"), text_reply("done"),
        FINAL,
    ]
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("text_parity", replies, Path(workdir))
    assert result.ran == names
    note = result.workers[1]["invocations"][0]["note"]
    # The payload as it crossed: a mapping of the output's name to its records,
    # not the table the host knows it stood for.
    assert note == (
        "Host reading of what you were handed — the JSON in your instruction: "
        f"It is a dict with keys ['{CASE.task.output}']."
    )


def test_a_worker_run_twice_is_judged_on_each_run():
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    replies = _cave_script(codes)
    # reviser_1's step runs it twice, the first time skipping its edit.
    output = CASE.revisions[0].output
    twice = fenced_reply(
        f"reviser_1.runtime.update_variable('{INPUT_SLOT}', obj0)\n"
        "await reviser_1.run('do your part')\nawait reviser_1.run('do your part')\n"
        f"obj1 = await reviser_1.runtime.retrieve('{output}')\nprint(type(obj1).__name__)"
    )
    unchanged = f"{CARRIED} = {INPUT_SLOT}\n{output} = {INPUT_SLOT}"
    replies[3:6] = [twice, fenced_reply(unchanged), text_reply("done"), *replies[4:6]]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("cave", replies, Path(workdir))
    assert not provider.replies
    reviser = result.workers[1]
    first, last = reviser["invocations"]
    assert reviser["runs"] == 2 and first["completed"] and last["completed"]
    assert first["stamp"] < last["stamp"]
    assert first["carried"] is True and first["applied"] is False
    assert last["applied"] is True and reviser["applied"] is True
    assert result.success and result.repeated == ["reviser_1"]
    # The original arms keep no note.
    assert all("note" not in run for record in result.workers for run in record["invocations"])
