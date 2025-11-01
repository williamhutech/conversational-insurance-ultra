"""
Loader for original policy text into Supabase.
Processes product_dict.pkl, chunks text, generates embeddings, and stores in original_text table.
"""

import asyncio
import pickle
from pathlib import Path
from typing import List, Dict, Any
from supabase import create_client, Client

from .config import TaxonomyLoaderConfig, load_config
from .original_text_models import (
    OriginalTextRecord,
    OriginalTextStats,
    ProductDocument
)
from .text_chunker import TextChunker
from .original_text_embedding_service import OriginalTextEmbeddingService


class OriginalTextLoader:
    """
    ETL pipeline for loading raw policy text with embeddings.
    Processes JSON files from raw_text directory.
    """

    def __init__(self, config: TaxonomyLoaderConfig):
        self.config = config

        # Validate service key format
        if not self._is_service_role_key(config.supabase_service_key):
            print("⚠️  WARNING: SUPABASE_SERVICE_KEY may not be a service role key!")
            print("   Service role keys typically start with 'eyJ' and are longer than anon keys.")
            print("   Make sure you're using the SERVICE ROLE key, not the ANON key.")
            print("   RLS policies require service role for INSERT operations.\n")

        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_service_key
        )
        self.embedding_service = OriginalTextEmbeddingService(config)
        self.chunker = TextChunker(
            chunk_size=1000,
            chunk_overlap=200,
            min_chunk_size=100
        )
        self.stats = OriginalTextStats()
        self._rls_error_shown = False  # Track if RLS error guidance was shown

    def _is_service_role_key(self, key: str) -> bool:
        """
        Basic validation that key looks like a service role key.
        Service role keys are typically JWT tokens starting with 'eyJ'.
        """
        return key.startswith("eyJ") and len(key) > 200

    async def load_all_documents(self, pickle_file_path: str) -> Dict[str, int]:
        """
        Load all policy documents from product_dict.pkl.

        Args:
            pickle_file_path: Path to product_dict.pkl file

        Returns:
            Statistics dictionary
        """
        print("=" * 80)
        print("🚀 ORIGINAL POLICY TEXT LOADER")
        print("=" * 80)

        # Load pickle file
        print(f"\n📁 Step 1: Loading pickle file: {pickle_file_path}")
        documents = self._discover_documents(pickle_file_path)
        print(f"✓ Found {len(documents)} policy documents")

        try:
            # Process each document
            for idx, doc in enumerate(documents, 1):
                print(f"\n📄 Step 2.{idx}: Processing {doc.product_name}")
                await self._process_document(doc)
                self.stats.products_processed += 1

            print("\n" + "=" * 80)
            print("✅ LOADING COMPLETE!")
            print("=" * 80)
            print(f"📊 Final Statistics:")
            print(f"  - Products Processed: {self.stats.products_processed}")
            print(f"  - Total Chunks: {self.stats.total_chunks}")
            print(f"  - Chunks Inserted: {self.stats.chunks_inserted}")
            print(f"  - Embeddings Generated: {self.stats.embeddings_generated}")
            print(f"  - Total Characters: {self.stats.total_characters:,}")
            print(f"  - Errors: {self.stats.errors}")
            print("=" * 80)

            return self.stats.to_dict()

        finally:
            await self.embedding_service.close()

    def _discover_documents(self, pickle_file_path: str) -> List[ProductDocument]:
        """
        Load documents from product_dict.pkl.

        Args:
            pickle_file_path: Path to pickle file

        Returns:
            List of ProductDocument objects
        """
        pickle_path = Path(pickle_file_path)
        if not pickle_path.exists():
            raise FileNotFoundError(f"Pickle file not found: {pickle_file_path}")

        try:
            with open(pickle_path, "rb") as f:
                product_dict = pickle.load(f)

            if not isinstance(product_dict, dict):
                raise ValueError(f"Expected dict, got {type(product_dict)}")

            documents = []
            for product_name, raw_content in product_dict.items():
                # Validate raw_content is a list
                if not isinstance(raw_content, list):
                    print(f"⚠️  Skipping {product_name}: expected list, got {type(raw_content)}")
                    self.stats.errors += 1
                    continue

                # Filter out empty strings
                raw_content = [text for text in raw_content if text and text.strip()]

                if not raw_content:
                    print(f"⚠️  Skipping {product_name}: no valid text content")
                    self.stats.errors += 1
                    continue

                doc = ProductDocument(
                    product_name=product_name,
                    raw_content=raw_content
                )
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"❌ Failed to load pickle file: {e}")
            raise

    async def _process_document(self, document: ProductDocument):
        """
        Process a single document: chunk, embed, and store.

        Args:
            document: ProductDocument to process
        """
        print(f"  📏 Document length: {document.total_length:,} characters")

        # Step 1: Chunk the document
        chunks = self.chunker.chunk_text(
            document.full_text,
            metadata={
                "product_name": document.product_name,
                "source": "product_dict.pkl"
            }
        )
        print(f"  ✂️  Generated {len(chunks)} chunks")
        self.stats.total_chunks += len(chunks)
        self.stats.total_characters += document.total_length

        if not chunks:
            print(f"  ⚠️  No chunks generated for {document.product_name}")
            return

        # Step 2: Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embedding_service.generate_embeddings_batch(
            texts,
            verbose=self.config.verbose
        )
        successful_embeddings = sum(1 for emb in embeddings if emb is not None)
        self.stats.embeddings_generated += successful_embeddings

        # Step 3: Insert into database
        print(f"  💾 Inserting into Supabase...")
        inserted_count = await self._insert_chunks(document.product_name, chunks, embeddings)
        self.stats.chunks_inserted += inserted_count
        print(f"  ✓ Inserted {inserted_count} chunks")

    async def _insert_chunks(
        self,
        product_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> int:
        """
        Insert chunks with embeddings into Supabase.

        Args:
            product_name: Product name
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors

        Returns:
            Number of successfully inserted chunks
        """
        inserted_count = 0

        for chunk, embedding in zip(chunks, embeddings):
            try:
                record = OriginalTextRecord(
                    product_name=product_name,
                    text=chunk["text"],
                    chunk_index=chunk["chunk_index"],
                    char_count=chunk["char_count"],
                    original_embedding=embedding,
                    metadata=chunk.get("metadata", {})
                )

                # Convert to dict for Supabase
                # Note: text_id and created_at are auto-generated by Postgres DEFAULT
                data = {
                    "product_name": record.product_name,
                    "text": record.text,
                    "chunk_index": record.chunk_index,
                    "char_count": record.char_count,
                    "original_embedding": record.original_embedding,
                    "metadata": record.metadata
                }

                # Insert into Supabase
                result = self.supabase.table("original_text").insert(data).execute()

                if result.data:
                    inserted_count += 1

            except Exception as e:
                error_msg = str(e)
                print(f"  ❌ Failed to insert chunk {chunk['chunk_index']}: {error_msg}")

                # Provide specific guidance for RLS errors (only show once)
                if not self._rls_error_shown and ("row-level security policy" in error_msg.lower() or "42501" in error_msg):
                    self._rls_error_shown = True
                    print("\n" + "=" * 80)
                    print("🔒 ROW-LEVEL SECURITY (RLS) ERROR DETECTED")
                    print("=" * 80)
                    print("This error means you don't have permission to INSERT into the table.")
                    print("\nPossible causes:")
                    print("  1. Wrong API key - Check your .env file:")
                    print("     • SUPABASE_SERVICE_KEY should be the SERVICE ROLE key (not anon key)")
                    print("     • Service keys start with 'eyJ' and are 200+ characters long")
                    print("     • Find it in: Supabase Dashboard → Settings → API → service_role key")
                    print("\n  2. RLS policies not created - Run this SQL in Supabase SQL Editor:")
                    print("     • File: database/supabase/taxonomy/schema_original_text.sql")
                    print("     • Especially lines 175-197 (RLS policies section)")
                    print("\n  3. Table doesn't exist - Create it first:")
                    print("     • Run the full schema_original_text.sql file")
                    print("=" * 80 + "\n")

                self.stats.errors += 1

        return inserted_count


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main entry point for CLI execution"""
    try:
        # Load configuration
        config = load_config()

        # Set pickle file path
        pickle_file_path = "database/supabase/taxonomy/raw_text/product_dict.pkl"

        # Create loader
        loader = OriginalTextLoader(config)

        # Run ETL pipeline
        await loader.load_all_documents(pickle_file_path)

        print(f"\n✨ Success! Data loaded into Supabase at {config.supabase_url}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
