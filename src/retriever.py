import os
import sys
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.policy_loader import load_all_policies

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolicyRetriever:
    """TF-IDF based policy retriever."""

    def __init__(self, policies_dir='data/policies'):
        self.chunks = load_all_policies(policies_dir)
        self.texts = [c['text'] for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)
        logger.info(f"Retriever initialized with {len(self.chunks)} chunks")

    def retrieve(self, query, top_k=3):
        """
        Retrieve top-k most relevant policy chunks for a query.
        Returns list of dicts with chunk text, metadata, and score.
        """
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                result = self.chunks[idx].copy()
                result['score'] = round(float(scores[idx]), 4)
                results.append(result)

        logger.info(f"Query: '{query[:60]}' → {len(results)} results")
        return results

    def retrieve_for_denial(self, carc, rarc, carc_meaning, short_description='', top_k=3):
        """
        Build a query from denial fields and retrieve relevant policy chunks.
        """
        query_parts = [carc_meaning]
        if short_description:
            query_parts.append(short_description)
        if rarc:
            query_parts.append(f"remark code {rarc}")
        query = ' '.join(query_parts)
        return self.retrieve(query, top_k=top_k)


if __name__ == "__main__":
    import json

    retriever = PolicyRetriever()

    # Test with denial scenarios from our sample data
    test_cases = [
        {
            "claim_id": "CLM10001",
            "carc": "16",
            "rarc": "MA130",
            "carc_meaning": "Claim/service lacks information or has submission/billing error(s).",
            "short_description": "Missing information"
        },
        {
            "claim_id": "CLM10002",
            "carc": "50",
            "rarc": "N20",
            "carc_meaning": "These are non-covered services because this is not deemed a medical necessity by the payer.",
            "short_description": "Service not medically necessary"
        },
        {
            "claim_id": "CLM10004",
            "carc": "97",
            "rarc": "M15",
            "carc_meaning": "The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated.",
            "short_description": "Service bundled"
        },
        {
            "claim_id": "CLM10003",
            "carc": "1",
            "rarc": "N4",
            "carc_meaning": "Deductible Amount.",
            "short_description": "Deductible amount"
        },
        {
            "claim_id": "CLM10005",
            "carc": "4",
            "rarc": "N130",
            "carc_meaning": "The procedure code is inconsistent with the modifier used.",
            "short_description": "Service inconsistent with modifier"
        },
    ]

    print("\n" + "="*60)
    print("RETRIEVAL TEST RESULTS")
    print("="*60)

    for case in test_cases:
        print(f"\nClaim: {case['claim_id']} | CARC {case['carc']} — {case['short_description']}")
        print("-" * 50)
        results = retriever.retrieve_for_denial(
            carc=case['carc'],
            rarc=case['rarc'],
            carc_meaning=case['carc_meaning'],
            short_description=case['short_description']
        )
        for i, r in enumerate(results, 1):
            print(f"  [{i}] Score: {r['score']} | {r['source']} | {r['section']}")
            print(f"      Topic: {r['topic']}")
            print(f"      Text: {r['text'][:150]}...")
        print()