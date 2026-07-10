import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retriever import PolicyRetriever

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def precision_at_k(results, expected_topic, k=3):
    """
    Check if the expected topic appears in the top-k results.
    Returns 1 if found, 0 if not.
    """
    top_k = results[:k]
    for r in top_k:
        if expected_topic.lower() in r['topic'].lower():
            return 1
    return 0


def run_evaluation(eval_file='data/retrieval_eval.json', top_k=3):
    """
    Run retrieval evaluation against all seed cases.
    Returns a dict with precision@k, pass/fail per case, and summary.
    """
    with open(eval_file) as f:
        cases = json.load(f)

    retriever = PolicyRetriever()
    results = []
    hits = 0

    for case in cases:
        retrieved = retriever.retrieve_for_denial(
            carc=case['carc'],
            rarc=case['rarc'],
            carc_meaning=case['carc_meaning'],
            short_description=case['short_description'],
            top_k=top_k
        )

        hit = precision_at_k(retrieved, case['expected_topic'], k=top_k)
        hits += hit

        top_sources = [r['source'] for r in retrieved]
        top_topics = [r['topic'] for r in retrieved]
        top_scores = [r['score'] for r in retrieved]

        results.append({
            'case_id': case['case_id'],
            'claim_id': case['claim_id'],
            'carc': case['carc'],
            'expected_topic': case['expected_topic'],
            'top_retrieved_topics': top_topics,
            'top_scores': top_scores,
            'hit': hit == 1,
        })

        status = "✅ HIT" if hit == 1 else "❌ MISS"
        logger.info(f"{status} | {case['case_id']} | CARC {case['carc']} | Expected: {case['expected_topic']}")

    precision = hits / len(cases)

    summary = {
        'total_cases': len(cases),
        'hits': hits,
        'misses': len(cases) - hits,
        'precision_at_k': round(precision, 3),
        'top_k': top_k,
        'verdict': 'PASS' if precision >= 0.75 else 'NEEDS IMPROVEMENT'
    }

    return summary, results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RETRIEVAL EVALUATION — TF-IDF BASELINE")
    print("="*60 + "\n")

    summary, results = run_evaluation()

    print("\n" + "="*60)
    print("RESULTS PER CASE")
    print("="*60)
    for r in results:
        status = "✅" if r['hit'] else "❌"
        print(f"{status} {r['case_id']} | CARC {r['carc']} | Top topic: {r['top_retrieved_topics'][0] if r['top_retrieved_topics'] else 'None'}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total cases:    {summary['total_cases']}")
    print(f"Hits:           {summary['hits']}")
    print(f"Misses:         {summary['misses']}")
    print(f"Precision@{summary['top_k']}:   {summary['precision_at_k']}")
    print(f"Verdict:        {summary['verdict']}")

    # Save results to outputs
    output = {'summary': summary, 'results': results}
    with open('outputs/retrieval_eval_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results saved to outputs/retrieval_eval_results.json")