"""
agent.py
--------
Architecture multi-agents ADK pour un assistant d'aide aux déplacés au Liban.

Objectif :
- proposer des shelters
- donner des contacts médicaux
- trouver de l'aide alimentaire
- fournir une vue d'ensemble des ressources
- signaler la nécessité de confirmer avant déplacement
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools.agent_tool import AgentTool

from .tools import (
    get_shelters_by_location,
    get_hotline_by_region,
    get_medical_resources,
    get_food_and_aid,
    get_emergency_summary,
)
from .callbacks import log_agent_start, log_agent_end, log_tool_call


MODEL_NAME = "gemini-2.5-pro"



# AGENT 1 — ShelterAgent
shelter_agent = LlmAgent(
    name="ShelterAgent",
    model=MODEL_NAME,
    description="Finds nearby shelters and regional shelter hotlines in Lebanon.",
    instruction="""
You help displaced people find shelters in Lebanon.

Important rules:
- Extract the user's city or region from the conversation.
- Call get_shelters_by_location once.
- Call get_hotline_by_region once.
- Use the conversation location directly. Do not invent a location.
- If the location is unclear, say clearly that the city/region must be specified.
- Present at most 3 shelter options.
- Always remind the user to call before going.
- Reply in the user's language.
""",
    tools=[get_shelters_by_location, get_hotline_by_region],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    before_tool_callback=log_tool_call,
    output_key="shelter_result",
)



# AGENT 2 — CheckAgent
check_agent = LlmAgent(
    name="CheckAgent",
    model=MODEL_NAME,
    description="Checks that the shelter response contains key safety guidance.",
    instruction="""
You review the previous shelter result stored in {shelter_result}.

Your job:
- Check whether the answer includes at least one contact number or hotline.
- Check whether it reminds the user to call before going.
- If both are present, reply with a short validation note.
- If something is missing, add a short safety note.
- Do not call tools.
- Reply in the user's language.
""",
    tools=[],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    output_key="check_result",
)



# WORKFLOW 1 — SequentialAgent
# Shelter search -> safety check
shelter_pipeline = SequentialAgent(
    name="ShelterPipeline",
    description="Find shelters first, then validate the safety guidance.",
    sub_agents=[shelter_agent, check_agent],
)



# AGENT 3 — OverviewAgent
overview_agent = LlmAgent(
    name="OverviewAgent",
    model=MODEL_NAME,
    description="Provides a broad overview of emergency resources in a Lebanese area.",
    instruction="""
You provide a broad emergency overview for displaced people in Lebanon.

Your job:
- Extract the city or region from the conversation.
- Call get_emergency_summary exactly once.
- Summarize shelters, medical lines, food aid, and hotlines.
- End with a short warning that the user should call before going.
- Reply in the user's language.
- If the location is missing, ask for the city or region in Lebanon.
""",
    tools=[get_emergency_summary],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    before_tool_callback=log_tool_call,
    output_key="overview_result",
)



# WORKFLOW 2 — LoopAgent
# Minimal loop for the TP requirement
overview_loop = LoopAgent(
    name="OverviewLoop",
    description="Runs one controlled overview pass for emergency resources.",
    sub_agents=[overview_agent],
    max_iterations=1,
)



# AGENT 4 — MedicalAgent
# Used via AgentTool
medical_agent = LlmAgent(
    name="MedicalAgent",
    model=MODEL_NAME,
    description="Provides national medical emergency lines for displaced people.",
    instruction="""
You help displaced people with medical support in Lebanon.

Your job:
- Call get_medical_resources exactly once.
- Present the medical emergency lines clearly.
- Start with the most urgent line first.
- Mention whether the line is free and/or 24h when available.
- End with a short note telling the user to call immediately in emergencies.
- Reply in the user's language.
""",
    tools=[get_medical_resources],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    before_tool_callback=log_tool_call,
    output_key="medical_result",
)



# AGENT 5 — FoodAgent
# Used via AgentTool
food_agent = LlmAgent(
    name="FoodAgent",
    model=MODEL_NAME,
    description="Finds food aid and humanitarian support in Lebanon.",
    instruction="""
You help displaced people find food aid and humanitarian support in Lebanon.

Your job:
- Extract the user's city or region from the conversation.
- Call get_food_and_aid exactly once.
- Present the most relevant options clearly.
- Mention when contact details are missing or need confirmation.
- End with a reminder to confirm availability before going.
- Reply in the user's language.
- If the location is missing, ask for the city or region.
""",
    tools=[get_food_and_aid],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    before_tool_callback=log_tool_call,
    output_key="food_result",
)



# ROOT AGENT — CoordinatorAgent
# transfer_to_agent + AgentTool
coordinator_agent = LlmAgent(
    name="CoordinatorAgent",
    model=MODEL_NAME,
    description="Main coordinator for a displaced-person support assistant in Lebanon.",
    instruction="""
You are the main coordinator for an emergency support assistant for displaced people in Lebanon.

You must choose the BEST next action based on the user's request.

Routing rules:
1. If the user mainly asks for shelter, place to stay, accommodation, abri, dormir:
   -> transfer_to_agent with agent_name="ShelterPipeline"

2. If the user mainly asks for an overview, all resources, everything nearby, all help, tout:
   -> transfer_to_agent with agent_name="OverviewLoop"

3. If the user mainly asks for medical help, injury, doctor, hospital, psychological help:
   -> call the MedicalAgent tool

4. If the user mainly asks for food, meals, aid, hungry, nourishment:
   -> call the FoodAgent tool

5. If the request mixes several needs strongly (for example shelter + medical + food):
   -> transfer_to_agent with agent_name="OverviewLoop"

6. If the location is missing:
   -> ask: "Which city or region in Lebanon are you in?"

General rules:
- Reply in the user's language.
- Be calm, supportive, and clear.
- Never invent addresses or numbers.
- Prefer concise, structured answers.
""",
    tools=[
        AgentTool(agent=medical_agent),
        AgentTool(agent=food_agent),
    ],
    sub_agents=[
        shelter_pipeline,
        overview_loop,
    ],
    before_agent_callback=log_agent_start,
    after_agent_callback=log_agent_end,
    before_tool_callback=log_tool_call,
    output_key="final_result",
)

root_agent = coordinator_agent