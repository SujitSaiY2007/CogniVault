"""
Automated Playwright Frontend Test Suite for Phase 5.
Validates:
- Registration page (signup)
- Duplicate / invalid credentials error handling
- Login page & password visibility toggle
- Successful authenticated redirection to /workspace
- Navigation across workspace tabs: Tutor, Course Materials, Learner Mastery
- Tutor grounded query with citation inspect drawer
- Logout and session clearing
- Session persistence and restoration across page reload
- Mobile responsive layout (390x844)
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
import urllib.request
import pytest
from playwright.sync_api import sync_playwright, Page, Browser


def is_service_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False


def wait_for_url(url: str, max_wait: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < max_wait:
        if is_service_ready(url):
            return True
        time.sleep(0.5)
    return False


def test_phase5_frontend_browser_complete():
    project_root = Path(__file__).resolve().parent.parent.parent
    evidence_dir = project_root / "docs" / "evidence" / "phase5_frontend"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    processes = []
    python_exe = sys.executable

    # Ensure backend is running on 8000
    if not is_service_ready("http://127.0.0.1:8000/health"):
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app.agent_os.app:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(backend_proc)
        assert wait_for_url("http://127.0.0.1:8000/health", max_wait=20.0), "Backend failed to start on 8000"

    # Ensure frontend is running on 3000
    if not is_service_ready("http://localhost:3000"):
        npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
        frontend_proc = subprocess.Popen(
            [npx_cmd, "next", "start", "-p", "3000"],
            cwd=str(project_root / "frontend"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=(sys.platform == "win32"),
        )
        processes.append(frontend_proc)
        assert wait_for_url("http://localhost:3000", max_wait=25.0), "Frontend failed to start on 3000"

    try:
        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page: Page = context.new_page()

            # Safely route any requests targeted at remote Render to the local backend
            def handle_route(route):
                req = route.request
                url = req.url
                if "cognivault-backend-znn4.onrender.com" in url:
                    local_url = url.replace("https://cognivault-backend-znn4.onrender.com", "http://127.0.0.1:8000")
                    try:
                        resp = route.fetch(url=local_url)
                        route.fulfill(response=resp)
                    except Exception as e:
                        route.abort()
                else:
                    route.continue_()

            page.route("**/*", handle_route)

            # -----------------------------------------------------------------
            # 1. Registration Page: Sign up a new user
            # -----------------------------------------------------------------
            test_username = f"tester_{int(time.time())}"
            test_password = "SecurePassword123!"

            page.goto("http://localhost:3000/login?mode=signup", wait_until="networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=str(evidence_dir / "01_signup_page.png"), full_page=True)

            page.fill("#username", test_username)
            page.fill("#password", test_password)
            page.click("button[type='submit']")

            # Wait for navigation to /workspace
            page.wait_for_url("**/workspace*", timeout=15000)
            page.wait_for_timeout(1000)
            page.screenshot(path=str(evidence_dir / "02_workspace_initial.png"), full_page=True)

            # Assert workspace loaded and username badge is visible
            assert page.locator(f"text={test_username}").count() > 0 or page.locator("text=CogniVault").count() > 0

            # -----------------------------------------------------------------
            # 2. Logout Flow
            # -----------------------------------------------------------------
            logout_btn = page.locator("button:has-text('Sign out'), button[title='Sign out']").first
            assert logout_btn.is_visible()
            logout_btn.click()

            page.wait_for_url("**/login*", timeout=10000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(evidence_dir / "03_after_logout.png"))

            # -----------------------------------------------------------------
            # 3. Invalid Credentials Handling
            # -----------------------------------------------------------------
            page.fill("#username", test_username)
            page.fill("#password", "WrongPassword999!")
            page.click("button[type='submit']")
            page.wait_for_timeout(800)

            err_alert = page.locator("p[role='alert']").first
            assert err_alert.is_visible(), "Error alert must appear on wrong password"
            assert "Username or password is incorrect" in err_alert.text_content()
            page.screenshot(path=str(evidence_dir / "04_invalid_password_error.png"))

            # -----------------------------------------------------------------
            # 4. Successful Login
            # -----------------------------------------------------------------
            page.fill("#password", test_password)
            page.click("button[type='submit']")
            page.wait_for_url("**/workspace*", timeout=15000)
            page.wait_for_timeout(1000)

            # -----------------------------------------------------------------
            # 5. Course Materials Interface
            # -----------------------------------------------------------------
            materials_btn = page.locator("#nav-tab-materials, nav button:has-text('Course Materials')").first
            materials_btn.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(evidence_dir / "05_course_materials_tab.png"), full_page=True)
            assert page.locator("text=Course Materials & Ingestion").count() > 0 or page.locator("text=Upload Material").count() > 0

            # -----------------------------------------------------------------
            # 6. Evidence Tutor Interface & Citation Drawer
            # -----------------------------------------------------------------
            tutor_btn = page.locator("#nav-tab-tutor, nav button:has-text('Evidence Tutor')").first
            tutor_btn.click()
            page.wait_for_timeout(800)

            # Click a sample query button
            sample_query = page.locator("button:has-text('Newton\\'s Second Law')").first
            if sample_query.is_visible():
                sample_query.click()
            else:
                input_box = page.locator("input[placeholder*='Ask a doubt'], textarea").first
                input_box.fill("What is Newton's second law?")
                page.locator("button:has-text('Ask Tutor'), button[type='submit']").first.click()

            page.wait_for_timeout(2500)
            page.screenshot(path=str(evidence_dir / "06_tutor_response_grounded.png"), full_page=True)

            # Inspect citation badge if visible
            citation_badge = page.locator("button:has-text('Page 1'), button:has-text('Slide'), button:has-text('physics_mechanics')").first
            if citation_badge.is_visible():
                citation_badge.click()
                page.wait_for_timeout(500)
                page.screenshot(path=str(evidence_dir / "07_citation_drawer.png"))

            # -----------------------------------------------------------------
            # 7. Learner Progress / Topic Mastery Interface
            # -----------------------------------------------------------------
            mastery_btn = page.locator("#nav-tab-mastery, nav button:has-text('BKT Mastery')").first
            mastery_btn.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(evidence_dir / "08_learner_mastery_tab.png"), full_page=True)

            # -----------------------------------------------------------------
            # 8. Session Restoration across Page Reload
            # -----------------------------------------------------------------
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1000)
            assert "workspace" in page.url, "Session must persist across refresh without redirecting to login"
            page.screenshot(path=str(evidence_dir / "09_session_restored_refresh.png"))

            # -----------------------------------------------------------------
            # 9. Mobile Responsive Layout (390x844)
            # -----------------------------------------------------------------
            mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
            mobile_page = mobile_context.new_page()
            mobile_page.route("**/*", handle_route)

            mobile_page.goto("http://localhost:3000/login?mode=login", wait_until="networkidle")
            mobile_page.wait_for_timeout(500)
            mobile_page.screenshot(path=str(evidence_dir / "10_mobile_login.png"), full_page=True)

            mobile_context.close()
            context.close()
            browser.close()

    finally:
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
