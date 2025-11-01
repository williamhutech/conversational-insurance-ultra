"""
Neo4j Service
Handles schema creation, bulk import, indexes, and verification for knowledge graph.
"""

import time
import ijson
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from decimal import Decimal
from neo4j import GraphDatabase



from ..utils.neo4j_utils import test_connection, get_database_stats, print_database_stats


class Neo4jService:
    """
    Service for managing Neo4j knowledge graph operations.

    Handles:
    - Database connection and testing
    - Schema and constraint creation
    - Bulk node/edge import
    - Index creation (including vector indexes)
    - Database verification and statistics
    """

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j service.

        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
            database: Database name
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[GraphDatabase.driver] = None

    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.

        Returns:
            True if connection successful
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            print(f"✅ Connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            self.driver = None

    def test_connection(self) -> bool:
        """Test database connection."""
        return test_connection(
            self.uri,
            self.username,
            self.password,
            self.database
        )

    def create_schema(self) -> bool:
        """
        Create schema and constraints.

        Creates:
        - Database (if not exists)
        - Unique constraints on Memory node ID
        """
        print("Creating schema and constraints...")

        try:
            if not self.driver:
                self.connect()

            # Create database if needed
            try:
                with self.driver.session(database="system") as session:
                    session.run(f"CREATE DATABASE {self.database} IF NOT EXISTS")
                    print(f"✅ Database '{self.database}' ready")
            except Exception as e:
                print(f"⚠️  Could not create database: {e}")

            # Create constraints - MODIFIED: Use Memory label
            with self.driver.session(database=self.database) as session:
                session.run("""
                    CREATE CONSTRAINT memory_id_unique IF NOT EXISTS
                    FOR (n:Memory) REQUIRE n.id IS UNIQUE
                """)
                print("✅ Created unique constraint on Memory.id")

            return True

        except Exception as e:
            print(f"❌ Schema creation failed: {e}")
            return False

    def bulk_import_nodes(
        self,
        json_file_path: Path,
        batch_size: int = 1000
    ) -> int:
        """
        Bulk import nodes from JSON file.

        Args:
            json_file_path: Path to knowledge graph JSON file
            batch_size: Batch size for import

        Returns:
            Number of nodes imported
        """
        print("\n" + "=" * 60)
        print("BULK IMPORTING NODES")
        print("=" * 60)

        if not self.driver:
            self.connect()

        start_time = time.time()
        success_count = 0
        batch = []

        try:
            with open(json_file_path, 'rb') as f:
                # Use ijson for memory-efficient streaming
                nodes = ijson.items(f, 'nodes.item')

                for node in nodes:
                    # Clean and prepare node data
                    node_data = self._prepare_node(node)
                    batch.append(node_data)

                    # Execute batch
                    if len(batch) >= batch_size:
                        batch_success = self._execute_node_batch(batch)
                        success_count += batch_success
                        batch = []

                        # Progress update
                        elapsed = time.time() - start_time
                        rate = success_count / elapsed if elapsed > 0 else 0
                        print(f"  Imported: {success_count:,} nodes | "
                              f"Rate: {rate:.1f} nodes/sec")

                # Process remaining batch
                if batch:
                    batch_success = self._execute_node_batch(batch)
                    success_count += batch_success

            total_time = time.time() - start_time
            print(f"\n✅ Node import complete:")
            print(f"  Nodes imported: {success_count:,}")
            print(f"  Total time: {total_time/60:.1f} minutes")
            print(f"  Average rate: {success_count/total_time:.1f} nodes/sec")

            return success_count

        except Exception as e:
            print(f"❌ Node import failed: {e}")
            return success_count

    def bulk_import_edges(
        self,
        json_file_path: Path,
        batch_size: int = 1000
    ) -> int:
        """
        Bulk import edges from JSON file.

        Args:
            json_file_path: Path to knowledge graph JSON file
            batch_size: Batch size for import

        Returns:
            Number of edges imported
        """
        print("\n" + "=" * 60)
        print("BULK IMPORTING EDGES")
        print("=" * 60)

        if not self.driver:
            self.connect()

        start_time = time.time()
        success_count = 0
        batch = []

        try:
            with open(json_file_path, 'rb') as f:
                edges = ijson.items(f, 'edges.item')

                for edge in edges:
                    # Clean edge data
                    edge_data = self._clean_data_types(edge)
                    batch.append({
                        'source': edge_data.get('source'),
                        'target': edge_data.get('target'),
                        'type': edge_data.get('type', 'RELATED_TO'),
                        'created_at': edge_data.get('created_at', datetime.now().isoformat())
                    })

                    # Execute batch
                    if len(batch) >= batch_size:
                        batch_success = self._execute_edge_batch(batch)
                        success_count += batch_success
                        batch = []

                        # Progress update
                        if success_count % (batch_size / 100) == 0:
                            elapsed = time.time() - start_time
                            rate = success_count / elapsed if elapsed > 0 else 0
                            print(f"  Imported: {success_count:,} edges | "
                                  f"Rate: {rate:.1f} edges/sec")

                # Process remaining batch
                if batch:
                    batch_success = self._execute_edge_batch(batch)
                    success_count += batch_success

            total_time = time.time() - start_time
            print(f"\n✅ Edge import complete:")
            print(f"  Edges imported: {success_count:,}")
            print(f"  Total time: {total_time/60:.1f} minutes")
            print(f"  Average rate: {success_count/total_time:.1f} edges/sec")

            return success_count

        except Exception as e:
            print(f"❌ Edge import failed: {e}")
            return success_count

    def create_indexes(self) -> bool:
        """
        Create indexes for query performance (MemOS-compatible).

        Creates:
        - Property indexes on memory_type, status, created_at, updated_at
        - Full-text search index on memory content
        - Vector index for semantic search on embeddings
        """
        print("\n" + "=" * 60)
        print("CREATING INDEXES")
        print("=" * 60)

        try:
            if not self.driver:
                self.connect()

            with self.driver.session(database=self.database) as session:
                # MODIFIED: Property indexes for MemOS fields on Memory label
                indexes = [
                    "CREATE INDEX memory_type_idx IF NOT EXISTS FOR (n:Memory) ON (n.memory_type)",
                    "CREATE INDEX memory_status_idx IF NOT EXISTS FOR (n:Memory) ON (n.status)",
                    "CREATE INDEX memory_created_at_idx IF NOT EXISTS FOR (n:Memory) ON (n.created_at)",
                    "CREATE INDEX memory_updated_at_idx IF NOT EXISTS FOR (n:Memory) ON (n.updated_at)",
                ]

                for index_query in indexes:
                    session.run(index_query)
                    print(f"✅ Property index created")

                # MODIFIED: Full-text search index on Memory.memory
                try:
                    session.run("""
                        CREATE FULLTEXT INDEX memory_fulltext IF NOT EXISTS
                        FOR (n:Memory) ON EACH [n.memory]
                    """)
                    print("✅ Full-text index created for Memory.memory")
                except Exception as e:
                    print(f"⚠️  Full-text index creation failed: {e}")

                # MODIFIED: Vector index on Memory.embedding
                try:
                    session.run("""
                        CREATE VECTOR INDEX memory_vector_index IF NOT EXISTS
                        FOR (n:Memory) ON (n.embedding)
                        OPTIONS {indexConfig: {
                            `vector.dimensions`: 768,
                            `vector.similarity_function`: 'cosine'
                        }}
                    """)
                    print("✅ Vector index created (768 dimensions, cosine similarity)")
                except Exception as e:
                    print(f"⚠️  Vector index creation failed: {e}")
                    print("   Vector search functionality will be unavailable")

            print("✅ Index creation complete")
            return True

        except Exception as e:
            print(f"❌ Index creation failed: {e}")
            return False

    def verify_import(self) -> Dict[str, Any]:
        """
        Verify import and print statistics.

        Returns:
            Dictionary with verification results
        """
        print("\n" + "=" * 60)
        print("VERIFYING IMPORT")
        print("=" * 60)

        if not self.driver:
            self.connect()

        stats = get_database_stats(self.driver, self.database)
        print_database_stats(self.driver, self.database)

        # Verify constraints
        with self.driver.session(database=self.database) as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = [record.data() for record in result]
            print(f"\nConstraints: {len(constraints)}")

            result = session.run("SHOW INDEXES")
            indexes = [record.data() for record in result]
            print(f"Indexes: {len(indexes)}")

        return {
            "stats": stats,
            "constraints": len(constraints),
            "indexes": len(indexes)
        }

    def _clean_data_types(self, obj: Any) -> Any:
        """Clean data types for Neo4j compatibility."""
        if isinstance(obj, dict):
            return {k: self._clean_data_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_data_types(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif obj is None:
            return None
        else:
            return obj

    def _prepare_node(self, node: Dict) -> Dict:
        """Prepare node data for import (MemOS-compatible structure from Stage 8)."""
        node = self._clean_data_types(node)
        metadata = node.get('metadata', {}).copy()
        
        # MODIFIED: Ensure created_at and updated_at exist
        if 'created_at' not in metadata:
            metadata['created_at'] = datetime.now().isoformat()
        if 'updated_at' not in metadata:
            metadata['updated_at'] = datetime.now().isoformat()

        return {
            'id': node.get('id'),
            'memory': node.get('memory', ''),
            'sources': node.get('sources', []),  # ADDED: Required by MemOS
            'metadata': self._clean_data_types(metadata)
        }

    def _execute_node_batch(self, batch: List[Dict]) -> int:
        """Execute node batch import (MemOS-compatible properties)."""
        cypher = """
        UNWIND $batch AS row
        MERGE (n:Memory {id: row.id})
        SET n.key = row.id,
            n.memory = row.memory,
            n.sources = row.sources,
            n.created_at = datetime(row.metadata.created_at),
            n.updated_at = datetime(row.metadata.updated_at),
            n += row.metadata
        RETURN count(n) AS imported
        """
        try:
            with self.driver.session(database=self.database) as session:
                res = session.run(cypher, batch=batch)
                return res.single()["imported"]
        except Exception as e:
            print(f"  Batch error: {e}")
            return 0

    def _execute_edge_batch(self, batch: List[Dict]) -> int:
        """Execute edge batch import with dynamic relationship types (RELATE_TO or PARENT)."""
        # Use APOC for dynamic relationship type creation
        cypher = """
        UNWIND $batch AS row
        MATCH (s:Memory {id: row.source})
        MATCH (t:Memory {id: row.target})
        MERGE (s)-[r:PARENT]->(t)
        SET r.created_at = datetime(row.created_at)
        RETURN count(r) AS imported
        """
        try:
            with self.driver.session(database=self.database) as session:
                res = session.run(cypher, batch=batch)
                return res.single()["imported"]
        except Exception as e:
            # If APOC is not available, fall back to separate batches by type
            print(f"  Edge batch error (possibly APOC not installed): {e}")
            print(f"  Falling back to type-specific batches...")
            return self._execute_edge_batch_fallback(batch)

    def _execute_edge_batch_fallback(self, batch: List[Dict]) -> int:
        """Fallback edge import without APOC - separate batches by relationship type."""
        # Group by relationship type
        relate_to_batch = [e for e in batch if e.get('type') == 'RELATE_TO']
        parent_batch = [e for e in batch if e.get('type') == 'PARENT']

        total_imported = 0

        # Import RELATE_TO relationships
        if relate_to_batch:
            cypher_relate = """
            UNWIND $batch AS row
            MATCH (s:Node {id: row.source})
            MATCH (t:Node {id: row.target})
            MERGE (s)-[r:RELATE_TO]->(t)
            SET r.created_at = datetime(row.created_at)
            RETURN count(r) AS imported
            """
            try:
                with self.driver.session(database=self.database) as session:
                    res = session.run(cypher_relate, batch=relate_to_batch)
                    total_imported += res.single()["imported"]
            except Exception as e:
                print(f"  RELATE_TO batch error: {e}")

        # Import PARENT relationships
        if parent_batch:
            cypher_parent = """
            UNWIND $batch AS row
            MATCH (s:Node {id: row.source})
            MATCH (t:Node {id: row.target})
            MERGE (s)-[r:PARENT]->(t)
            SET r.created_at = datetime(row.created_at)
            RETURN count(r) AS imported
            """
            try:
                with self.driver.session(database=self.database) as session:
                    res = session.run(cypher_parent, batch=parent_batch)
                    total_imported += res.single()["imported"]
            except Exception as e:
                print(f"  PARENT batch error: {e}")

        return total_imported

    def full_import_pipeline(
        self,
        json_file_path: Path,
        node_batch_size: int = 1000,
        edge_batch_size: int = 10000
    ) -> Dict[str, Any]:
        """
        Complete import pipeline: schema → nodes → edges → indexes → verify.

        Args:
            json_file_path: Path to knowledge graph JSON
            node_batch_size: Batch size for node import
            edge_batch_size: Batch size for edge import

        Returns:
            Dictionary with pipeline results
        """
        print("\n" + "=" * 60)
        print("NEO4J FULL IMPORT PIPELINE")
        print("=" * 60)

        start_time = time.time()

        # Step 1: Test connection
        print("\n[Step 1] Testing connection...")
        if not self.test_connection():
            return {"success": False, "error": "Connection test failed"}

        # Step 2: Create schema
        print("\n[Step 2] Creating schema...")
        if not self.create_schema():
            return {"success": False, "error": "Schema creation failed"}

        # Step 3: Import nodes
        print("\n[Step 3] Importing nodes...")
        nodes_start = time.time()
        nodes_imported = self.bulk_import_nodes(json_file_path, node_batch_size)
        nodes_elapsed = time.time() - nodes_start
        if nodes_elapsed > 0:
            print(f"  Avg speed (nodes): {nodes_imported / nodes_elapsed:.1f} nodes/sec")
        else:
            print("  Avg speed (nodes): n/a (elapsed time ~0)")

        # Step 4: Import edges
        print("\n[Step 4] Importing edges...")
        edges_start = time.time()
        edges_imported = self.bulk_import_edges(json_file_path, edge_batch_size)
        edges_elapsed = time.time() - edges_start
        if edges_elapsed > 0:
            print(f"  Avg speed (edges): {edges_imported / edges_elapsed:.1f} edges/sec")
        else:
            print("  Avg speed (edges): n/a (elapsed time ~0)")

        # Step 5: Create indexes
        print("\n[Step 5] Creating indexes...")
        if not self.create_indexes():
            print("⚠️  Index creation had errors")

        # Step 6: Verify
        print("\n[Step 6] Verifying import...")
        verification = self.verify_import()

        total_time = time.time() - start_time

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Nodes imported: {nodes_imported:,}")
        if 'nodes_elapsed' in locals() and nodes_elapsed > 0:
            print(f"Avg speed (nodes): {nodes_imported / nodes_elapsed:.1f} nodes/sec")
        print(f"Edges imported: {edges_imported:,}")
        if 'edges_elapsed' in locals() and edges_elapsed > 0:
            print(f"Avg speed (edges): {edges_imported / edges_elapsed:.1f} edges/sec")
        print("=" * 60)

        return {
            "success": True,
            "total_time_minutes": total_time / 60,
            "nodes_imported": nodes_imported,
            "edges_imported": edges_imported,
            "verification": verification
        }
