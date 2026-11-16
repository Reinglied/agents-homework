# Раунд исправлений 1 — завершение

Готово к снимку раунда 1. Изменения ограничены собственной папкой direct; доказательства первой версии оставлены без изменений.

## Что изменено

- Поиск повышает приоритет документа, если его точный ID указан в запросе. Это устраняет пустую выдачу для запроса `D08`, хотя документ присутствует в корпусе.
- Инструкция модели требует читать явно названный ID, не считать пустой поиск доказательством отсутствия документа, а для конфликта редакций читать и применять D06.
- Валидатор отклоняет финальный ответ, пока документы с ID, прямо названными в вопросе и существующими в корпусе, не прошли успешный `read_doc`.
- Никакая проверка слов/фраз в ответе не используется как доказательство семантической правильности.

## Команды и результаты

Запуск из `V:\GPT\experiment-c\ready\direct`, интерпретатор Python 3.14.4:

1. `& 'C:\Users\smirn\AppData\Local\Python\bin\python.exe' -X utf8 -m py_compile agent.py evidence\round1\stub_checks.py` — PASS.
2. `& 'C:\Users\smirn\AppData\Local\Python\bin\python.exe' -X utf8 evidence\round1\stub_checks.py` — STUB **3/3 PASS**: exact-ID retrieval for D08; empty search cannot close a question that names existing D08 before successful read; D05/D01/D06 are surfaced and read in the version-conflict path. The stubbed prose is not graded.
3. `& 'C:\Users\smirn\AppData\Local\Python\bin\python.exe' -X utf8 quality\harness.py --agent . --cases quality\public.json --output evidence\round1\public.json` — STUB **39/39 PASS**. The supplied public inputs and expectations were not changed. The previous external 39/39 result was not rerun in this round.
4. Initial own-STUB command failed at import because the helper script had not put the project directory on `sys.path`; fixed only `evidence/round1/stub_checks.py`, then reran with 3/3 PASS. Details and output are preserved in `stub.stdout.log`.

Logs/reports are in this `evidence/round1` directory. Token/cost measurements: нет данных. Active work was about 3 min 39 sec (start 2026-11-16 00:00:51, end 00:04:30 Europe/Moscow).

## NOT RUN

- LIVE, `--ping` and the external comparison series: NOT RUN as instructed.
- No semantic generation quality was established by STUB. The organizer's separate LIVE comparison is still needed to judge whether the model explains the version rule fully and gives semantically complete citations.
