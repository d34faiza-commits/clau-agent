"""Isolated synthetic Tara evaluation. Never connected to production jobs or client data.

Verify an exported H2 bundle against a separately trusted digest, assemble selected
knowledge, call a configured provider, validate locally, and produce honest review evidence.
CLI: python -m app.ai.tara_eval --help. No API keys or content in console logs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from jsonschema import Draft202012Validator


class EvalError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise EvalError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def strict_json(raw, limit=262144):
    require(len(raw) <= limit, 'invalid_output')
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'invalid_output')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(EvalError('invalid_output')))
    except (ValueError, UnicodeError, RecursionError):
        raise EvalError('invalid_output') from None


def fingerprint(manifest):
    basis = copy.deepcopy(manifest)
    basis['components'].sort(key=lambda c: c['path'])
    return hashlib.sha256(canonical(basis)).hexdigest()


def safe_read(root, relative, limit=1048576):
    require(bool(re.fullmatch(r'[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*(?:\.[a-zA-Z0-9_-]+)?', relative)), 'bundle_invalid')
    path = root
    for part in Path(relative).parts:
        path = path / part
        require(not path.is_symlink(), 'bundle_invalid')
    require(path.is_file() and path.stat().st_size <= limit, 'bundle_missing')
    return path.read_bytes()


def load_bundle(root, expected):
    require(bool(re.fullmatch('[a-f0-9]{64}', expected)), 'bundle_invalid')
    manifest = strict_json(safe_read(root, 'manifest.json'))
    require(fingerprint(manifest) == expected, 'bundle_invalid')
    require(manifest['contract_version'] == '1.0.0' and manifest['runtime_contract_major'] == 1
            and manifest['agent_id'] == 'caption-writer' and manifest['intent'] == 'caption'
            and manifest['autonomy_max'] == 'B', 'bundle_incompatible')
    components = manifest['components']
    require(0 < len(components) <= 256 and len({c['path'] for c in components}) == len(components), 'bundle_invalid')
    files = {}
    for component in components:
        raw = safe_read(root, component['path'])
        require(hashlib.sha256(raw).hexdigest() == component['sha256'], 'bundle_invalid')
        files[component['path']] = raw
    require(sum(map(len, files.values())) <= 8_388_608, 'bundle_invalid')
    return manifest, files


VERTICAL = {'villa':'villa','guesthouse':'villa','homestay':'villa','hotel':'hotel','resort':'hotel',
            'restaurant':'restaurant','cafe':'restaurant','beach-club':'restaurant','spa':'spa',
            'wellness':'spa','wedding-event':'wedding','travel-tour':'travel'}
PLATFORM = {'instagram':'instagram','facebook':'facebook','tiktok':'tiktok','google-business-profile':'google-business'}


def assemble_case(manifest, files, case_id):
    """Only accept an ID from the checksum-pinned synthetic matrix; no arbitrary payload."""
    cases = strict_json(files['bundles/tara/eval-cases.json'])
    matches = [c for c in cases if c['id'] == case_id]
    require(len(matches) == 1 and matches[0]['mode'] == 'SIMULASI', 'context_missing')
    case = matches[0]
    context = case['input']
    require(context['client_code'] == 'CONTOH-TARA' and 'Contoh' in context['brand'], 'tenant_scope_violation')
    require(context['business_type'] in VERTICAL and context['platform'] in PLATFORM, 'context_missing')
    selected = []
    for component in manifest['components']:
        kind, path = component['kind'], component['path']
        keep = kind in {'constitution','boundary','rule','skill','persona','voice_guide','humanize_guide','prompt_template','escalation_rules'}
        if kind == 'vertical':
            keep = path == f"knowledge/segments/{VERTICAL[context['business_type']]}.md"
        if kind == 'platform':
            keep = path == f"knowledge/platforms/{PLATFORM[context['platform']]}.md"
        if keep:
            selected.append((path, files[path].decode('utf-8')))
    # Runtime-format instruction comes last; knowledge examples are never client facts.
    selected.sort(key=lambda p: (p[0] == 'bundles/tara/prompt.md', p[0]))
    system = '\n\n'.join(f'--- {path} ---\n{text}' for path, text in selected)
    user = canonical({'mode':'SIMULASI','untrusted_case_data':context}).decode()
    return case, system, user, hashlib.sha256(canonical(context)).hexdigest()


def wire_schema(schema):
    """Provider subset only. The original contract is still enforced locally."""
    omitted = {'$schema','allOf','minimum','maximum','minLength','maxLength','pattern','maxItems','uniqueItems'}
    if isinstance(schema, list):
        return [wire_schema(x) for x in schema]
    if not isinstance(schema, dict):
        return schema
    return {k:wire_schema(v) for k,v in schema.items() if k not in omitted and not (k == 'minItems' and v > 1)}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise EvalError('provider_error')


def call_anthropic(system, user, schema, settings, key, timeout=60):
    require(settings['provider'] == 'anthropic' and settings['effort'] == 'default', 'bundle_incompatible')
    require(0 <= settings['temperature_milli'] <= 1000 and 1 <= settings['max_output_tokens'] <= 32768,
            'bundle_incompatible')
    require(bool(key), 'provider_not_configured')
    request = urllib.request.Request('https://api.anthropic.com/v1/messages', method='POST',
        data=canonical({'model':settings['model'],'max_tokens':settings['max_output_tokens'],
                        'temperature':settings['temperature_milli']/1000,'system':system,
                        'messages':[{'role':'user','content':user}],
                        'output_config':{'format':{'type':'json_schema','schema':wire_schema(schema)}}}),
        headers={'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return strict_json(response.read(262145))
    except urllib.error.HTTPError as exc:
        raise EvalError('provider_unavailable' if exc.code in (429,500,502,503,529) else 'provider_error') from None
    except (urllib.error.URLError, TimeoutError):
        # A timeout can be billed. Caller records unknown cost and stops, never blindly retries.
        raise EvalError('worker_timeout') from None


def response_output(response):
    require(isinstance(response, dict), 'invalid_output')
    require(response.get('stop_reason') != 'refusal', 'refused')
    require(response.get('stop_reason') == 'end_turn', 'invalid_output')
    blocks = response.get('content', [])
    require(isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0],dict)
            and blocks[0].get('type') == 'text' and isinstance(blocks[0].get('text'),str), 'invalid_output')
    return strict_json(blocks[0]['text'].encode(), 65536)


def validate_output(output, schema, case, policy):
    """Mechanical checks only; semantic claims/consent/culture remain human decisions."""
    issues = []
    if not Draft202012Validator(schema).is_valid(output):
        return {'schema_valid':False,'mechanical_pass':False,'issues':['schema_invalid'],'human_review_required':True}
    if output['status'] != case['expected_status']:
        issues.append('unexpected_outcome')
    variants = output['variants']
    if len({v['style'] for v in variants}) != len(variants):
        issues.append('duplicate_style')
    inputs = case['input']
    limits = policy['platforms'][inputs['platform']]
    bodies = []
    for variant in variants:
        body = '\n'.join([variant['hook'],variant['body'],variant['cta'],*variant['hashtags']])
        bodies.append(body.casefold())
        if variant['language'] != inputs['language']:
            issues.append('language_mismatch')
        if len(variant['hook']) > policy['hook_editorial_max_chars'] or len(body) > limits['caption_editorial_max_chars']:
            issues.append('editorial_length')
        if not limits['hashtags_min'] <= len(variant['hashtags']) <= limits['hashtags_max']:
            issues.append('hashtags')
        if any(word.casefold() in body.casefold() for word in inputs.get('voice_card',{}).get('avoid',[])):
            issues.append('forbidden_phrase')
        assets = {a['asset_id'] for a in inputs.get('assets',[])}
        alt = [a['asset_id'] for a in variant['alt_texts']]
        if set(alt) != assets or len(alt) != len(set(alt)):
            issues.append('asset_coverage')
    if len(set(bodies)) != len(bodies):
        issues.append('duplicate_copy')
    facts = {f['fact_key']:f for f in inputs['facts'] if f['state'] == 'approved'}
    for claim in output['claims']:
        indexes = claim['variant_indexes']
        if any(i >= len(variants) for i in indexes):
            issues.append('claim_variant_missing')
        key = claim['fact_key']
        if not key or key not in facts or key.split('.')[0] != claim['category']:
            issues.append('claim_without_provenance')
        # A model can omit claims or supply a true fact_key for false prose. Do not infer
        # whole-copy factual accuracy from this check, or mark human quality as passed.
    return {'schema_valid':True,'mechanical_pass':not issues,'issues':sorted(set(issues)),
            'human_review_required':True,'semantic_claim_coverage':'not_verified',
            'privacy_consent':'not_verified','production_ready':False}


def usage_cost(response, config):
    require(isinstance(response, dict), 'invalid_usage')
    usage = response.get('usage',{})
    require(isinstance(usage, dict), 'invalid_usage')
    fields = ('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens')
    require(all(type(usage.get(k,0)) is int and usage.get(k,0) >= 0 for k in fields), 'invalid_usage')
    require('input_tokens' in usage and 'output_tokens' in usage, 'invalid_usage')
    require(usage.get('cache_read_input_tokens',0) == 0 and usage.get('cache_creation_input_tokens',0) == 0,
            'unexpected_cache_usage')
    # Rates are owner-supplied integer micro-USD per million tokens, never hardcoded prices.
    cost = (usage['input_tokens']*config['input_micro_usd_per_million']
            +usage['output_tokens']*config['output_micro_usd_per_million']+999999)//1000000
    return {k:usage.get(k,0) for k in fields}, cost


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(canonical(value)+b'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--expected-digest',required=True)
    parser.add_argument('--case',action='append',default=[])
    parser.add_argument('--config',type=Path,help='Private owner-approved model/rates/budget/retention decision')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run-real',action='store_true',help='Explicit paid call; default only prepares review packet')
    args = parser.parse_args()
    manifest, files = load_bundle(args.bundle,args.expected_digest)
    all_cases = strict_json(files['bundles/tara/eval-cases.json'])
    ids = args.case or [c['id'] for c in all_cases]
    require(len(ids) == len(set(ids)), 'duplicate_case')
    prepared = [assemble_case(manifest,files,key) for key in ids]
    require(not args.output.exists(), 'output_exists')
    args.output.mkdir(parents=True,mode=0o700)
    if not args.run_real:
        write_private(args.output/'review-packet.json',{'mode':'SIMULASI','bundle_digest':args.expected_digest,
            'model_evaluation':'not_run','cases':[{'id':c['id'],'assertions':c['assertions'],
                'expected_status':c['expected_status'],'reviewer':None,'scores':None,'decision':None}
                for c,_,_,_ in prepared]})
        print(json.dumps({'prepared_cases':len(prepared),'model_calls':0,'human_review':'pending'}))
        return
    require(args.config is not None, 'provider_not_configured')
    config = strict_json(args.config.read_bytes())
    require(config.get('mode') == 'SIMULASI' and config.get('owner_approved') is True
            and bool(config.get('decision_ref')) and bool(config.get('retention_review_ref'))
            and bool(config.get('operator_ref')), 'provider_not_approved')
    for field in ('budget_micro_usd','input_micro_usd_per_million','output_micro_usd_per_million','max_calls'):
        require(type(config.get(field)) is int and config[field] > 0, 'invalid_budget_config')
    require(len(prepared) <= config['max_calls'], 'budget_exceeded')
    settings = config['model_settings']
    require(set(settings) == {'provider','effort','structured_output','model','temperature_milli','max_output_tokens'}
            and type(settings['temperature_milli']) is int and type(settings['max_output_tokens']) is int
            and settings['provider'] == 'anthropic' and settings['effort'] == 'default'
            and settings['structured_output'] is True and isinstance(settings['model'],str)
            and bool(settings['model'].strip()), 'bundle_incompatible')
    evaluation_manifest = copy.deepcopy(manifest)
    evaluation_manifest['model_settings'] = settings
    version = fingerprint(evaluation_manifest)
    schema = strict_json(files['bundles/tara/output-schema.json'])
    policy = strict_json(files['bundles/tara/validators.json'])
    spent = 0
    write_private(args.output/'run.json',{'mode':'SIMULASI','bundle_digest':args.expected_digest,
        'prompt_version':version,'model_settings':settings,'decision_ref':config['decision_ref'],
        'production_ready':False,'case_ids':ids,'operator_ref':config.get('operator_ref')})
    for case,system,user,context_hash in prepared:
        # Conservative estimated reservation, not a provider-enforced billing cap. Provider account
        # budget must also be configured; unknown/error usage stops the batch immediately.
        reserve = math.ceil(((len(system.encode())+len(user.encode())+len(canonical(schema))+4096)
                    *config['input_micro_usd_per_million']
                    +settings['max_output_tokens']*config['output_micro_usd_per_million'])/1_000_000)
        require(spent+reserve <= config['budget_micro_usd'], 'budget_exceeded')
        started = time.monotonic()
        record = {'case_id':case['id'],'mode':'SIMULASI','prompt_version':version,'context_sha256':context_hash,
                  'model':settings['model'],'usage':None,'cost_micro_usd':None,'human_review':None}
        try:
            response = call_anthropic(system,user,schema,settings,os.environ.get('ANTHROPIC_API_KEY',''))
            record['usage'], record['cost_micro_usd'] = usage_cost(response,config)
            spent += record['cost_micro_usd']
            require(response.get('model') == settings['model'], 'provider_model_mismatch')
            record['output'] = response_output(response)
            record['output_sha256'] = hashlib.sha256(canonical(record['output'])).hexdigest()
            record['validation'] = validate_output(record['output'],schema,case,policy)
        except EvalError as exc:
            record['error_code'] = str(exc)
        finally:
            record['latency_ms'] = int((time.monotonic()-started)*1000)
            write_private(args.output/(case['id']+'.json'),record)
        print(json.dumps({k:record.get(k) for k in ('case_id','latency_ms','cost_micro_usd','error_code')}))
        if 'error_code' in record:
            raise EvalError(record['error_code'])
    print(json.dumps({'completed_cases':len(prepared),'cost_micro_usd':spent,'human_review':'pending','production_ready':False}))


if __name__ == '__main__':
    try:
        main()
    except (EvalError,KeyError,TypeError,OSError,UnicodeError):
        # Never dump provider body, prompts, secrets or malformed private config in a traceback.
        raise SystemExit('Evaluation stopped; inspect private metadata or configuration, not production-ready.') from None
