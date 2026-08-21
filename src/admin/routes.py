"""Admin routes for hospital hierarchy and dashboard."""
from __future__ import annotations

from datetime import date
from flask import current_app, render_template, request, session, flash, redirect, url_for

from src.decorators import require_admin
from src.admin import bp


@bp.get("/", endpoint="dashboard")
@require_admin()
def dashboard():
    """Admin dashboard with statistics."""
    db = current_app.get_db()
    cursor = db.cursor()

    # Get counts
    cursor.execute("SELECT COUNT(*) as count FROM hospitals")
    hospital_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'doctor'")
    doctor_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'pharmacist'")
    pharmacist_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prescriptions")
    prescription_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prescriptions WHERE status = 'active'")
    active_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prescriptions WHERE status = 'revoked'")
    revoked_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM prescriptions WHERE status = 'received'")
    received_count = cursor.fetchone()["count"]

    stats = {
        "hospitals": hospital_count,
        "doctors": doctor_count,
        "pharmacists": pharmacist_count,
        "prescriptions": prescription_count,
        "active": active_count,
        "revoked": revoked_count,
        "received": received_count,
    }

    return render_template("admin/dashboard.html", stats=stats)


@bp.get("/hospitals", endpoint="hospitals")
@require_admin()
def hospitals_list():
    """List all hospitals with doctor/pharmacist counts."""
    db = current_app.get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT h.*,
               COUNT(CASE WHEN u.role = 'doctor' THEN 1 END) as doctor_count,
               COUNT(CASE WHEN u.role = 'pharmacist' THEN 1 END) as pharmacist_count
        FROM hospitals h
        LEFT JOIN users u ON u.hospital_id = h.id
        GROUP BY h.id
        ORDER BY h.name
    """)
    hospitals = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/hospitals.html", hospitals=hospitals)


@bp.get("/hospitals/<int:hospital_id>", endpoint="hospital_detail")
@require_admin()
def hospital_detail(hospital_id: int):
    """Show hospital details with doctors and pharmacists."""
    db = current_app.get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hospital = cursor.fetchone()
    if not hospital:
        from flask import abort
        abort(404)

    # Get doctors for this hospital
    cursor.execute("""
        SELECT u.*, COUNT(p.id) as prescription_count
        FROM users u
        LEFT JOIN prescriptions p ON p.doctor_name = u.name
        WHERE u.hospital_id = ? AND u.role = 'doctor'
        GROUP BY u.id
        ORDER BY u.name
    """, (hospital_id,))
    doctors = [dict(row) for row in cursor.fetchall()]

    # Get pharmacists for this hospital
    cursor.execute("""
        SELECT u.*, COUNT(p.id) as verification_count
        FROM users u
        LEFT JOIN prescriptions p ON p.received_by_user_id = u.id
        WHERE u.hospital_id = ? AND u.role = 'pharmacist'
        GROUP BY u.id
        ORDER BY u.name
    """, (hospital_id,))
    pharmacists = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/hospital_detail.html",
                           hospital=dict(hospital),
                           doctors=doctors,
                           pharmacists=pharmacists)


@bp.get("/hospitals/<int:hospital_id>/doctors/<int:doctor_id>", endpoint="doctor_detail")
@require_admin()
def doctor_detail(hospital_id: int, doctor_id: int):
    """Show doctor details with their prescriptions."""
    db = current_app.get_db()
    cursor = db.cursor()

    # Verify hospital exists
    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hospital = cursor.fetchone()
    if not hospital:
        from flask import abort
        abort(404)

    # Verify doctor exists and belongs to this hospital
    cursor.execute("SELECT * FROM users WHERE id = ? AND hospital_id = ? AND role = 'doctor'", (doctor_id, hospital_id))
    doctor = cursor.fetchone()
    if not doctor:
        from flask import abort
        abort(404)

    # Get doctor's prescriptions with optional date filter
    date_filter = request.args.get("date")
    if date_filter:
        cursor.execute("""
            SELECT * FROM prescriptions
            WHERE doctor_name = ? AND issue_date = ?
            ORDER BY created_at DESC
        """, (doctor["name"], date_filter))
    else:
        cursor.execute("""
            SELECT * FROM prescriptions
            WHERE doctor_name = ?
            ORDER BY created_at DESC
        """, (doctor["name"],))

    prescriptions = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/doctor_detail.html",
                           hospital=dict(hospital),
                           doctor=dict(doctor),
                           prescriptions=prescriptions,
                           date_filter=date_filter)


@bp.get("/hospitals/<int:hospital_id>/doctors/<int:doctor_id>/prescriptions", endpoint="doctor_prescriptions")
@require_admin()
def doctor_prescriptions(hospital_id: int, doctor_id: int):
    """Show doctor's prescriptions with date filter (alias for doctor_detail with prescription focus)."""
    return doctor_detail(hospital_id, doctor_id)


@bp.get("/notifications", endpoint="notifications")
@require_admin()
def notifications():
    """View all notifications for the admin."""
    db = current_app.get_db()
    from src.models import get_notifications_by_user, get_unread_count
    notifications = get_notifications_by_user(db, session["user_id"])
    unread_count = get_unread_count(db, session["user_id"])
    return render_template("admin/notifications.html", notifications=notifications, unread_count=unread_count)


@bp.post("/notifications/<int:notification_id>/read", endpoint="mark_notification_read")
@require_admin()
def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    db = current_app.get_db()
    from src.models import mark_notification_read
    mark_notification_read(db, notification_id, session["user_id"])
    flash("Notification marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@bp.post("/notifications/read-all", endpoint="mark_all_read")
@require_admin()
def mark_all_read():
    """Mark all notifications as read."""
    db = current_app.get_db()
    from src.models import mark_all_read
    count = mark_all_read(db, session["user_id"])
    flash(f"{count} notification(s) marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@bp.get("/notifications/poll", endpoint="notifications_poll")
@require_admin()
def notifications_poll():
    """Poll endpoint for unread notification count for admin."""
    db = current_app.get_db()
    from src.models import get_unread_count
    unread_count = get_unread_count(db, session["user_id"])
    return {"unread_count": unread_count}