"""The phrasing eval. The model writes the sentence; the numbers are checked.

Every case replays a recorded chat-completion response, so the eval needs no key
and no network. A sentence is shown only when it quotes every number the query
returned and no number it did not; otherwise the plain numbers are shown.
"""

import json
from pathlib import Path

import pytest

from engine.errors import EngineError
from engine.phrase import Answer, Fact, faithful, phrase

CASES = json.loads((Path(__file__).parent / "recordings" / "phrase.json").read_text())["cases"]


def replay(response, calls=None):
    def complete(messages, schema=None):
        if calls is not None:
            calls.append(messages)
        return response["choices"][0]["message"]["content"]
    return complete


def answer_of(case):
    facts = [Fact(label, value) for label, value in case["facts"]]
    return Answer(facts, plain="PLAIN: " + "; ".join(f"{f.label} {f.value}" for f in facts))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_a_recorded_sentence_is_shown_only_when_its_numbers_are_exact(case):
    answer = answer_of(case)
    sentence = phrase(case["question"], answer, replay(case["response"]))
    content = case["response"]["choices"][0]["message"]["content"]
    assert faithful(content, answer, case["question"]) is case["faithful"]
    assert sentence == (content if case["faithful"] else answer.plain)


def test_the_prompt_carries_the_facts_and_the_question():
    calls = []
    case = CASES[0]
    phrase(case["question"], answer_of(case), replay(case["response"], calls))
    prompt = json.dumps(calls[0], ensure_ascii=False)
    assert "who owes me money" in prompt
    assert "₹1,250.50" in prompt


def test_one_fact_is_stated_plainly_without_a_model_call():
    calls = []
    answer = Answer([Fact("spent on food, this month", "₹700")], plain="You spent ₹700 on food.")
    assert phrase("how much on food", answer, replay(CASES[0]["response"], calls)) == answer.plain
    assert calls == []


def test_no_model_means_plain_numbers():
    answer = answer_of(CASES[0])
    assert phrase("who owes me money", answer, None) == answer.plain


def test_a_model_failure_falls_back_to_plain_numbers():
    def broken(messages, schema=None):
        raise EngineError("unparseable", "the model did not answer", status=502)

    answer = answer_of(CASES[0])
    assert phrase("who owes me money", answer, broken) == answer.plain


def test_advice_may_leave_figures_out_but_never_adds_one():
    facts = [Fact("food this month", "₹7,000"), Fact("food last month", "₹4,000")]
    advice = Answer(facts, plain="plain", exhaustive=False)
    assert faithful("Food is up from ₹4,000 to ₹7,000; try cooking at home.", advice, "")
    assert faithful("Try cooking at home more often.", advice, "")
    assert not faithful("Cut food to ₹5,000 next month.", advice, "")
