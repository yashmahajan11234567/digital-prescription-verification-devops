"""Doctor routes."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from flask import current_app, flash, redirect, render_template, request, session, url_for

from src.decorators import require_role
from src.doctor import bp
from src.models import get_unread_count


@bp.route("/prescriptions/new", methods=["GET", "POST"], endpoint="issue_prescription")
@require_role("doctor")
def issue_prescription():
    if request.method == "POST":
        fields = {
            "patient_name": request.form.get("patient_name", "").strip(),
            "patient_reference": request.form.get("patient_reference", "").strip(),
            "medicine_name": request.form.get("medicine_name", "").strip(),
            "dosage": request.form.get("dosage", "").strip(),
            "instructions": request.form.get("instructions", "").strip(),
            "issue_date": request.form.get("issue_date", "").strip(),
        }
        missing = [name.replace("_", " ") for name, value in fields.items() if not value]
        if missing:
            flash(f"Please complete: {', '.join(missing)}.", "error")
            return render_template("issue.html", form=fields), 400

        try:
            date.fromisoformat(fields["issue_date"])
        except ValueError:
            flash("Issue date must be a valid date.", "error")
            return render_template("issue.html", form=fields), 400

        # Get authenticated doctor information from session
        db = current_app.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name, hospital_id FROM users WHERE id = ?", (session["user_id"],))
        doctor = cursor.fetchone()

        if not doctor:
            flash("Doctor not found.", "error")
            return redirect(url_for("auth.logout"))

        doctor_id = doctor["id"]
        doctor_name = doctor["name"]
        hospital_id = doctor["hospital_id"]

        # Get hospital name for clinic_name field (for backward compatibility)
        clinic_name = ""
        if hospital_id:
            cursor.execute("SELECT name FROM hospitals WHERE id = ?", (hospital_id,))
            hospital = cursor.fetchone()
            if hospital:
                clinic_name = hospital["name"]

        verification_id = f"RX-{uuid.uuid4().hex[:10].upper()}"
        cursor.execute(
            """
            INSERT INTO prescriptions
            (verification_id, patient_name, patient_reference, doctor_name, clinic_name,
             doctor_id, hospital_id, medicine_name, dosage, instructions, issue_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verification_id,
                fields["patient_name"], fields["patient_reference"], doctor_name, clinic_name,
                doctor_id, hospital_id, fields["medicine_name"], fields["dosage"],
                fields["instructions"], fields["issue_date"],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        db.commit()
        return redirect(url_for("pharmacist.verification_result", verification_id=verification_id))

    # For GET request, pre-populate form with current doctor info
    db = current_app.get_db()
    cursor = db.cursor()
    cursor.execute("SELECT name FROM users WHERE id = ?", (session["user_id"],))
    doctor = cursor.fetchone()
    doctor_name = doctor["name"] if doctor else ""

    return render_template("issue.html", form={
        "issue_date": date.today().isoformat(),
        "doctor_name": doctor_name
    })


@bp.get("/prescriptions", endpoint="prescriptions")
@require_role("doctor")
def prescriptions():
    db = current_app.get_db()
    cursor = db.cursor()

    # Optional date filter
    date_filter = request.args.get("date")

    if date_filter:
        cursor.execute("SELECT * FROM prescriptions WHERE issue_date = ? ORDER BY created_at DESC", (date_filter,))
    else:
        cursor.execute("SELECT * FROM prescriptions ORDER BY created_at DESC")

    records = cursor.fetchall()
    # Convert sqlite3.Row objects to plain dicts for reliable template rendering
    records = [dict(record) for record in records]

    # Get unread notification count
    unread_count = get_unread_count(db, session["user_id"])

    return render_template("prescriptions.html", prescriptions=records, date_filter=date_filter, unread_count=unread_count)


@bp.post("/prescriptions/<int:prescription_id>/revoke", endpoint="revoke_prescription")
@require_role("doctor")
def revoke_prescription(prescription_id: int):
    db = current_app.get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE prescriptions SET status = 'revoked' WHERE id = ?", (prescription_id,))
    if cursor.rowcount == 0:
        from flask import abort
        abort(404)
    db.commit()
    flash("Prescription revoked. Future checks will show it as invalid.", "success")
    return redirect(url_for("doctor.prescriptions"))


@bp.get("/notifications", endpoint="notifications")
@require_role("doctor")
def notifications():
    """View all notifications for the doctor."""
    db = current_app.get_db()
    from src.models import get_notifications_by_user
    notifications = get_notifications_by_user(db, session["user_id"])
    unread_count = get_unread_count(db, session["user_id"])
    return render_template("doctor/notifications.html", notifications=notifications, unread_count=unread_count)


@bp.post("/notifications/<int:notification_id>/read", endpoint="mark_notification_read")
@require_role("doctor")
def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    db = current_app.get_db()
    from src.models import mark_notification_read
    mark_notification_read(db, notification_id, session["user_id"])
    flash("Notification marked as read.", "success")
    return redirect(url_for("doctor.notifications"))


@bp.post("/notifications/read-all", endpoint="mark_all_read")
@require_role("doctor")
def mark_all_read():
    """Mark all notifications as read."""
    db = current_app.get_db()
    from src.models import mark_all_read
    count = mark_all_read(db, session["user_id"])
    flash(f"{count} notification(s) marked as read.", "success")
    return redirect(url_for("doctor.notifications"))


@bp.get("/notifications/poll", endpoint="notifications_poll")
@require_role("doctor")
def notifications_poll():
    """Poll endpoint for unread notification count."""
    db = current_app.get_db()
    from src.models import get_unread_count
    unread_count = get_unread_count(db, session["user_id"])
    return {"unread_count": unread_count}