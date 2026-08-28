"""Pharmacist routes."""
from __future__ import annotations

from datetime import datetime, timezone
from flask import current_app, flash, redirect, render_template, request, session, url_for

from src.decorators import require_role, require_any_role
from src.pharmacist import bp
from src.models.user import get_user_by_id


@bp.get("/verify", endpoint="verify_form")
@require_role("pharmacist")
def verify_form():
    return render_template("verify.html")


@bp.post("/verify", endpoint="verify_submit")
@require_role("pharmacist")
def verify_submit():
    verification_id = request.form.get("verification_id", "").strip().upper()
    if not verification_id:
        flash("Enter a prescription ID to verify it.", "error")
        return redirect(url_for("pharmacist.verify_form"))
    return redirect(url_for("pharmacist.verification_result", verification_id=verification_id))


@bp.get("/verify/<verification_id>", endpoint="verification_result")
@require_any_role("doctor", "pharmacist")
def verification_result(verification_id: str):
    db = current_app.get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE verification_id = ?", (verification_id.upper(),))
    prescription = cursor.fetchone()
    # Convert sqlite3.Row to dict for reliable template rendering
    if prescription:
        prescription = dict(prescription)
        # Get doctor and hospital info using FKs when available, fallback to text fields
        if prescription.get("doctor_id"):
            cursor.execute("SELECT name FROM users WHERE id = ?", (prescription["doctor_id"],))
            doctor = cursor.fetchone()
            if doctor:
                prescription["doctor_name"] = doctor["name"]
        if prescription.get("hospital_id"):
            cursor.execute("SELECT name FROM hospitals WHERE id = ?", (prescription["hospital_id"],))
            hospital = cursor.fetchone()
            if hospital:
                prescription["clinic_name"] = hospital["name"]

        # Get pharmacist info if received
        if prescription["received_by_user_id"]:
            cursor.execute("SELECT name FROM users WHERE id = ?", (prescription["received_by_user_id"],))
            pharmacist = cursor.fetchone()
            if pharmacist:
                prescription["received_by_name"] = pharmacist["name"]
    return render_template("result.html", prescription=prescription, verification_id=verification_id)


def _create_notification_if_not_exists(db, cursor, user_id: int, prescription_id: int, message: str, now: str) -> bool:
    """Create a notification if one doesn't already exist for this user/prescription/message combination.

    Returns True if notification was created, False if it already existed.
    """
    # Check if notification already exists for this user+prescription+message pattern
    cursor.execute(
        """
        SELECT id FROM notifications
        WHERE user_id = ? AND prescription_id = ? AND message LIKE ?
        """,
        (user_id, prescription_id, f"%{prescription_id}%"),
    )
    existing = cursor.fetchone()
    if existing:
        return False

    cursor.execute(
        """
        INSERT INTO notifications (user_id, message, is_read, created_at, prescription_id)
        VALUES (?, ?, 0, ?, ?)
        """,
        (user_id, message, now, prescription_id),
    )
    return True


@bp.post("/receive/<int:prescription_id>", endpoint="receive_medicine")
@require_role("pharmacist")
def receive_medicine(prescription_id: int):
    """Mark prescription as received by pharmacist."""
    db = current_app.get_db()
    cursor = db.cursor()

    # Get the prescription
    cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (prescription_id,))
    prescription = cursor.fetchone()
    if not prescription:
        flash("Prescription not found.", "error")
        return redirect(url_for("pharmacist.verify_form"))

    prescription = dict(prescription)

    # Check if already received
    if prescription["status"] == "received":
        flash("This prescription has already been marked as received.", "error")
        return redirect(url_for("pharmacist.verification_result", verification_id=prescription["verification_id"]))

    # Check if revoked
    if prescription["status"] == "revoked":
        flash("Cannot mark a revoked prescription as received.", "error")
        return redirect(url_for("pharmacist.verification_result", verification_id=prescription["verification_id"]))

    # Check if active
    if prescription["status"] != "active":
        flash("Only active prescriptions can be marked as received.", "error")
        return redirect(url_for("pharmacist.verification_result", verification_id=prescription["verification_id"]))

    # Update prescription to received
    now = datetime.now(timezone.utc).isoformat()
    pharmacist_id = session["user_id"]
    pharmacist_name = session.get("name", "Pharmacist")

    cursor.execute("""
        UPDATE prescriptions
        SET status = 'received', received_at = ?, received_by_user_id = ?
        WHERE id = ?
    """, (now, pharmacist_id, prescription_id))
    db.commit()

    verification_id = prescription["verification_id"]
    doctor_name = prescription["doctor_name"]
    notification_created_count = 0

    # Create notification for the prescribing doctor
    # Use doctor_id from prescription (primary) with fallback to name matching for legacy data
    doctor_id_to_notify = None
    doctor_name_for_msg = doctor_name  # fallback

    if prescription.get("doctor_id"):
        # New prescription: use FK relationship
        doctor_id_to_notify = prescription["doctor_id"]
        cursor.execute("SELECT name FROM users WHERE id = ?", (doctor_id_to_notify,))
        doctor = cursor.fetchone()
        if doctor:
            doctor_name_for_msg = doctor["name"]
    else:
        # Legacy prescription: fallback to name matching
        try:
            cursor.execute("SELECT id FROM users WHERE name = ? AND role = 'doctor'", (doctor_name,))
            doctor = cursor.fetchone()
            if doctor:
                doctor_id_to_notify = doctor["id"]
        except Exception as e:
            # Log the error but continue - don't let one doctor notification failure
            # prevent admin notifications
            current_app.logger.error(f"Failed to create notification for doctor: {e}")

    if doctor_id_to_notify:
        doctor_msg = (
            f"Medicine for prescription {verification_id} has been received by "
            f"pharmacist {pharmacist_name}."
        )
        if _create_notification_if_not_exists(db, cursor, doctor_id_to_notify, prescription_id, doctor_msg, now):
            notification_created_count += 1

    # Create notifications for all active admins
    try:
        cursor.execute("SELECT id FROM users WHERE role = 'admin' AND is_active = 1")
        admins = cursor.fetchall()
        for admin in admins:
            try:
                admin_msg = f"Prescription {verification_id} has been marked as received by pharmacist {pharmacist_name}."
                if _create_notification_if_not_exists(db, cursor, admin["id"], prescription_id, admin_msg, now):
                    notification_created_count += 1
            except Exception as e:
                # Log the error but continue with other admins
                current_app.logger.error(f"Failed to create notification for admin {admin['id']}: {e}")
    except Exception as e:
        # Log error in querying admins but continue
        current_app.logger.error(f"Failed to query for admins: {e}")

    db.commit()

    if notification_created_count > 0:
        flash("Medicine marked as received. Doctor and admins have been notified.", "success")
    else:
        flash("Medicine marked as received. Notifications already exist.", "success")
    return redirect(url_for("pharmacist.verification_result", verification_id=verification_id))