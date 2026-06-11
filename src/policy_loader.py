import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_policy_text(filepath):
    """Load plain text from a policy file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def chunk_policy_text(text, filepath, chunk_size=500):
    """
    Chunk policy text by section heading or paragraph.
    Returns list of dicts with text and metadata.
    """
    filename = os.path.basename(filepath)
    payer, topic, effective_date = extract_metadata(text)

    chunks = []
    current_section = "General"
    current_chunk = []
    current_length = 0

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Detect section headings
        if line.startswith('SECTION'):
            # Save current chunk before starting new section
            if current_chunk:
                chunk_text = ' '.join(current_chunk).strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'source': filename,
                        'section': current_section,
                        'payer': payer,
                        'topic': topic,
                        'effective_date': effective_date,
                    })
            current_section = line
            current_chunk = []
            current_length = 0
        else:
            current_chunk.append(line)
            current_length += len(line)

            # Split on size if chunk gets too large
            if current_length >= chunk_size:
                chunk_text = ' '.join(current_chunk).strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'source': filename,
                        'section': current_section,
                        'payer': payer,
                        'topic': topic,
                        'effective_date': effective_date,
                    })
                current_chunk = []
                current_length = 0

    # Don't forget the last chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk).strip()
        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'source': filename,
                'section': current_section,
                'payer': payer,
                'topic': topic,
                'effective_date': effective_date,
            })

    logger.info(f"Loaded {len(chunks)} chunks from {filename}")
    return chunks


def extract_metadata(text):
    """Extract payer, topic, and effective date from policy header."""
    payer = 'Unknown'
    topic = 'Unknown'
    effective_date = 'Unknown'

    for line in text.splitlines():
        line = line.strip()
        if line.startswith('Payer:'):
            payer = line.replace('Payer:', '').strip()
        elif line.startswith('Topic:'):
            topic = line.replace('Topic:', '').strip()
        elif line.startswith('Effective Date:'):
            effective_date = line.replace('Effective Date:', '').strip()

    return payer, topic, effective_date


def load_all_policies(policies_dir='data/policies'):
    """Load and chunk all policy files in the policies directory."""
    all_chunks = []
    for filename in os.listdir(policies_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(policies_dir, filename)
            text = load_policy_text(filepath)
            chunks = chunk_policy_text(text, filepath)
            all_chunks.extend(chunks)
    logger.info(f"Total chunks loaded: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    chunks = load_all_policies()
    print(f"\nTotal chunks: {len(chunks)}")
    print("\nSample chunk:")
    if chunks:
        c = chunks[0]
        print(f"  Source: {c['source']}")
        print(f"  Section: {c['section']}")
        print(f"  Payer: {c['payer']}")
        print(f"  Topic: {c['topic']}")
        print(f"  Effective Date: {c['effective_date']}")
        print(f"  Text: {c['text'][:200]}...")