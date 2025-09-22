from agent import VacationArithmeticAgent
import sys

def main():
    agent = VacationArithmeticAgent()

    print("LangGraph Vacation and Arithmetic Assistant")
    print("\nSpecial commands:")
    print("* 'history' - View conversation history")
    print("* 'stats' - View conversation statistics")
    print("* 'exit' - Quit the application")
    print("-" * 50)

    user_id = "default_user"
    print(f"Welcome {user_id}! Starting conversation...\n")

    try:
        while True:
            user_input = input(f"[{user_id}]: ").strip()

            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            elif user_input.lower() == 'history':
                history = agent.get_conversation_history(user_id)
                print(f"\nConversation History (last {len(history)} messages):")
                for i, item in enumerate(history[-10:], 1):
                    if isinstance(item, dict):
                        message = item.get('message', 'N/A')
                        response = item.get('response', 'N/A')
                        print(f"  {i}. User: {message}")
                        print(f"      Assistant: {response[:100]}{'...' if len(response) > 100 else ''}")
                    else:
                        # LangGraph message format
                        role = "User" if hasattr(item, 'content') and item.__class__.__name__ == "HumanMessage" else "Assistant"
                        content = item.content[:100] + "..." if len(item.content) > 100 else item.content
                        print(f"  {i}. {role}: {content}")
                print()
                continue
            elif user_input.lower() == 'stats':
                stats = agent.get_conversation_stats(user_id)
                print(f"\nConversation Statistics:")
                print(f"  * Total conversations: {stats['conversation_count']}")
                print(f"  * Last tool used: {stats['last_tool_used']}")
                print(f"  * Total messages: {stats['total_messages']}")
                print()
                continue

            if not user_input:
                continue

            print("Processing...")
            response = agent.run(user_input, user_id)
            print(f"\nAssistant: {response}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        agent.close()

if __name__ == "__main__":
    main()