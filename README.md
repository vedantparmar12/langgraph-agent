# My LangGraph Agent Implementation

## What I Built

I created a conversational AI agent using LangGraph that can do math calculations and look up country information. The agent remembers conversations using a Neo4j database and provides an interactive command-line interface.

## How I Implemented It

### Core Agent Structure
I built the agent using LangGraph's StateGraph pattern. The agent flows between calling the language model and using tools based on what the user asks. I set up proper state management to track conversations, user interactions, and tool usage.

### Two Main Tools
I implemented two tools that the agent can use:

**Arithmetic Calculator**: I made this tool handle both simple operations like "5 + 3" and complex expressions like "2+3*4-5/2". I used Python's AST module to safely evaluate mathematical expressions without security risks.

**Country Information Tool**: I connected this to the free REST Countries API to get real data about any country including capital, currency, and region.

### Memory System
I implemented a dual memory approach:
- LangGraph's built-in memory for active conversation state
- Neo4j graph database for persistent storage across sessions

The Neo4j system stores users and their conversations as connected nodes, making it easy to retrieve conversation history and track user interactions over time.

### User Experience
I created a simple command-line interface that automatically uses "default_user" so people can start asking questions immediately without setup. I added special commands like "history" and "stats" to let users see their past conversations and usage statistics.

### Error Handling
I made the system robust by handling API failures gracefully and providing clear error messages. Instead of crashing, the agent explains what went wrong and suggests how to fix it.



## What Works

The agent successfully:
- Performs accurate mathematical calculations following proper order of operations
- Retrieves real country information including currencies with symbols
- Stores all conversations in the Neo4j database
- Maintains conversation context during sessions
- Provides helpful error messages when things go wrong
- Supports multiple users with separate conversation histories
