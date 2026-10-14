"""
CogniVault Agno AgentOS Package.
Provides local-first, evidence-grounded agent services and REST API.
"""
from __future__ import annotations

from .service import AgentOSTutorService
from .tutor_agent import EvidenceTutorAgent
from .app import create_agent_os_app, app

__all__ = [
    "AgentOSTutorService",
    "EvidenceTutorAgent",
    "create_agent_os_app",
    "app",
]
