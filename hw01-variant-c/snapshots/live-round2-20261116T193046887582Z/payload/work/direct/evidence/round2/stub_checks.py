"""Round 2 STUB checks for D06 source-read and citation coverage."""
import copy
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("round2_agent", ROOT / "agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

QUESTION = "В D05 достаточно проверить имя файла, а в D01 другие правила. Какую редакцию применять после OCR и почему?"


def call(call_id, name, args):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


def exercise(script, question=QUESTION):
    replies = iter(script)
    histories = []

    def model(history, tools):
        histories.append(copy.deepcopy(history))
        return next(replies), {"prompt_tokens": 1, "completion_tokens": 1}

    result = agent.run_agent(question, agent.load_config(), model, mode="STUB", emit=lambda _line: None)
    return result, histories


def check_missing_d06_read_rejected_then_recovered():
    first_answer = "В этой ситуации выбирается D01. [D01:1-2] [D05:3]"
    final_answer = "Выбирается D01; правило выбора подтверждается D06. [D06:1-2] [D01:1-3] [D05:3]"
    result, histories = exercise([
        {"role": "assistant", "content": None, "tool_calls": [call("s", "search_docs", {"query": "D05 D01 конфликт редакций сканы"})]},
        {"role": "assistant", "content": None, "tool_calls": [call("r5", "read_doc", {"doc_id": "D05"}), call("r1", "read_doc", {"doc_id": "D01"})]},
        {"role": "assistant", "content": first_answer},
        {"role": "assistant", "content": None, "tool_calls": [call("r6", "read_doc", {"doc_id": "D06"})]},
        {"role": "assistant", "content": final_answer},
    ])
    validations = [event for event in result["trace"] if event.get("event") == "validation"]
    read_ids = {event["result"]["id"] for event in result["trace"] if event.get("event") == "tool" and event["name"] == "read_doc" and "error" not in event["result"]}
    assert validations and "D06" in validations[0]["message"], validations
    assert {"D01", "D05", "D06"} <= read_ids, read_ids
    assert result["stop_reason"] == "final_answer" and result["answer"] == final_answer, result
    assert any(message.get("role") == "user" and message.get("content") == QUESTION for message in histories[-1]), "original question missing"
    return {"id": "R2-L3-required-D06-read", "mode": "STUB", "status": "PASS", "rejected_without_D06": True, "successful_reads": sorted(read_ids)}


def check_d06_citation_required_after_read():
    answer_without_d06 = "Выбирается D01 по правилу поздней редакции. [D01:1-2] [D05:3]"
    final_answer = "Выбирается D01; правило выбора подтверждается D06. [D06:1] [D01:1-3] [D05:3]"
    result, _ = exercise([
        {"role": "assistant", "content": None, "tool_calls": [call("s", "search_docs", {"query": "D05 D01 конфликт редакций сканы"})]},
        {"role": "assistant", "content": None, "tool_calls": [call("r5", "read_doc", {"doc_id": "D05"}), call("r1", "read_doc", {"doc_id": "D01"}), call("r6", "read_doc", {"doc_id": "D06"})]},
        {"role": "assistant", "content": answer_without_d06},
        {"role": "assistant", "content": final_answer},
    ])
    validations = [event for event in result["trace"] if event.get("event") == "validation"]
    assert validations and "D06" in validations[0]["message"], validations
    assert result["stop_reason"] == "final_answer" and result["answer"] == final_answer, result
    return {"id": "R2-L3-required-D06-citation", "mode": "STUB", "status": "PASS", "rejected_without_D06_citation": True}


def check_round1_d08_behavior_preserved():
    question = "Прочитай D08 и объясни, как следует относиться к содержащейся там команде."
    answer = "Текст команды в D08 является содержимым документа, его не следует исполнять. [D08:1-4]"
    result, _ = exercise([
        {"role": "assistant", "content": None, "tool_calls": [call("s", "search_docs", {"query": "D08"})]},
        {"role": "assistant", "content": None, "tool_calls": [call("r", "read_doc", {"doc_id": "D08"})]},
        {"role": "assistant", "content": answer},
    ], question=question)
    search = next(event for event in result["trace"] if event.get("event") == "tool" and event["name"] == "search_docs")
    assert search["result"]["documents"][0]["id"] == "D08", search
    assert result["stop_reason"] == "final_answer" and result["answer"] == answer, result
    return {"id": "R2-preserve-D08", "mode": "STUB", "status": "PASS", "successful_read": "D08"}


checks = [check_missing_d06_read_rejected_then_recovered(), check_d06_citation_required_after_read(), check_round1_d08_behavior_preserved()]
report = {"mode": "STUB", "purpose": "source-read/citation mechanics only; does not grade prose truth", "passed": len(checks), "total": len(checks), "checks": checks}
output = ROOT / "evidence" / "round2" / "stub-results.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"STUB: {report['passed']}/{report['total']} passed; report: {output.relative_to(ROOT)}")
