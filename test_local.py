#!/usr/bin/env python3
"""
Local testing script for Kāraka RAG system
Tests the core functionality with local Neo4j
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, 'src')

from neo4j import GraphDatabase

def test_neo4j_connection():
    """Test Neo4j connection"""
    print("Testing Neo4j Connection")
    print("=" * 50)
    
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'karaka123')
    
    print(f"URI: {uri}")
    print(f"Username: {username}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' as message")
            record = result.single()
            print(f"✓ {record['message']}")
            
            # Get Neo4j version
            result = session.run("CALL dbms.components() YIELD name, versions")
            for record in result:
                print(f"✓ {record['name']}: {record['versions'][0]}")
        
        driver.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_graph_operations():
    """Test basic graph operations"""
    print("\nTesting Graph Operations")
    print("=" * 50)
    
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'karaka123')
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Create test nodes
            print("Creating test entities...")
            session.run("""
                MERGE (e1:Entity {name: 'Test Entity 1', type: 'PERSON'})
                MERGE (e2:Entity {name: 'Test Entity 2', type: 'ORGANIZATION'})
                MERGE (e1)-[:KARTA {confidence: 0.9}]->(e2)
            """)
            print("✓ Created test entities and relationship")
            
            # Query nodes
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            count = result.single()['count']
            print(f"✓ Total entities in graph: {count}")
            
            # Query relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            count = result.single()['count']
            print(f"✓ Total relationships in graph: {count}")
            
            # Get sample data
            result = session.run("""
                MATCH (e1:Entity)-[r]->(e2:Entity)
                RETURN e1.name as source, type(r) as relation, e2.name as target
                LIMIT 5
            """)
            
            print("\nSample relationships:")
            for record in result:
                print(f"  {record['source']} --[{record['relation']}]--> {record['target']}")
        
        driver.close()
        return True
    except Exception as e:
        print(f"✗ Graph operations failed: {e}")
        return False

def test_ingestion_logic():
    """Test document ingestion logic"""
    print("\nTesting Ingestion Logic")
    print("=" * 50)
    
    try:
        from karaka_extractor import KarakaExtractor
        
        extractor = KarakaExtractor()
        
        # Test document
        test_doc = "John works at Microsoft. He leads the AI team."
        
        print(f"Test document: {test_doc}")
        print("\nExtracting entities and relationships...")
        
        entities, relationships = extractor.extract(test_doc)
        
        print(f"\n✓ Extracted {len(entities)} entities:")
        for entity in entities[:5]:
            print(f"  - {entity.get('text', 'N/A')} ({entity.get('type', 'N/A')})")
        
        print(f"\n✓ Extracted {len(relationships)} relationships:")
        for rel in relationships[:5]:
            print(f"  - {rel.get('source', 'N/A')} --[{rel.get('type', 'N/A')}]--> {rel.get('target', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ Ingestion logic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_logic():
    """Test query logic"""
    print("\nTesting Query Logic")
    print("=" * 50)
    
    try:
        from karaka_query import KarakaQuery
        
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'karaka123')
        
        query_engine = KarakaQuery(uri, username, password)
        
        # Test query
        test_query = "What entities are in the graph?"
        
        print(f"Test query: {test_query}")
        print("\nExecuting query...")
        
        result = query_engine.query(test_query)
        
        print(f"\n✓ Query result:")
        print(json.dumps(result, indent=2))
        
        return True
    except Exception as e:
        print(f"✗ Query logic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("Kāraka RAG System - Local Testing")
    print("=" * 50 + "\n")
    
    results = []
    
    # Test Neo4j connection
    results.append(("Neo4j Connection", test_neo4j_connection()))
    
    # Test graph operations
    results.append(("Graph Operations", test_graph_operations()))
    
    # Test ingestion logic
    results.append(("Ingestion Logic", test_ingestion_logic()))
    
    # Test query logic
    results.append(("Query Logic", test_query_logic()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
