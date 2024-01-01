import os
import requests
import json
import re

from types import SimpleNamespace

import func.rag
import func.chatgpt
import func.llm

import func.var
from func.messages import msg, msgcount

from func.config import cfg

def comment(s):
    return ''

def test(s):
    return s if cfg['is_test'] else ''

def msgf(v: str | list):
    msgs = []

    a = []
    if type(v) is list:
        a = v
    elif type(v) is str:
        a = v.splitlines()

    if cfg['location'] == 'Local':
        return "\n".join(a)
        
    if a:
        for line in a:
            if line.lower().startswith('user:'):
                msgs.append({'role': 'user', 'content': line[5:].strip()})
            elif line.lower().startswith('ai:'):
                msgs.append({'role': 'assistant', 'content': line[3:].strip()})
            elif line.lower().startswith('assistant:'):
                msgs.append({'role': 'assistant', 'content': line[10:].strip()})
            elif line.lower().startswith('system:'):
                msgs.append({'role': 'system', 'content': line[7:].strip()})
            else:
                msgs[-1]['content'] += line
        
    return json.dumps(msgs)

def iif(expr, t, f = ''):
    return t if expr else f

def rag(dir, query):
    args = {
        'dir': dir,
        'query': query,
        'k': 1,
    }
    try:
        vector_store = func.rag.vector_load(args)
        result, detail = func.rag.search(vector_store, args)
        return result
    except Exception as e:
        print(e)
        return ''

def llm(dir, **kwargs):
    try:
        args = dict(kwargs)
        args['dir'] = dir
        return infer(args)
    except Exception as e:
        print(e)
        return ''

def infer_prompt(instruction, input = '', opt = {}):
    var = func.var.load_vars()
    var = SimpleNamespace(**var)

    args = opt.copy()
    args['instruction'] = eval("f'''" + instruction + "'''")
    args['input'] = input

    if opt['location'] == 'Local':
        if 'is_messages' in opt and opt['is_messages']:
            messages = prompt_to_messages(args['instruction'])
            return func.llm.chat(args), json.dumps(messages)
        else:
            return func.llm.chat(args), args['instruction']
    else:
        messages = prompt_to_messages(args['instruction'])
        return func.chatgpt.infer(messages), json.dumps(messages)

def infer(args: dict):
    instruction = load_prompt(args['dir'])
    opt = load_options(args['dir'])
    opt.update(args)

    del opt['dir']
    del opt['input']

    return infer_prompt(instruction, args['input'], opt)

def prompt_to_messages(prompt):
    msgs = []
    s = 0
    for m in re.finditer('\[\{.*?\}\]', prompt):
        system = prompt[s:m.start()].strip()
        if len(system):
            msgs.append({'role': 'system', 'content': system})
        msgs.extend(json.loads(prompt[m.start():m.end()]))
        s = m.end()
    system = prompt[s:].strip()
    if len(system):
        msgs.append({'role': 'system', 'content': system})

    return msgs

def save_options(dir, cfg):
    path = f"prompt/{dir}.json"
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=4)

    return 'saved.'

def load_options(dir):
    path = f"prompt/{dir}.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_prompt(dir, prompt):
    path = f"prompt/{dir}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    return f"saved {path}"

def load_prompts():
    prompts = {}
    for name in os.listdir('prompt'):
        if not name.endswith('.txt'):
            continue
        stem, ext = os.path.splitext(name)
        path = f"prompt/{name}"
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                prompts[stem] = f.read()

    return prompts

def load_prompt(dir):
    path = f"prompt/{dir}.txt"
    if not os.path.exists(path):
        raise ValueError('instruction not found: ' + path)
    with open(path, 'r') as f:
        return f.read()
