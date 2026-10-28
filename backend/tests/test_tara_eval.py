"""Isolated staging runner tests. No network, provider bill or client data."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.ai import tara_eval as t
from app.ai import tara_eval_report as report


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"n":NaN}',b'{"n":Infinity}',b'not-json'])
def test_strict_json(raw):
    with pytest.raises(t.EvalError):
        t.strict_json(raw)


def test_size_before_parse():
    with pytest.raises(t.EvalError):
        t.strict_json(b' ' * 65537,65536)


def artifact(tmp_path):
    case = {'id':'tara-001','mode':'SIMULASI','input':{'client_code':'CONTOH-TARA','brand':'Villa Contoh',
        'business_type':'villa','platform':'instagram','facts':[]},'assertions':['no_invented_facts']}
    content = {'bundles/tara/eval-cases.json':t.canonical([case]),
               'bundles/tara/prompt.md':b'Only drafts',
               'knowledge/segments/villa.md':b'Villa knowledge',
               'knowledge/segments/spa.md':b'Spa knowledge',
               'knowledge/platforms/instagram.md':b'Instagram knowledge',
               'knowledge/platforms/facebook.md':b'Facebook knowledge'}
    kinds = ['validator_config','prompt_template','vertical','vertical','platform','platform']
    manifest = {'contract_version':'1.0.0','runtime_contract_major':1,'agent_id':'caption-writer',
                'intent':'caption','autonomy_max':'B','components':[]}
    for (path,raw),kind in zip(content.items(),kinds):
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        manifest['components'].append({'path':path,'kind':kind,'sha256':hashlib.sha256(raw).hexdigest()})
    (tmp_path/'manifest.json').write_bytes(t.canonical(manifest))
    return manifest,t.fingerprint(manifest)


def test_load_selects_only_relevant_knowledge_and_hashes_context(tmp_path):
    _, digest = artifact(tmp_path)
    manifest,files = t.load_bundle(tmp_path,digest)
    case,system,user,context_hash = t.assemble_case(manifest,files,'tara-001')
    assert 'Villa knowledge' in system and 'Instagram knowledge' in system
    assert 'Spa knowledge' not in system and 'Facebook knowledge' not in system
    assert len(context_hash) == 64 and 'untrusted_case_data' in user
    with pytest.raises(t.EvalError):
        t.assemble_case(manifest,files,'OTHER-CLIENT')


def test_tamper_wrong_digest_and_symlink_fail_closed(tmp_path):
    _,digest=artifact(tmp_path)
    with pytest.raises(t.EvalError):t.load_bundle(tmp_path,'0'*64)
    path=tmp_path/'bundles/tara/prompt.md'
    path.write_bytes(b'tampered')
    with pytest.raises(t.EvalError):t.load_bundle(tmp_path,digest)
    path.unlink();path.symlink_to(tmp_path/'manifest.json')
    with pytest.raises(t.EvalError):t.load_bundle(tmp_path,digest)
    with pytest.raises(t.EvalError):t.safe_read(tmp_path,'../escape')


def test_cross_client_input_is_rejected_even_in_test_artifact(tmp_path):
    manifest,digest=artifact(tmp_path)
    _,files=t.load_bundle(tmp_path,digest)
    cases=t.strict_json(files['bundles/tara/eval-cases.json'])
    cases[0]['input']['client_code']='OTHER'
    files['bundles/tara/eval-cases.json']=t.canonical(cases)
    with pytest.raises(t.EvalError,match='tenant_scope_violation'):
        t.assemble_case(manifest,files,'tara-001')


@pytest.mark.parametrize('reason',['refusal','max_tokens','tool_use',None])
def test_non_end_turn_is_not_a_complete_generation(reason):
    with pytest.raises(t.EvalError):t.response_output({'stop_reason':reason,'content':[{'type':'text','text':'{}'}]})


def test_usage_is_integer_and_unknown_is_not_zero():
    cfg={'input_micro_usd_per_million':3000000,'output_micro_usd_per_million':15000000}
    usage,cost=t.usage_cost({'usage':{'input_tokens':100,'output_tokens':20}},cfg)
    assert cost == 600 and usage['input_tokens'] == 100
    for bad in ({},{'usage':{}},{'usage':{'input_tokens':True,'output_tokens':0}},
                {'usage':{'input_tokens':10,'output_tokens':1,'cache_creation_input_tokens':5}}):
        with pytest.raises(t.EvalError):t.usage_cost(bad,cfg)


def test_provider_endpoint_redirect_policy_and_wire_schema():
    with pytest.raises(t.EvalError):t.NoRedirect().redirect_request(None,None,None,None,None,None)
    settings={'provider':'anthropic','effort':'default','temperature_milli':0,'max_output_tokens':100,'model':'model-snapshot'}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            assert limit == 262145
            return b'{"stop_reason":"end_turn","content":[{"type":"text","text":"{}"}]}'
    with patch.object(t.urllib.request,'build_opener') as mocked:
        mocked.return_value.open.return_value=Response()
        t.call_anthropic('system','synthetic',{'type':'string','maxLength':10},settings,'test-only-key')
        request=mocked.return_value.open.call_args.args[0]
        assert request.full_url == 'https://api.anthropic.com/v1/messages'
        payload=json.loads(request.data)
        assert payload['output_config']['format']['schema'] == {'type':'string'}
        assert payload['model'] == 'model-snapshot'


def test_output_artifacts_do_not_overwrite(tmp_path):
    p=tmp_path/'result.json';t.write_private(p,{'mode':'SIMULASI'})
    assert p.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):t.write_private(p,{'mode':'changed'})


def test_incomplete_run_never_looks_like_perfect_eval(tmp_path):
    t.write_private(tmp_path/'run.json',{'case_ids':[f'tara-{i:03}' for i in range(1,61)],
                                      'prompt_version':'x','operator_ref':'operator'})
    t.write_private(tmp_path/'tara-001.json',{'case_id':'tara-001','prompt_version':'x',
                  'validation':{'schema_valid':True,'mechanical_pass':True},'cost_micro_usd':None,
                  'latency_ms':20,'human_review':None})
    result=report.summarize(tmp_path)
    assert result['schema_valid_rate'] == 1/60
    assert result['missing'] == 59 and result['human_average'] is None
    assert result['calls_with_unknown_cost'] == 1
    assert result['regression_gate_pass'] is False and result['production_ready'] is False


def test_modified_output_invalidates_human_review(tmp_path):
    t.write_private(tmp_path/'run.json',{'case_ids':['tara-001'],'prompt_version':'x','operator_ref':'operator'})
    t.write_private(tmp_path/'tara-001.json',{'case_id':'tara-001','prompt_version':'x','output':{},
         'output_sha256':'old','human_review':{'output_sha256':'old','reviewer_ref':'reviewer'}})
    with pytest.raises(t.EvalError,match='review_output_mismatch'):report.summarize(tmp_path)
