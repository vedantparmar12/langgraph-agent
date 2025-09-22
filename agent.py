from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from tools.arithmetic_tool import ArithmeticTool
from tools.vacation_tool import VacationTool
from memory.neo4j_memory import Neo4jMemory
import operator
import os
from dotenv import load_dotenv

load_dotenv()

def add_messages(existing: list, new: list):
    return existing + new

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    conversation_count: int
    last_tool_used: str

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state['messages']
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tools"
    return "__end__"

class VacationArithmeticAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv('OPENROUTER_API_KEY'),
            model=os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-haiku'),
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "LangGraph Vacation Arithmetic Agent"
            }
        )

        self.tools = [ArithmeticTool(), VacationTool()]
        self.tool_node = ToolNode(self.tools)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.memory = MemorySaver()
        self.neo4j_memory = Neo4jMemory()
        self.graph = self._create_graph()

    def _create_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self.tool_node)
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=self.memory)

    def _call_model(self, state: AgentState):
        messages = state["messages"]
        response = self.llm_with_tools.invoke(messages)

        new_count = state.get("conversation_count", 0) + 1
        last_tool = "none"

        if hasattr(response, 'tool_calls') and response.tool_calls:
            last_tool = response.tool_calls[0]["name"]

        return {
            "messages": [response],
            "conversation_count": new_count,
            "last_tool_used": last_tool
        }

    def run(self, message: str, user_id: str = 'default_user') -> str:
        config = {"configurable": {"thread_id": user_id}}

        system_prompt = SystemMessage(content="""You are a friendly and helpful assistant that can help with arithmetic calculations and provide country information.

You have access to two tools:
1. arithmetic_calculator: For mathematical calculations and expressions
2. vacation_finder: For getting country information (capital, currency, region)

For simple greetings like "hello" or "hi", respond naturally and offer to help. For questions that require calculations or country information, use the appropriate tools. Be conversational and helpful.""")

        initial_state = {
            "messages": [system_prompt, HumanMessage(content=message)],
            "user_id": user_id,
            "conversation_count": 0,
            "last_tool_used": "none"
        }

        events = self.graph.stream(initial_state, config)

        response_content = ""
        for event in events:
            for value in event.values():
                if "messages" in value:
                    last_message = value["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        response_content = last_message.content

        final_response = response_content if response_content else "I couldn't process your request. Please try again."

        # Store conversation in Neo4j
        try:
            conversation_id = self.neo4j_memory.store_conversation(
                user_id=user_id,
                message=message,
                response=final_response
            )
        except Exception as e:
            print(f"Warning: Could not store conversation in Neo4j: {e}")

        return final_response

    def get_conversation_history(self, user_id: str, limit: int = 10):
        try:
            # Try to get from Neo4j first
            neo4j_history = self.neo4j_memory.get_conversation_history(user_id, limit)
            if neo4j_history:
                return neo4j_history
        except Exception as e:
            print(f"Warning: Could not retrieve from Neo4j: {e}")

        # Fallback to LangGraph memory
        config = {"configurable": {"thread_id": user_id}}
        try:
            state = self.graph.get_state(config)
            messages = state.values.get("messages", [])
            return messages[-limit:] if len(messages) > limit else messages
        except:
            return []

    def get_conversation_stats(self, user_id: str):
        config = {"configurable": {"thread_id": user_id}}
        try:
            state = self.graph.get_state(config)
            return {
                "conversation_count": state.values.get("conversation_count", 0),
                "last_tool_used": state.values.get("last_tool_used", "none"),
                "total_messages": len(state.values.get("messages", []))
            }
        except:
            return {"conversation_count": 0, "last_tool_used": "none", "total_messages": 0}

    def close(self):
        try:
            self.neo4j_memory.close()
        except:
            pass
