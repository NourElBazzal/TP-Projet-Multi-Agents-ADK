"""
main.py
-------
Script principal — Runner programmatique.

Ce fichier remplit la contrainte #7 du TP :
"Un script main.py qui instancie Runner + InMemorySessionService"

Il permet de lancer le système en ligne de commande sans passer par `adk web`.
Utile pour tester rapidement ou pour les démonstrations en terminal.

Usage :
    python main.py
    python main.py "I am in Saida with my family. Where can we find shelter?"
"""

import asyncio
import sys
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from my_agent.agent import root_agent


APP_NAME = "lebanon-aid-assistant"
USER_ID = "user_demo"
SESSION_ID = "session_001"


async def run_agent(user_message: str) -> str:
    """
    Lance une conversation avec le système multi-agents
    et retourne la réponse finale de l'assistant.

    Args:
        user_message: message utilisateur

    Returns:
        str: réponse finale générée par l'agent
    """
    session_service = InMemorySessionService()

    # Création de session avec un state initial simple
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={
            "user_location": "Unknown",
            "user_needs": "Not yet assessed",
            "loop_iteration": 0,
        },
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    user_content = Content(
        role="user",
        parts=[Part(text=user_message)],
    )

    print(f"\n{'─' * 60}")
    print(f"👤 USER: {user_message}")
    print(f"{'─' * 60}\n")

    final_response_parts = []

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                text: Optional[str] = getattr(part, "text", None)
                if text:
                    final_response_parts.append(text)

    final_response = "".join(final_response_parts).strip()

    if not final_response:
        final_response = (
            "No text response was returned by the agent. "
            "Please check the agent configuration and tool execution logs."
        )

    print(f"{'─' * 60}")
    print(f"🤖 ASSISTANT:\n\n{final_response}")
    print(f"{'─' * 60}\n")

    return final_response


def main() -> None:
    """Point d'entrée principal."""
    default_message = (
        "I am in Saida with my family and we had to leave our home. "
        "Where can we find shelter and medical help nearby?"
    )

    user_message = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else default_message

    try:
        asyncio.run(run_agent(user_message))
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as exc:
        print(f"\nError while running the ADK agent: {exc}")


if __name__ == "__main__":
    main()