import os
import sys
import json
import pypdf

# Ensure python path includes GeoGuardianAI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.document_service.cleaner import TextCleaner
from ai.document_service.chunker import DocumentChunker
from ai.embedding_service.bge import BGEEmbeddingModel

KB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "rag_knowledge_base"))
DB_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "database", "qdrant_db.json")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "qdrant_db.json"))
]

TITLE_MAP = {
    "NDMA_Guidelines_Management_of_Urban_Flooding_2010.pdf": "urban_flooding_guidelines.pdf",
    "NDMA_Guidelines_Management_of_Floods_2008.pdf": "flood_management_guidelines.pdf",
    "Pune_DDMP_2025-26_Official.pdf": "pune_district_disaster_management_plan.pdf",
    "State_Disaster_Management_Plan_2023_Maharashtra_SDMA.pdf": "state_disaster_management_plan_2023.pdf",
    "Preparedness_and_Capacity_Building_DDMA_SOP.en.txt": "district_preparedness_sop.pdf",
    "Preparedness_and_Capacity_Building_DDMA_SOP.pdf": "district_preparedness_sop.pdf",
    "Disaster_Management_Rule_2005_Maharashtra.txt": "disaster_management_rule_2005.pdf",
    "Disaster_Management_Rule_2005_Maharashtra.pdf": "disaster_management_rule_2005.pdf",
}

def sync_vectordb():
    primary_db = DB_PATHS[0]
    if not os.path.exists(primary_db):
        print(f"Database not found at {primary_db}")
        return

    with open(primary_db, "r", encoding="utf-8") as f:
        docs = json.load(f)

    print(f"Loaded {len(docs)} existing chunks from {primary_db}")

    # Step 1: Standardize existing chunk titles and remove any mock files
    valid_titles = set(TITLE_MAP.values())
    valid_titles.add("urban_flooding_sop.pdf")

    cleaned_docs = []
    renamed_count = 0
    mock_removed_count = 0

    for doc in docs:
        old_title = doc.get("metadata", {}).get("title", "")
        # Remove any mock test files uploaded during earlier testing
        if "mock" in old_title.lower() or "sop_flood_response_2026" in old_title.lower() or "flood_sop.txt" in old_title.lower():
            mock_removed_count += 1
            continue

        if old_title in TITLE_MAP:
            doc["metadata"]["title"] = TITLE_MAP[old_title]
            doc["metadata"]["source_file"] = TITLE_MAP[old_title]
            doc["metadata"]["dataset"] = "rag_knowledge_base"
            renamed_count += 1
        cleaned_docs.append(doc)

    print(f"Standardized {renamed_count} document titles. Filtered {mock_removed_count} mock entries.")

    # Step 2: Index urban_flooding_sop.pdf if not already present
    already_has_sop = any(d.get("metadata", {}).get("title") == "urban_flooding_sop.pdf" for d in cleaned_docs)

    if not already_has_sop:
        sop_path = os.path.join(KB_DIR, "Flood", "urban_flooding_sop.pdf")
        if os.path.exists(sop_path):
            print(f"Ingesting {sop_path}...")
            embedder = BGEEmbeddingModel()
            reader = pypdf.PdfReader(sop_path)
            new_chunks_count = 0

            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                cleaned = TextCleaner.clean(page_text)
                if not cleaned:
                    continue

                chunks = DocumentChunker.chunk(cleaned, chunk_size=800, overlap=100)
                for c_idx, c in enumerate(chunks):
                    chunk_text = c["text"]
                    chunk_id = f"urban_flooding_sop.pdf_p{page_idx + 1}_c{c_idx}"
                    vector = embedder.get_embedding(chunk_text)

                    cleaned_docs.append({
                        "id": chunk_id,
                        "vector": vector,
                        "text": chunk_text,
                        "metadata": {
                            "title": "urban_flooding_sop.pdf",
                            "source_file": "urban_flooding_sop.pdf",
                            "category": "Flood",
                            "disaster_type": "Flood",
                            "authority": "Ministry of Housing and Urban Affairs (MoHUA)",
                            "jurisdiction": "National",
                            "pages": page_idx + 1,
                            "dataset": "rag_knowledge_base"
                        }
                    })
                    new_chunks_count += 1

            print(f"Successfully added {new_chunks_count} chunks from urban_flooding_sop.pdf")
    else:
        print("urban_flooding_sop.pdf is already indexed.")

    # Step 3: Save to both DB locations
    for db_path in DB_PATHS:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_docs, f, indent=2)
        print(f"Saved {len(cleaned_docs)} verified real chunks to {db_path}")

    # Summary
    titles = set(d["metadata"].get("title") for d in cleaned_docs)
    print("\n==========================================")
    print("VERIFIED RAG KNOWLEDGE BASE INGESTION COMPLETE")
    print("Total Chunks:", len(cleaned_docs))
    print("Active Documents in Vector Store:")
    for t in sorted(titles):
        count = sum(1 for d in cleaned_docs if d["metadata"].get("title") == t)
        print(f"  - {t}: {count} chunks")
    print("==========================================")

if __name__ == "__main__":
    sync_vectordb()
