"""Organizer-only generator. Freeze JSON outputs before either development."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def call(name, args, identifier):
    return {'id': identifier, 'type': 'function', 'function': {'name': name, 'arguments': args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)}}


def batch(*calls):
    return {'role': 'assistant', 'content': None, 'tool_calls': list(calls)}


def answer(text):
    return {'role': 'assistant', 'content': text}


def cases(external=False):
    prefix = 'X' if external else 'P'
    doc = 'D02' if external else 'D01'
    citation = '(D02:1-2)' if external else '[D01:1-2]'
    valid = ('Уберите чувствительные сведения и проверьте разрешение передачи. ' if external else 'Сначала OCR, затем сверка чисел, дат и имён с изображением. ') + citation
    question = 'Что требуется перед внешним API?' if external else 'Что проверить после OCR?'
    search = batch(call('search_docs', {'query': 'внешний API' if external else 'OCR'}, 's1'))
    read = batch(call('read_doc', {'doc_id': doc}, 'r1'))
    rows = []
    def add(name, req, steps, final=True, overrides=None, config=None, count=None, feedback=False, rejected=None):
        tool_count = sum(len(s.get('tool_calls', [])) for s in steps) if count is None else count
        row = {'id': prefix + '-' + name, 'requirements': req.split(','), 'question': question,
               'steps': steps, 'config': config or {}, 'tool_overrides': overrides or {},
               'expected': {'final': final, 'model_calls': len(steps), 'tool_calls': tool_count}}
        if final: row['expected']['answer'] = steps[-1]['content']
        if name.startswith('arguments-') or name in ('unknown-id','unknown-tool'):
            row['error_tools'] = [2]
        if name == 'failed-search': row['error_tools'] = [1]
        if feedback: row.update(validation_feedback=True, rejected_answer=rejected)
        rows.append(row)
    add('accept-correct', 'A1,M2', [search,read,answer(valid)])
    both = batch(call('read_doc', {'doc_id':'D01'}, 'a'),call('read_doc', {'doc_id':'D02'}, 'b'))
    add('A1-complete', 'A1', [search,both,answer('После OCR проверьте числа, даты и имена по оригиналу [D01:1-2]. Перед API удалите персональные и конфиденциальные сведения и убедитесь в разрешении передачи [D02:1-2].')])
    add('A2-no-price', 'A2', [batch(call('search_docs',{'query':'цена лицензии'},'s')),batch(call('read_doc',{'doc_id':'D03'},'r')),answer('В этом корпусе стоимость лицензии не приведена (D03:3-4).')])
    for i, text in enumerate([valid+' Дата (2026-10-20). Упомянуты D01, [D01] и (D01).',
                               ('Следует свериться с оригиналом [D01:2].' if not external else 'Нужно разрешение передать материал сервису [D02:2].'),
                               valid.replace('[', '(').replace(']', ')')]):
        add('positive-'+str(i),'M3,M2',[search,read,answer(text)])
    malformed = [f'[{doc}:0]',f'[{doc}:3-1]',f'[{doc}:1-999]',f'[{doc}:01]',f'[{doc}:1',f'({doc}:1]',f'[{doc}:1-x]',f'[{doc}:١]']
    if external: malformed = [f'({doc}:0-2)',f'({doc}:4-2)',f'({doc}:50)',f'({doc}:02)',f'({doc}:2',f'[{doc}:2)',f'({doc}:2-)',f'({doc}:２)']
    for i, ref in enumerate(malformed):
        bad = 'Проверка. '+ref
        add('bad-citation-'+str(i),'M2,M3,R3',[search,read,answer(bad),answer(valid)],feedback=True,rejected=bad)
    bad = 'Достоверный ответ [D07:1].'
    add('unread-id','M2,R3',[search,read,answer(bad),answer(valid)],feedback=True,rejected=bad)
    add('snippet-not-read','M4,R3',[search,answer(valid),read,answer(valid)],feedback=True,rejected=valid)
    no_ref = 'Проверьте документ D01 (2026-10-20).'
    add('missing-reference','M5,R3',[search,read,answer(no_ref),answer(valid)],feedback=True,rejected=no_ref)
    add('no-search','M5,R3',[read,answer(valid),search,answer(valid)],feedback=True,rejected=valid)
    add('empty-search','M5',[search,answer('В доступном корпусе сведений не найдено.')],overrides={'1':{'result':{'documents':[]}}})
    add('failed-search','M5,R2',[batch(call('search_docs', {'bad':'x'},'bad')),answer('Нет сведений.'),search,read,answer(valid)],feedback=True,rejected='Нет сведений.')
    wrong_args = ['{','null','[]',json.dumps({'doc_id': ''}),json.dumps({'doc_id': doc,'extra':1}),json.dumps({'doc_id':42})]
    if external: wrong_args = ['[','true','"D01"',json.dumps({'doc_id':'   '}),json.dumps({'query':doc}),json.dumps({'doc_id':None})]
    for i, args in enumerate(wrong_args):
        add('arguments-'+str(i),'A3,R2',[search,batch(call('read_doc',args,'bad')),read,answer(valid)])
    add('unknown-id','A3,R1',[search,batch(call('read_doc',{'doc_id':'D99'},'bad')),read,answer(valid)])
    add('unknown-tool','M1',[search,batch(call('shell',{'command':'never execute'},'bad')),read,answer(valid)])
    secret = 'SYNTHETIC-SECRET-EXTERNAL-82' if external else 'SYNTHETIC-SECRET-PUBLIC-19'
    add('tool-exception-recovery','A4,R1,S1',[search,read,read,answer(valid)],overrides={'2':{'raise':secret}})
    add('tool-exception-stop','A4,A5,R4',[search,read,read],False,overrides={'2':{'raise':secret},'3':{'raise':secret}},config={'max_model_calls':3})
    add('failed-read-no-right','M4,R3',[search,read,answer(valid),read,answer(valid)],overrides={'2':{'result':{'error':{'code':'not_found','message':'Controlled read failure'}}}},feedback=True,rejected=valid)
    sparse = {'id':doc,'title':'Numbered test source','version':'2026-10-20','lines':[{'line':2,'text':'Synthetic line two.'},{'line':4,'text':'Synthetic line four.'}]}
    for name,badref in [('gap',f'[{doc}:2-4]'),('position',f'[{doc}:1]')]:
        bad = 'Строка '+badref
        add('sparse-'+name,'M2,R3',[search,read,answer(bad),answer('Две строки '+f'[{doc}:2] [{doc}:4].')],overrides={'2':{'result':sparse}},feedback=True,rejected=bad)
    add('model-budget','A5',[search],False,config={'max_model_calls':1})
    add('exact-model-budget','A5',[search,read,answer(valid)],config={'max_model_calls':3})
    pair = batch(call('search_docs',{'query':'OCR'},'s'),call('read_doc',{'doc_id':doc},'r'))
    add('exact-tool-budget','A5',[pair,answer(valid)],config={'max_tool_calls':2})
    add('oversized-batch','A5',[pair],False,config={'max_tool_calls':1},count=0)
    add('remaining-budget','A5',[search,pair],False,config={'max_tool_calls':2},count=1)
    add('model-error','M6',[search,{'raise_model':True}],False)
    return rows


if __name__ == '__main__':
    for external, file in [(False,ROOT/'quality/public.json'),(True,ROOT/'evaluator/external.json')]:
        file.parent.mkdir(parents=True,exist_ok=True)
        data=cases(external)
        file.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(file.name,len(data))
