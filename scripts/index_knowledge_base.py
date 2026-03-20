#!/usr/bin/env python3
"""Index the medical nutrition knowledge base into a FAISS vector store.

Usage:
    python scripts/index_knowledge_base.py [--force]

This script reads all .md files from data/knowledge_base/, chunks them,
embeds them with sentence-transformers, and stores the FAISS index to
data/faiss_index/ for fast retrieval during diet generation.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS index from medical nutrition knowledge base"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if cached index exists",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show index statistics and exit",
    )
    args = parser.parse_args()

    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from modules.rag import build_index, get_index_stats, KNOWLEDGE_BASE_DIR, FAISS_INDEX_DIR

    if args.stats:
        stats = get_index_stats()
        print("\n=== RAG Index Statistics ===")
        for key, value in stats.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")
        return

    print(f"\nKnowledge base: {KNOWLEDGE_BASE_DIR}")
    print(f"Index output:   {FAISS_INDEX_DIR}")

    # List knowledge base files
    md_files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not md_files:
        print("\n❌ No .md files found in knowledge base directory!")
        print(f"   Add markdown files to: {KNOWLEDGE_BASE_DIR}")
        sys.exit(1)

    print(f"\nFound {len(md_files)} knowledge base documents:")
    for f in md_files:
        size_kb = f.stat().st_size / 1024
        print(f"  📄 {f.name} ({size_kb:.1f} KB)")

    # Build index
    print("\n🔨 Building FAISS index...")
    pack = build_index(force_rebuild=args.force)

    index = pack.get("index")
    chunks = pack.get("chunks", [])

    if index is None:
        print("\n❌ Index build failed — no vectors created.")
        sys.exit(1)

    # Show results
    print(f"\n✅ Index built successfully!")
    print(f"   Chunks:  {len(chunks)}")
    print(f"   Vectors: {index.ntotal}")
    print(f"   Dim:     {index.d}")
    print(f"   Saved:   {FAISS_INDEX_DIR}")

    # Show full stats
    stats = get_index_stats()
    print(f"\n   Sources: {len(stats['source_files'])}")
    print(f"   Unique sections: {stats['unique_sections']}")
    print(f"   Embedding model: {stats['embedding_model']}")


if __name__ == "__main__":
    main()
