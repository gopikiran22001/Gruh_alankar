"""Gruha Alankara — Design, Furniture, Web, Booking, Memory, Critic Agent Tests (stubs)."""

import pytest
from app.agents.schemas import AgentTask, TaskStatusEnum


# Stub test files — each agent's test follows the same pattern
# as test_budget_agent.py and test_buddy_agent.py

class TestDesignAgent:
    def test_supported_task_types(self):
        from app.agents.design_agent import DesignAgent
        agent = DesignAgent()
        assert agent.can_handle("generate_design")
        assert agent.can_handle("suggest_layout")


class TestFurnitureAgent:
    def test_supported_task_types(self):
        from app.agents.furniture_agent import FurnitureAgent
        agent = FurnitureAgent()
        assert agent.can_handle("recommend_products")
        assert agent.can_handle("rank_products")


class TestWebAgent:
    def test_parse_price(self):
        from app.agents.web_agent import WebAgent
        agent = WebAgent()
        assert agent._parse_price("₹12,999") == 12999.0
        assert agent._parse_price("Rs. 5000") == 5000.0
        assert agent._parse_price("") is None


class TestBookingAgent:
    def test_supported_task_types(self):
        from app.agents.booking_agent import BookingAgent
        agent = BookingAgent()
        assert agent.can_handle("create_booking")
        assert agent.can_handle("track_order")


class TestMemoryAgent:
    def test_collection_mapping(self):
        from app.agents.memory_agent import MemoryAgent
        assert MemoryAgent._get_collection_for_type("preference") == "user_memory"
        assert MemoryAgent._get_collection_for_type("conversation") == "conversation_memory"


class TestCriticAgent:
    def test_supported_task_types(self):
        from app.agents.critic_agent import CriticAgent
        agent = CriticAgent()
        assert agent.can_handle("validate")
        assert agent.can_handle("criticize")
