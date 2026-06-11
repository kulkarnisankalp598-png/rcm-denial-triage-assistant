import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.policy_loader import load_all_policies, chunk_policy_text, extract_metadata
from src.retriever import PolicyRetriever

# --- policy_loader tests ---

def test_load_all_policies_returns_list():
    chunks = load_all_policies()
    assert isinstance(chunks, list)

def test_load_all_policies_count():
    chunks = load_all_policies()
    assert len(chunks) == 36

def test_chunk_has_required_keys():
    chunks = load_all_policies()
    for chunk in chunks:
        assert 'text' in chunk
        assert 'source' in chunk
        assert 'section' in chunk
        assert 'payer' in chunk
        assert 'topic' in chunk
        assert 'effective_date' in chunk

def test_chunk_text_not_empty():
    chunks = load_all_policies()
    for chunk in chunks:
        assert chunk['text'].strip() != ''

def test_payer_extracted_correctly():
    chunks = load_all_policies()
    for chunk in chunks:
        assert chunk['payer'] == 'SyntheticPayerA'

def test_effective_date_extracted():
    chunks = load_all_policies()
    for chunk in chunks:
        assert chunk['effective_date'] == '2026-01-01'

def test_all_six_policy_files_loaded():
    chunks = load_all_policies()
    sources = set(c['source'] for c in chunks)
    assert 'synthetic_missing_information_policy.txt' in sources
    assert 'synthetic_medical_necessity_policy.txt' in sources
    assert 'synthetic_modifier_25_policy.txt' in sources
    assert 'synthetic_bundled_services_policy.txt' in sources
    assert 'synthetic_duplicate_claims_policy.txt' in sources
    assert 'synthetic_deductible_coinsurance_policy.txt' in sources

def test_extract_metadata():
    text = "Payer: TestPayer\nTopic: Test Topic\nEffective Date: 2026-01-01"
    payer, topic, effective_date = extract_metadata(text)
    assert payer == 'TestPayer'
    assert topic == 'Test Topic'
    assert effective_date == '2026-01-01'

# --- retriever tests ---

@pytest.fixture(scope='module')
def retriever():
    return PolicyRetriever()

def test_retriever_initializes(retriever):
    assert retriever is not None
    assert len(retriever.chunks) == 36

def test_retrieve_returns_list(retriever):
    results = retriever.retrieve("missing information claim denial")
    assert isinstance(results, list)

def test_retrieve_top_k(retriever):
    results = retriever.retrieve("missing information", top_k=3)
    assert len(results) <= 3

def test_retrieve_has_score(retriever):
    results = retriever.retrieve("missing information")
    for r in results:
        assert 'score' in r
        assert r['score'] >= 0

def test_retrieve_carc_16_finds_missing_info_policy(retriever):
    results = retriever.retrieve_for_denial(
        carc='16',
        rarc='MA130',
        carc_meaning='Claim/service lacks information or has submission/billing error(s).',
        short_description='Missing information'
    )
    sources = [r['source'] for r in results]
    assert any('missing_information' in s for s in sources)

def test_retrieve_carc_50_finds_medical_necessity_policy(retriever):
    results = retriever.retrieve_for_denial(
        carc='50',
        rarc='N20',
        carc_meaning="These are non-covered services because this is not deemed a medical necessity by the payer.",
        short_description='Service not medically necessary'
    )
    sources = [r['source'] for r in results]
    assert any('medical_necessity' in s for s in sources)

def test_retrieve_carc_97_finds_bundled_policy(retriever):
    results = retriever.retrieve_for_denial(
        carc='97',
        rarc='M15',
        carc_meaning="The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated.",
        short_description='Service bundled'
    )
    sources = [r['source'] for r in results]
    assert any('bundled' in s for s in sources)

def test_retrieve_carc_1_finds_deductible_policy(retriever):
    results = retriever.retrieve_for_denial(
        carc='1',
        rarc='N4',
        carc_meaning="Deductible Amount.",
        short_description='Deductible amount'
    )
    sources = [r['source'] for r in results]
    assert any('deductible' in s for s in sources)

def test_retrieve_carc_4_finds_modifier_policy(retriever):
    results = retriever.retrieve_for_denial(
        carc='4',
        rarc='N130',
        carc_meaning="The procedure code is inconsistent with the modifier used.",
        short_description='Service inconsistent with modifier'
    )
    sources = [r['source'] for r in results]
    assert any('modifier' in s for s in sources)

def test_retrieve_returns_metadata(retriever):
    results = retriever.retrieve("medical necessity")
    for r in results:
        assert 'source' in r
        assert 'section' in r
        assert 'topic' in r
        assert 'payer' in r

def test_retrieve_top_1(retriever):
    results = retriever.retrieve("missing information", top_k=1)
    assert len(results) == 1

def test_retrieve_empty_query_does_not_crash(retriever):
    results = retriever.retrieve("")
    assert isinstance(results, list)