import asyncio
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from security_agent import app

async def main():
    # Initialize the runner with an in-memory session service
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        auto_create_session=True
    )

    user_id = "test_user"
    session_id = "test_session"

    print("--- Starting Agent Interaction ---")

    # 1. Simple greeting
    print("\nUser: Hello! Who are you?")
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text="Hello! Who are you?")])
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent: {part.text}")

    # 2. Test SecOps / Chronicle integration
    query = "Can you summarize the latest high-severity security alerts from Chronicle for the past 24 hours?"
    print(f"\nUser: {query}")
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=query)])
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent: {part.text}")

    print("\n--- Interaction Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
