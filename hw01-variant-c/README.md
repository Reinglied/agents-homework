# ДЗ 1 — вариант C: direct и OpenSpec

Сравнение первого результата и двух раундов исправлений при прямом задании и разработке через OpenSpec на одинаковой ограниченной доработке учебного агента.

**[Итоговый отчёт](REPORT.md)** содержит методику, результаты, ресурсы и ограничения эксперимента. Первые версии решили полностью 10/15 (direct) и 9/15 (with-spec) LIVE-задач; после двух раундов — 10/15 и 15/15. Это один опыт, без основания обобщать преимущество подхода.

## Материалы

- `ready/direct/`, `ready/with-spec/` — финальные реализации после второго раунда; OpenSpec находится в `ready/with-spec/openspec/`.
- `snapshots/` — исходные материалы, первые версии, документы и оба раунда с манифестами SHA-256; код каждой версии находится в `payload/`.
- `protocol.md`, `contract.md`, `matrix.md` — протокол, контракт и тестовая матрица.
- `prompts/`, `ready/*/evidence/` и evidence внутри снимков — доступные поручения, журналы и самоотчёты; полных экспортов чатов нет.
- `quality/`, `evaluator/` — публичные и внешние тесты, результаты и оценки по LIVE-рубрике.
- `live-results/` — исходные трассы всех серий, включая отменённые сетевые попытки.
- `PREPARATION-README.md`, `LAUNCH.md` — исторические инструкции подготовки, их статусы относятся к моменту до запуска.

## Запуск

Нужен Python 3.11+ и стандартная библиотека; фактически проверки выполнялись Python 3.14. Ключ вводится скрыто при LIVE; REPLAY и STUB не требуют сети.

Из папки `hw01-variant-c`:

```powershell
python -B -X utf8 quality/harness.py --agent ready/direct --cases quality/public.json --output direct-public.json
python -B -X utf8 quality/harness.py --agent ready/with-spec --cases quality/public.json --output spec-public.json
python -B -X utf8 quality/harness.py --agent ready/direct --cases evaluator/external.json --output direct-external.json
python -B -X utf8 quality/harness.py --agent ready/with-spec --cases evaluator/external.json --output spec-external.json
python -B -X utf8 ready/direct/agent.py --replay --output direct-replay.json
python -B -X utf8 ready/with-spec/agent.py --replay --output spec-replay.json
python -B -X utf8 ready/direct/agent.py --question "Какие OCR и API поддерживает DemoDesk?" --output direct-live.json
python -B -X utf8 ready/with-spec/agent.py --question "Какие OCR и API поддерживает DemoDesk?" --output spec-live.json
python -B -X utf8 snapshot.py verify snapshots/direct-first
python -B -X utf8 snapshot.py verify snapshots/with-spec-first
```

Для строгой проверки документов установить OpenSpec CLI 2.0.0 и из `ready/with-spec` выполнить `openspec validate --all --strict --json --no-interactive`.

Старые организаторские anchors и команды в логах сохраняют абсолютные пути исходного компьютера. Для повторной проверки переносимых снимков используйте `snapshot.py verify` с относительным путём. Сценарий `run_live.py` и инфраструктура исходного эксперимента сохранены для аудита; массовый повтор требует настройки путей anchors для новой машины и образует новую серию.

Манифесты и содержимое снимков сохранены без изменений. Из экспортируемого рабочего дерева исключены только дублирующие папки `work` и кеши вне снимков. Пилотный архив и бинарник OpenSpec в публикацию не включены. Исходная инструкция преподавателя не перепубликовывается; соответствие варианту C описано в `preflight-review.md`.
