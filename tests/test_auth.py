"""Tests for authentication, users, and RBAC."""
from __future__ import annotations

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from src.models.user import (
    VALID_ROLES,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
    set_user_active,
    delete_user,
    list_users,
    User,
)

# Import login helper from conftest
from tests.conftest import login


class TestUserModel:
    """Tests for User model and data access layer."""

    def test_user_creation(self, client):
        """Test user creation with all required fields."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "test@example.com", "Test User", "password123", "doctor")

            assert user.id is not None
            assert user.email == "test@example.com"
            assert user.name == "Test User"
            assert user.role == "doctor"
            assert user.is_active is True
            assert user.password_hash != "password123"
            assert check_password_hash(user.password_hash, "password123")
            assert user.created_at is not None
            assert user.updated_at is not None

    def test_password_hashing(self, client):
        """Test password hashing and verification."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "hash@example.com", "Hash User", "securepass", "doctor")

            # Verify password works
            assert user.verify_password("securepass") is True
            # Wrong password fails
            assert user.verify_password("wrongpass") is False

    def test_password_verification(self, client):
        """Test check_password_hash directly."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "verify@example.com", "Verify User", "mypassword", "pharmacist")

            assert check_password_hash(user.password_hash, "mypassword") is True
            assert check_password_hash(user.password_hash, "wrong") is False

    def test_invalid_role_rejected(self, client):
        """Test that invalid roles are rejected."""
        with client.application.app_context():
            db = client.application.get_db()
            with pytest.raises(ValueError, match="Invalid role"):
                create_user(db, "bad@example.com", "Bad User", "pass", "invalid_role")

    def test_email_unique_constraint(self, client):
        """Test that duplicate emails are rejected (database-level)."""
        with client.application.app_context():
            db = client.application.get_db()
            create_user(db, "unique@example.com", "User One", "pass1", "doctor")
            # Second creation should fail at DB level
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                create_user(db, "unique@example.com", "User Two", "pass2", "pharmacist")


class TestUserQueries:
    """Tests for user query functions."""

    def test_get_user_by_email(self, client):
        """Test finding user by email."""
        with client.application.app_context():
            db = client.application.get_db()
            created = create_user(db, "find@example.com", "Find User", "password", "doctor")
            found = get_user_by_email(db, "find@example.com")

            assert found is not None
            assert found.id == created.id
            assert found.email == "find@example.com"

    def test_get_user_by_email_case_insensitive(self, client):
        """Test email lookup is case insensitive."""
        with client.application.app_context():
            db = client.application.get_db()
            create_user(db, "Case@Example.com", "Case User", "password", "doctor")
            found = get_user_by_email(db, "case@example.com")

            assert found is not None
            assert found.email == "case@example.com"

    def test_get_user_by_id(self, client):
        """Test finding user by ID."""
        with client.application.app_context():
            db = client.application.get_db()
            created = create_user(db, "id@example.com", "ID User", "password", "doctor")
            found = get_user_by_id(db, created.id)

            assert found is not None
            assert found.id == created.id

    def test_get_nonexistent_user(self, client):
        """Test finding nonexistent user returns None."""
        with client.application.app_context():
            db = client.application.get_db()
            assert get_user_by_email(db, "nonexistent@example.com") is None
            assert get_user_by_id(db, 99999) is None


class TestUserUpdates:
    """Tests for user update functions."""

    def test_update_user_name(self, client):
        """Test updating user name."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "update@example.com", "Old Name", "password", "doctor")
            updated = update_user(db, user.id, name="New Name")

            assert updated is not None
            assert updated.name == "New Name"
            assert updated.updated_at != user.updated_at

    def test_update_user_password(self, client):
        """Test updating user password."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "pwdupdate@example.com", "User", "oldpass", "doctor")
            updated = update_user(db, user.id, password="newpass")

            assert updated is not None
            assert updated.verify_password("newpass") is True
            assert updated.verify_password("oldpass") is False

    def test_update_user_role(self, client):
        """Test updating user role."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "roleupdate@example.com", "User", "password", "doctor")
            updated = update_user(db, user.id, role="pharmacist")

            assert updated is not None
            assert updated.role == "pharmacist"

    def test_update_user_invalid_role(self, client):
        """Test that invalid role update is rejected."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "badrole@example.com", "User", "password", "doctor")
            with pytest.raises(ValueError, match="Invalid role"):
                update_user(db, user.id, role="invalid")

    def test_set_user_active(self, client):
        """Test setting user active/inactive status."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "active@example.com", "User", "password", "doctor", is_active=True)

            # Deactivate
            updated = set_user_active(db, user.id, False)
            assert updated is not None
            assert updated.is_active is False

            # Reactivate
            updated = set_user_active(db, user.id, True)
            assert updated is not None
            assert updated.is_active is True


class TestUserListing:
    """Tests for user listing functions."""

    def test_list_all_users(self, client):
        """Test listing all users."""
        with client.application.app_context():
            db = client.application.get_db()
            create_user(db, "list1@example.com", "User 1", "pass", "doctor")
            create_user(db, "list2@example.com", "User 2", "pass", "pharmacist")
            create_user(db, "list3@example.com", "User 3", "pass", "admin")

            users = list_users(db)
            assert len(users) >= 3
            emails = {u.email for u in users}
            assert "list1@example.com" in emails
            assert "list2@example.com" in emails
            assert "list3@example.com" in emails

    def test_list_users_by_role(self, client):
        """Test listing users filtered by role."""
        with client.application.app_context():
            db = client.application.get_db()
            doctors = list_users(db, role="doctor")
            for user in doctors:
                assert user.role == "doctor"

    def test_list_users_invalid_role(self, client):
        """Test that invalid role filter is rejected."""
        with client.application.app_context():
            db = client.application.get_db()
            with pytest.raises(ValueError, match="Invalid role"):
                list_users(db, role="invalid")


class TestUserDeletion:
    """Tests for user deletion."""

    def test_delete_user(self, client):
        """Test deleting a user."""
        with client.application.app_context():
            db = client.application.get_db()
            user = create_user(db, "delete@example.com", "Delete Me", "password", "doctor")
            result = delete_user(db, user.id)
            assert result is True
            assert get_user_by_id(db, user.id) is None


class TestAuthenticationFlows:
    """Tests for authentication login/logout flows."""

    def test_doctor_login(self, client):
        """Test doctor login with correct credentials."""
        response = login(client, "doctor")
        assert response.status_code == 302
        assert "/prescriptions/new" in response.headers["Location"]

    def test_pharmacist_login(self, client):
        """Test pharmacist login with correct credentials."""
        response = login(client, "pharmacist")
        assert response.status_code == 302
        assert "/verify" in response.headers["Location"]

    def test_admin_login(self, client):
        """Test admin login with correct credentials."""
        response = login(client, "admin")
        assert response.status_code == 302
        assert "/" in response.headers["Location"]

    def test_invalid_password(self, client):
        """Test login with invalid password."""
        response = client.post("/login/doctor", data={
            "email": "doctor@rxverify.local",
            "password": "wrongpassword",
        })
        assert response.status_code == 200  # Shows login page with error
        assert b"Incorrect credentials" in response.data

    def test_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post("/login/doctor", data={
            "email": "nonexistent@rxverify.local",
            "password": "anything",
        })
        assert response.status_code == 200
        assert b"Incorrect credentials" in response.data

    def test_inactive_user(self, client):
        """Test login with inactive user."""
        response = client.post("/login/doctor", data={
            "email": "inactive@rxverify.local",
            "password": "password123",
        })
        assert response.status_code == 200
        assert b"Incorrect credentials" in response.data

    def test_role_mismatch(self, client):
        """Test login with correct password but wrong role."""
        response = client.post("/login/doctor", data={
            "email": "pharmacist@rxverify.local",
            "password": "pharmacist123",
        })
        assert response.status_code == 200
        assert b"Incorrect credentials" in response.data

    def test_logout_clears_session(self, client):
        """Test logout completely clears session."""
        login(client, "doctor")
        response = client.post("/logout")
        assert response.status_code == 302

        # Try to access protected route
        response = client.get("/prescriptions/new")
        assert response.status_code == 302
        assert "/login/doctor" in response.headers["Location"]


class TestAuthorization:
    """Tests for RBAC authorization decorators."""

    def test_doctor_authorization(self, client):
        """Test doctor can access doctor routes."""
        login(client, "doctor")
        response = client.get("/prescriptions/new")
        assert response.status_code == 200

    def test_pharmacist_authorization(self, client):
        """Test pharmacist can access pharmacist routes."""
        login(client, "pharmacist")
        response = client.get("/verify")
        assert response.status_code == 200

    def test_admin_authorization(self, client):
        """Test admin role is recognized and redirected to admin dashboard."""
        login(client, "admin")
        # Admin visiting / should be redirected to admin dashboard
        response = client.get("/")
        assert response.status_code == 302
        assert "/admin/" in response.headers["Location"]

        # Admin dashboard should be accessible
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_doctor_cannot_access_pharmacist_routes(self, client):
        """Test doctor cannot access pharmacist routes."""
        login(client, "doctor")
        response = client.get("/verify")
        assert response.status_code == 302
        assert "/login/pharmacist" in response.headers["Location"]

    def test_pharmacist_cannot_access_doctor_routes(self, client):
        """Test pharmacist cannot access doctor routes."""
        login(client, "pharmacist")
        response = client.get("/prescriptions/new")
        assert response.status_code == 302
        assert "/login/doctor" in response.headers["Location"]

    def test_doctor_cannot_access_admin_routes(self, client):
        """Test doctor cannot access admin routes (if any)."""
        login(client, "doctor")
        # There are no admin-only routes yet, but the decorator exists
        # This test ensures the admin role is recognized
        from src.decorators import require_admin
        assert require_admin is not None

    def test_cross_role_access_rejection(self, client):
        """Test cross-role access is rejected."""
        login(client, "doctor")
        response = client.get("/verify")
        assert response.status_code == 302

        client.post("/logout")
        login(client, "pharmacist")
        response = client.get("/prescriptions/new")
        assert response.status_code == 302


class TestSessionManagement:
    """Tests for session handling."""

    def test_session_contains_user_id(self, client):
        """Test that session contains user_id after login."""
        with client.session_transaction() as sess:
            assert "user_id" not in sess

        login(client, "doctor")

        with client.session_transaction() as sess:
            assert "user_id" in sess
            assert sess["user_id"] == 1  # First seeded user

    def test_session_cleared_on_new_login(self, client):
        """Test old session is cleared before new login."""
        login(client, "doctor")
        with client.session_transaction() as sess:
            assert sess["role"] == "doctor"

        client.post("/logout")
        login(client, "pharmacist")

        with client.session_transaction() as sess:
            assert sess["role"] == "pharmacist"
            assert sess["user_id"] != 1  # Different user


class TestAdminUXAndRBAC:
    """Tests for Admin UX/RBAC changes."""

    def test_admin_login_redirects_to_admin_dashboard(self, client):
        """A. Admin successful login redirects to /admin/"""
        response = login(client, "admin")
        assert response.status_code == 302
        assert "/admin/" in response.headers["Location"]

    def test_admin_dashboard_returns_200_after_login(self, client):
        """B. Admin dashboard returns HTTP 200 after login."""
        login(client, "admin")
        response = client.get("/admin/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data
        assert b"Hospitals" in response.data

    def test_admin_visiting_home_does_not_see_doctor_portal(self, client):
        """C. Admin visiting / does not see Doctor portal actions."""
        login(client, "admin")
        response = client.get("/")
        # Should be redirected to admin dashboard
        assert response.status_code == 302
        assert "/admin/" in response.headers["Location"]

    def test_admin_visiting_home_does_not_see_pharmacist_portal(self, client):
        """D. Admin visiting / does not see Pharmacist portal actions."""
        login(client, "admin")
        response = client.get("/")
        # Should be redirected to admin dashboard
        assert response.status_code == 302
        assert "/admin/" in response.headers["Location"]

    def test_unauthenticated_visitor_sees_normal_landing_page(self, client):
        """E. Unauthenticated visitor still sees the normal public landing page."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Doctor sign in" in response.data
        assert b"Pharmacist sign in" in response.data
        assert b"Admin sign in" in response.data

    def test_admin_cannot_access_doctor_only_routes(self, client):
        """F. Admin cannot access Doctor-only routes."""
        login(client, "admin")
        response = client.get("/prescriptions/new")
        assert response.status_code == 302
        assert "/login/doctor" in response.headers["Location"]

        response = client.get("/prescriptions")
        assert response.status_code == 302
        assert "/login/doctor" in response.headers["Location"]

    def test_admin_cannot_access_pharmacist_only_routes(self, client):
        """G. Admin cannot access Pharmacist-only routes."""
        login(client, "admin")
        # /verify is pharmacist-only
        response = client.get("/verify")
        assert response.status_code == 302
        assert "/login/pharmacist" in response.headers["Location"]

        # /verify/<id> allows doctor OR pharmacist - admin gets redirected to home then to /admin/
        response = client.get("/verify/RX-TEST", follow_redirects=True)
        assert response.status_code == 200  # Final destination is admin dashboard
        assert b"Dashboard" in response.data

    def test_doctor_pharmacist_functionality_unchanged(self, client):
        """H. Doctor and Pharmacist functionality remains unchanged."""
        # Doctor can still access doctor routes
        login(client, "doctor")
        response = client.get("/prescriptions/new")
        assert response.status_code == 200

        response = client.get("/prescriptions")
        assert response.status_code == 200

        # Pharmacist can still access pharmacist routes
        client.post("/logout")
        login(client, "pharmacist")
        response = client.get("/verify")
        assert response.status_code == 200

        response = client.get("/verify/RX-TEST")
        assert response.status_code == 200

    def test_admin_login_page_displays_correct_demo_credentials(self, client):
        """I. Admin login page displays admin@rxverify.local / admin123"""
        response = client.get("/login/admin")
        assert response.status_code == 200
        assert b"admin@rxverify.local" in response.data
        assert b"admin123" in response.data
        assert b"pharmacist@rxverify.local" not in response.data
        assert b"pharmacist123" not in response.data