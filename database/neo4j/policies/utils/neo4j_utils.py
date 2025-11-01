"""
Neo4j Utilities
Helper functions for Neo4j database operations.
"""

from typing import Dict, List, Any
from neo4j import GraphDatabase


def test_connection(uri: str, username: str, password: str, database: str) -> bool:
    """
    Test Neo4j database connection.

    Args:
        uri: Neo4j connection URI
        username: Database username
        password: Database password
        database: Database name

    Returns:
        True if connection successful, False otherwise
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session(database=database) as session:
            result = session.run("RETURN 'Connection OK' AS message")
            message = result.single()['message']
            print(f"✅ Neo4j connection successful: {message}")
        driver.close()
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False


def execute_query(
    driver: GraphDatabase.driver,
    query: str,
    parameters: Dict[str, Any] = None,
    database: str = None
) -> List[Dict]:
    """
    Execute a Cypher query and return results.

    Args:
        driver: Neo4j driver instance
        query: Cypher query string
        parameters: Query parameters
        database: Database name (optional)

    Returns:
        List of result dictionaries
    """
    with driver.session(database=database) as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


def execute_write_query(
    driver: GraphDatabase.driver,
    query: str,
    parameters: Dict[str, Any] = None,
    database: str = None
) -> Dict:
    """
    Execute a write query in a transaction.

    Args:
        driver: Neo4j driver instance
        query: Cypher query string
        parameters: Query parameters
        database: Database name (optional)

    Returns:
        Query statistics dictionary
    """
    with driver.session(database=database) as session:
        result = session.run(query, parameters or {})
        summary = result.consume()
        return {
            "nodes_created": summary.counters.nodes_created,
            "relationships_created": summary.counters.relationships_created,
            "properties_set": summary.counters.properties_set,
            "labels_added": summary.counters.labels_added,
            "indexes_added": summary.counters.indexes_added,
            "constraints_added": summary.counters.constraints_added
        }


def clear_database(driver: GraphDatabase.driver, database: str = None):
    """
    Clear all nodes and relationships from the database.

    WARNING: This operation is irreversible!

    Args:
        driver: Neo4j driver instance
        database: Database name (optional)
    """
    print("⚠️  Clearing database...")

    with driver.session(database=database) as session:
        # Delete all relationships first
        session.run("MATCH ()-[r]->() DELETE r")
        # Then delete all nodes
        session.run("MATCH (n) DELETE n")

    print("✅ Database cleared")


def get_node_count(
    driver: GraphDatabase.driver,
    label: str = None,
    database: str = None
) -> int:
    """
    Get count of nodes, optionally filtered by label.

    Args:
        driver: Neo4j driver instance
        label: Node label to filter by (optional)
        database: Database name (optional)

    Returns:
        Number of nodes
    """
    with driver.session(database=database) as session:
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) AS count"
        else:
            query = "MATCH (n) RETURN count(n) AS count"

        result = session.run(query)
        return result.single()['count']


def get_relationship_count(
    driver: GraphDatabase.driver,
    rel_type: str = None,
    database: str = None
) -> int:
    """
    Get count of relationships, optionally filtered by type.

    Args:
        driver: Neo4j driver instance
        rel_type: Relationship type to filter by (optional)
        database: Database name (optional)

    Returns:
        Number of relationships
    """
    with driver.session(database=database) as session:
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) AS count"

        result = session.run(query)
        return result.single()['count']


def get_database_stats(driver: GraphDatabase.driver, database: str = None) -> Dict:
    """
    Get comprehensive database statistics.

    Args:
        driver: Neo4j driver instance
        database: Database name (optional)

    Returns:
        Dictionary with database statistics
    """
    stats = {
        "total_nodes": get_node_count(driver, database=database),
        "total_relationships": get_relationship_count(driver, database=database)
    }

    # Get node counts by label
    with driver.session(database=database) as session:
        result = session.run("CALL db.labels()")
        labels = [record['label'] for record in result]

    stats["node_counts_by_label"] = {}
    for label in labels:
        count = get_node_count(driver, label=label, database=database)
        stats["node_counts_by_label"][label] = count

    # Get relationship counts by type
    with driver.session(database=database) as session:
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [record['relationshipType'] for record in result]

    stats["relationship_counts_by_type"] = {}
    for rel_type in rel_types:
        count = get_relationship_count(driver, rel_type=rel_type, database=database)
        stats["relationship_counts_by_type"][rel_type] = count

    return stats


def print_database_stats(driver: GraphDatabase.driver, database: str = None):
    """
    Print formatted database statistics.

    Args:
        driver: Neo4j driver instance
        database: Database name (optional)
    """
    stats = get_database_stats(driver, database=database)

    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    print(f"Total Nodes: {stats['total_nodes']:,}")
    print(f"Total Relationships: {stats['total_relationships']:,}")

    print("\nNodes by Label:")
    for label, count in stats['node_counts_by_label'].items():
        print(f"  {label}: {count:,}")

    print("\nRelationships by Type:")
    for rel_type, count in stats['relationship_counts_by_type'].items():
        print(f"  {rel_type}: {count:,}")

    print("=" * 50 + "\n")


def batch_execute(
    driver: GraphDatabase.driver,
    query: str,
    data: List[Dict],
    batch_size: int = 1000,
    database: str = None
) -> int:
    """
    Execute a query in batches using UNWIND.

    Args:
        driver: Neo4j driver instance
        query: Cypher query with $batch parameter
        data: List of data dictionaries
        batch_size: Size of each batch
        database: Database name (optional)

    Returns:
        Total number of items processed
    """
    total = len(data)
    processed = 0

    with driver.session(database=database) as session:
        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            session.run(query, {"batch": batch})
            processed += len(batch)

            if processed % (batch_size * 10) == 0:
                print(f"  Processed {processed:,} / {total:,} items")

    return processed