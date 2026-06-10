"""
Gruha Alankara — Booking Agent

Manages product bookings, order tracking, and status updates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from app.database.mongo import (
    insert_one,
    find_by_id,
    find_many,
    update_by_id,
)
from config.constants import AgentName, BookingStatus, MongoCollection
from config.logging_config import get_logger

logger = get_logger(__name__)


class BookingAgent(BaseAgent):
    """
    Booking management agent.

    Handles:
    - Creating new bookings/orders
    - Updating booking status
    - Tracking order progress
    """

    name = AgentName.BOOKING
    description = "Manages product bookings, order tracking, and status updates"
    supported_task_types = [
        "create_booking",
        "update_status",
        "track_order",
        "list_bookings",
    ]
    estimated_latency_s = 5.0

    def _get_capabilities(self) -> List[str]:
        return [
            "Create product bookings and orders",
            "Update order status through the fulfillment pipeline",
            "Track order delivery status",
            "List and filter user bookings",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "create_booking": self._create_booking,
            "update_status": self._update_status,
            "track_order": self._track_order,
            "list_bookings": self._list_bookings,
        }

        handler = handlers.get(task.task_type)
        if not handler:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Unknown task type: {task.task_type}"],
            )

        return await handler(task)

    async def _create_booking(self, task: AgentTask) -> AgentResult:
        """Create a new booking."""
        user_id = task.parameters.get("user_id", "")
        products = task.parameters.get("products", [])
        payment_info = task.parameters.get("payment_info", {})
        delivery_address = task.parameters.get("delivery_address", {})
        project_id = task.parameters.get("project_id")

        if not products:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["No products specified for booking"],
            )

        # Calculate totals
        subtotal = sum(
            p.get("price", 0) * p.get("quantity", 1) for p in products
        )
        gst = subtotal * 0.18  # 18% GST
        delivery_charge = 0 if subtotal > 5000 else 499
        total = subtotal + gst + delivery_charge

        booking = {
            "user_id": user_id,
            "project_id": project_id,
            "products": products,
            "subtotal_inr": round(subtotal, 2),
            "gst_inr": round(gst, 2),
            "delivery_charge_inr": delivery_charge,
            "total_inr": round(total, 2),
            "status": BookingStatus.DRAFT,
            "payment_info": payment_info,
            "delivery_address": delivery_address,
            "status_history": [
                {
                    "status": BookingStatus.DRAFT,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": "Booking created",
                }
            ],
        }

        booking_id = insert_one(MongoCollection.BOOKINGS, booking)

        logger.info(
            "booking_created",
            booking_id=booking_id,
            user_id=user_id,
            total=total,
            items=len(products),
        )

        # Fetch the complete booking with all fields including timestamps
        created_booking = find_by_id(MongoCollection.BOOKINGS, booking_id)

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "booking_id": booking_id,
                "status": BookingStatus.DRAFT,
                "subtotal_inr": round(subtotal, 2),
                "gst_inr": round(gst, 2),
                "delivery_charge_inr": delivery_charge,
                "total_inr": round(total, 2),
                "item_count": len(products),
                "booking": created_booking,  # Include full booking details
                "created_at": created_booking.get("created_at") if created_booking else None,
            },
        )

    async def _update_status(self, task: AgentTask) -> AgentResult:
        """Update a booking's status."""
        booking_id = task.parameters.get("booking_id", "")
        new_status = task.parameters.get("status", "")
        note = task.parameters.get("note", "")

        if not booking_id or not new_status:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["booking_id and status are required"],
            )

        # Validate status transition
        valid_statuses = [
            BookingStatus.DRAFT,
            BookingStatus.CONFIRMED,
            BookingStatus.PROCESSING,
            BookingStatus.SHIPPED,
            BookingStatus.DELIVERED,
            BookingStatus.CANCELLED,
            BookingStatus.REFUNDED,
        ]

        if new_status not in valid_statuses:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Invalid status: {new_status}"],
            )

        status_entry = {
            "status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }

        updated = update_by_id(
            MongoCollection.BOOKINGS,
            booking_id,
            {
                "$set": {"status": new_status},
                "$push": {"status_history": status_entry},
            },
        )

        if not updated:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Booking not found: {booking_id}"],
            )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "booking_id": booking_id,
                "new_status": new_status,
                "updated": True,
            },
        )

    async def _track_order(self, task: AgentTask) -> AgentResult:
        """Track order status and history."""
        booking_id = task.parameters.get("booking_id", "")

        booking = find_by_id(MongoCollection.BOOKINGS, booking_id)
        if not booking:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Booking not found: {booking_id}"],
            )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "booking_id": booking_id,
                "current_status": booking.get("status"),
                "total_inr": booking.get("total_inr"),
                "products": booking.get("products", []),
                "status_history": booking.get("status_history", []),
                "delivery_address": booking.get("delivery_address", {}),
            },
        )

    async def _list_bookings(self, task: AgentTask) -> AgentResult:
        """List bookings for a user."""
        user_id = task.parameters.get("user_id", "")
        status_filter = task.parameters.get("status")
        limit = task.parameters.get("limit", 20)

        query: Dict[str, Any] = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter

        bookings = find_many(
            MongoCollection.BOOKINGS,
            query,
            sort=[("created_at", -1)],
            limit=limit,
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "bookings": bookings,
                "total_count": len(bookings),
            },
        )
