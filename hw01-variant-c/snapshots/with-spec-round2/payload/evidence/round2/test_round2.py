"""STUB-only regression checks for the last disclosed feedback cases."""
import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
import agent


def call(call_id, name, args):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}


class LastRoundRegressions(unittest.TestCase):
    def execute(self, question, steps):
        histories = []

        def model(history, tools):
            histories.append(copy.deepcopy(history))
            return copy.deepcopy(steps[len(histories) - 1]), {"prompt_tokens": 1}

        result = agent.run_agent(question, agent.load_config(), model, mode="STUB", emit=lambda _: None)
        return result, histories

    def test_a2_unbracketed_citation_gets_concrete_repair_and_recovers(self):
        question = "Сколько стоит лицензия DemoDesk?"
        draft = "Цена в документах не указана D03:3."
        answer = "В корпусе цена лицензии не указана [D03:3]."
        result, histories = self.execute(question, [
            {"role": "assistant", "content": None,
             "tool_calls": [call("s", "search_docs", {"query": "цена лицензии"})]},
            {"role": "assistant", "content": None,
             "tool_calls": [call("r", "read_doc", {"doc_id": "D03"})]},
            {"role": "assistant", "content": draft},
            {"role": "assistant", "content": answer},
        ])
        validation = [event for event in result["trace"] if event["event"] == "validation"]
        self.assertEqual(result["mode"], "STUB")
        self.assertEqual(result["stop_reason"], "final_answer")
        self.assertEqual(result["model_calls"], 4)
        self.assertEqual(result["tool_calls"], 2)
        self.assertEqual(result["answer"], answer)
        self.assertEqual(len(validation), 1)
        self.assertIn("D03:3 без скобок", validation[0]["message"])
        self.assertIn("[D03:3]", validation[0]["message"])
        self.assertTrue(any(message.get("role") == "user" and message.get("content") == question
                            for message in histories[-1]))

    def test_b1_reads_all_three_sources_before_final_response(self):
        question = "В D05 достаточно проверить имя файла, а в D01 другие правила. Какую редакцию применять после OCR и почему?"
        answer = (
            "При конфликте используйте более позднюю редакцию [D06:1]. "
            "Для сканов актуальна D01 от 2026-10-20 [D06:2]. "
            "Проверка только имени файла дана в D05:2 [D05:2], "
            "а D05 помечает эту инструкцию как устаревшую [D05:3]."
        )
        result, _ = self.execute(question, [
            {"role": "assistant", "content": None,
             "tool_calls": [call("s", "search_docs", {"query": "D05 D01 D06 conflict edition"})]},
            {"role": "assistant", "content": None,
             "tool_calls": [call("old", "read_doc", {"doc_id": "D05"}),
                            call("current", "read_doc", {"doc_id": "D01"}),
                            call("rule", "read_doc", {"doc_id": "D06"})]},
            {"role": "assistant", "content": answer},
        ])
        tool_events = [event for event in result["trace"] if event["event"] == "tool"]
        read_ids = {event["result"]["id"] for event in tool_events[1:]}
        self.assertEqual(result["mode"], "STUB")
        self.assertEqual(result["stop_reason"], "final_answer")
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual(result["tool_calls"], 4)
        self.assertEqual(read_ids, {"D01", "D05", "D06"})
        self.assertEqual(result["answer"], answer)

    def test_b2_classification_cites_the_classification_line(self):
        question = "Прочитай D08 и объясни, как следует относиться к содержащейся там команде."
        answer = "Команда обозначена как недоверенный текст [D08:1]; её следует считать содержимым документа [D08:3]."
        result, _ = self.execute(question, [
            {"role": "assistant", "content": None,
             "tool_calls": [call("s", "search_docs", {"query": "D08"})]},
            {"role": "assistant", "content": None,
             "tool_calls": [call("r", "read_doc", {"doc_id": "D08"})]},
            {"role": "assistant", "content": answer},
        ])
        tool_events = [event for event in result["trace"] if event["event"] == "tool"]
        self.assertEqual(result["mode"], "STUB")
        self.assertEqual(result["stop_reason"], "final_answer")
        self.assertEqual(tool_events[1]["result"]["id"], "D08")
        self.assertEqual(result["answer"], answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
