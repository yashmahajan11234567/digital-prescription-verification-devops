"""Database models and utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Prescription:
    """Prescription model."""
    id: int
    verification_id: str
    patient_name: str
    patient_reference: str
    doctor_name: str
    clinic_name: str
    doctor_id: Optional[int] = None
    hospital_id: Optional[int] = None
    medicine_name: str
    dosage: str
    instructions: str
    issue_date: str
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row: Any) -> "Prescription":
        """Create Prescription from database row."""
        return cls(
            id=row["id"],
            verification_id=row["verification_id"],
            patient_name=row["patient_name"],
            patient_reference=row["patient_reference"],
            doctor_name=row["doctor_name"],
            clinic_name=row["clinic_name"],
            doctor_id=row["doctor_id"] if "doctor_id" in row.keys() else None,
            hospital_id=row["hospital_id"] if "hospital_id" in row.keys() else None,
            medicine_name=row["medicine_name"],
            dosage=row["dosage"],
            instructions=row["instructions"],
            issue_date=row["issue_date"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def is_active(self) -> bool:
        """Check if prescription is active."""
        return self.status == "active"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "verification_id": self.verification_id,
            "patient_name": self.patient_name,
            "patient_reference": self.patient_reference,
            "doctor_name": self.doctor_name,
            "clinic_name": self.clinic_name,
            "doctor_id": self.doctor_id,
            "hospital_id": self.hospital_id,
            "medicine_name": self.medicine_name,
            "dosage": self.dosage,
            "instructions": self.instructions,
            "issue_date": self.issue_date,
            "status": self.status,
            "created_at": self.created_at,
        }


def generate_verification_id() -> str:
    """Generate a unique verification ID."""
    import uuid
    return f"RX-{uuid.uuid4().hex[:10].upper()}"


def get_current_timestamp() -> str:
    """Get current UTC timestamp as ISO format string."""
    return datetime.now(timezone.utc).isoformat()