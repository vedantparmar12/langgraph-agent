from typing import Dict, List, Any
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Neo4jMemory:
    def __init__(self):
        uri = os.getenv('NEO4J_URI')
        username = os.getenv('NEO4J_USERNAME')
        password = os.getenv('NEO4J_PASSWORD')

        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self._initialize_schema()

    def _initialize_schema(self):
        with self.driver.session() as session:
            # Ensure each conversation has a unique ID
            session.run("""
                CREATE CONSTRAINT conversation_id IF NOT EXISTS
                FOR (c:Conversation) REQUIRE c.id IS UNIQUE
            """)
            # Ensure each user has a unique ID
            session.run("""
                CREATE CONSTRAINT user_id IF NOT EXISTS
                FOR (u:User) REQUIRE u.id IS UNIQUE
            """)

    def store_conversation(self, user_id: str, message: str, response: str, metadata: Dict = None):
        with self.driver.session() as session:
            query = """
                MERGE (u:User {id: $user_id})
                CREATE (c:Conversation {
                    id: randomUUID(),
                    timestamp: datetime(),
                    message: $message,
                    response: $response,
                    metadata: $metadata
                })
                CREATE (u)-[:HAD_CONVERSATION]->(c)
                RETURN c.id as conversation_id
            """
            result = session.run(
                query,
                user_id=user_id,
                message=message,
                response=response,
                metadata=metadata or None
            )
            return result.single()['conversation_id']

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Retrieve recent conversation history for a specific user.
        Returns conversations sorted by most recent first.
        """
        with self.driver.session() as session:
            query = """
                MATCH (u:User {id: $user_id})-[:HAD_CONVERSATION]->(c:Conversation)
                RETURN c.message as message,
                       c.response as response,
                       c.timestamp as timestamp,
                       c.metadata as metadata
                ORDER BY c.timestamp DESC
                LIMIT $limit
            """
            results = session.run(query, user_id=user_id, limit=limit)
            return [dict(record) for record in results]

    def store_tool_usage(self, conversation_id: str, tool_name: str, input_data: str, output_data: str):
        """
        Record when a tool was used during a conversation.
        Links tool usage to the specific conversation for analytics.
        """
        with self.driver.session() as session:
            query = """
                MATCH (c:Conversation {id: $conversation_id})
                CREATE (t:ToolUsage {
                    tool_name: $tool_name,
                    input: $input_data,
                    output: $output_data,
                    timestamp: datetime()
                })
                CREATE (c)-[:USED_TOOL]->(t)
            """
            session.run(
                query,
                conversation_id=conversation_id,
                tool_name=tool_name,
                input_data=input_data,
                output_data=output_data
            )

    def get_user_preferences(self, user_id: str) -> Dict:
        """
        Retrieve user preferences from the database.
        Returns empty dict if user has no preferences set.
        """
        with self.driver.session() as session:
            query = """
                MATCH (u:User {id: $user_id})
                RETURN u.preferences as preferences
            """
            result = session.run(query, user_id=user_id).single()
            return result['preferences'] if result else {}

    def update_user_preferences(self, user_id: str, preferences: Dict):
        """
        Save or update user preferences in the database.
        Creates user if they don't exist yet.
        """
        with self.driver.session() as session:
            query = """
                MERGE (u:User {id: $user_id})
                SET u.preferences = $preferences
            """
            session.run(query, user_id=user_id, preferences=preferences)

    def get_conversation_stats(self, user_id: str) -> Dict:
        """
        Get statistics about a user's conversations.
        Returns count of conversations and most used tool.
        """
        with self.driver.session() as session:
            query = """
                MATCH (u:User {id: $user_id})-[:HAD_CONVERSATION]->(c:Conversation)
                OPTIONAL MATCH (c)-[:USED_TOOL]->(t:ToolUsage)
                RETURN count(c) as conversation_count,
                       collect(t.tool_name) as tools_used
            """
            result = session.run(query, user_id=user_id).single()

            if result:
                tools = result['tools_used']
                # Find most frequently used tool
                most_used_tool = max(set(tools), key=tools.count) if tools else None

                return {
                    'conversation_count': result['conversation_count'],
                    'most_used_tool': most_used_tool,
                    'total_tool_uses': len(tools)
                }
            return {'conversation_count': 0, 'most_used_tool': None, 'total_tool_uses': 0}

    def delete_user_data(self, user_id: str):
        """
        Remove all data for a specific user.
        Useful for privacy compliance or testing cleanup.
        """
        with self.driver.session() as session:
            query = """
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[:HAD_CONVERSATION]->(c:Conversation)
                OPTIONAL MATCH (c)-[:USED_TOOL]->(t:ToolUsage)
                DETACH DELETE u, c, t
            """
            session.run(query, user_id=user_id)

    def close(self):
        """Close the database connection when done."""
        self.driver.close()