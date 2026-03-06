"""
callbacks.py
------------
Callbacks simples pour tracer l'exécution des agents et des tools.
Objectif : debug clair + conformité au TP.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def log_agent_start(callback_context: CallbackContext) -> None:
    """
    Callback exécuté avant le démarrage d'un agent.
    Enregistre le temps de départ dans le state partagé.
    """
    agent_name = callback_context.agent_name
    callback_context.state[f"_start_time_{agent_name}"] = time.time()

    print("\n" + "=" * 60)
    print(f"🤖 START AGENT: {agent_name}")
    print("=" * 60)


def log_agent_end(callback_context: CallbackContext) -> None:
    """
    Callback exécuté après la fin d'un agent.
    Affiche la durée approximative d'exécution.
    """
    agent_name = callback_context.agent_name
    start_time = callback_context.state.get(f"_start_time_{agent_name}")

    if start_time is not None:
        duration = round(time.time() - start_time, 2)
        print(f"✅ END AGENT: {agent_name} | duration={duration}s")
    else:
        print(f"✅ END AGENT: {agent_name}")


def log_tool_call(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
) -> Optional[Dict[str, Any]]:
    """
    Callback exécuté avant l'appel à un tool.
    Loggue simplement le nom du tool et ses arguments.
    Ne bloque pas l'exécution.
    """
    print("\n" + "-" * 60)
    print(f"🔧 TOOL CALL: {tool.name}")
    print(f"ARGS: {args}")
    print("-" * 60)

    return None