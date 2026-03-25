import re
from playwright.sync_api import Page, expect

# Playwright's to_have_class(str) requires exact class attribute match.
# Use regex for partial class checks (e.g. "filter-btn inactive").
INACTIVE = re.compile(r"inactive")


# ── Initial state ────────────────────────────────────────────────────────────

def test_initial_counter(app_page: Page):
    """Page loads with all 342 occupations visible."""
    expect(app_page.locator("#filterCount")).to_have_text("342 / 342 occupations")


def test_initial_edu_buttons_all_active(app_page: Page):
    """All 8 education toggle buttons start in active state."""
    buttons = app_page.locator("#eduFilters .filter-btn")
    expect(buttons).to_have_count(8)
    for btn in buttons.all():
        expect(btn).not_to_have_class(INACTIVE)


def test_initial_outlook_buttons_all_active(app_page: Page):
    """All 5 outlook toggle buttons start in active state."""
    buttons = app_page.locator("#outlookFilters .filter-btn")
    expect(buttons).to_have_count(5)
    for btn in buttons.all():
        expect(btn).not_to_have_class(INACTIVE)


def test_initial_pay_display(app_page: Page):
    expect(app_page.locator("#payDisplay")).to_have_text("$25K – $250K")


def test_initial_exposure_display(app_page: Page):
    expect(app_page.locator("#exposureDisplay")).to_have_text("0 – 10")


def test_canvas_renders(app_page: Page):
    """Canvas element is present and has non-zero dimensions."""
    canvas = app_page.locator("canvas#canvas")
    expect(canvas).to_be_visible()
    box = canvas.bounding_box()
    assert box["width"] > 0
    assert box["height"] > 0


# ── Education toggles ────────────────────────────────────────────────────────

def test_edu_toggle_deactivates(app_page: Page):
    """Clicking an active edu button marks it inactive."""
    btn = app_page.locator("#eduFilters .filter-btn").first
    btn.click()
    expect(btn).to_have_class(INACTIVE)


def test_edu_toggle_reduces_count(app_page: Page):
    """Deactivating an edu level reduces visible occupation count."""
    app_page.locator("#eduFilters .filter-btn").nth(1).click()  # HS diploma — high employment
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert int(visible.strip()) < 342


def test_edu_toggle_reactivates(app_page: Page):
    """Clicking an inactive button re-activates it and restores count."""
    btn = app_page.locator("#eduFilters .filter-btn").first
    btn.click()
    expect(btn).to_have_class(INACTIVE)
    btn.click()
    expect(btn).not_to_have_class(INACTIVE)
    expect(app_page.locator("#filterCount")).to_have_text("342 / 342 occupations")


def test_edu_at_least_one_enforced(app_page: Page):
    """Cannot deactivate the last remaining edu button."""
    buttons = app_page.locator("#eduFilters .filter-btn").all()
    for btn in buttons[1:]:
        btn.click()
    # Try to deactivate the last one
    buttons[0].click()
    # Button must remain active
    expect(buttons[0]).not_to_have_class(INACTIVE)
    # FILTER_STATE must still have 1 entry (not 0)
    size = app_page.evaluate("() => FILTER_STATE.edu.size")
    assert size == 1


# ── Outlook toggles ──────────────────────────────────────────────────────────

def test_outlook_toggle_deactivates(app_page: Page):
    btn = app_page.locator("#outlookFilters .filter-btn").first
    btn.click()
    expect(btn).to_have_class(INACTIVE)


def test_outlook_toggle_reduces_count(app_page: Page):
    """Deactivating 'Declining' removes declining-outlook occupations."""
    app_page.locator("#outlookFilters .filter-btn").first.click()
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert int(visible.strip()) < 342


def test_outlook_at_least_one_enforced(app_page: Page):
    """Cannot deactivate the last remaining outlook button."""
    buttons = app_page.locator("#outlookFilters .filter-btn").all()
    for btn in buttons[1:]:
        btn.click()
    buttons[0].click()
    expect(buttons[0]).not_to_have_class(INACTIVE)
    size = app_page.evaluate("() => FILTER_STATE.outlook.size")
    assert size == 1


# ── Sliders (JS injection — drag simulation is brittle) ──────────────────────

def test_pay_slider_reduces_count(app_page: Page):
    """Narrowing pay range reduces occupation count."""
    app_page.evaluate("""() => {
        FILTER_STATE.pay.min = 80000;
        FILTER_STATE.pay.max = 120000;
        applyFilters();
    }""")
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert 0 < int(visible.strip()) < 342


def test_pay_slider_extreme_narrow(app_page: Page):
    """Very narrow pay range returns a valid (non-crashing) result."""
    app_page.evaluate("""() => {
        FILTER_STATE.pay.min = 95000;
        FILTER_STATE.pay.max = 105000;
        applyFilters();
    }""")
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert int(visible.strip()) >= 0


def test_exposure_slider_reduces_count(app_page: Page):
    """Narrowing exposure to high end (7–10) reduces occupation count."""
    app_page.evaluate("""() => {
        FILTER_STATE.exposure.min = 7;
        FILTER_STATE.exposure.max = 10;
        applyFilters();
    }""")
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert 0 < int(visible.strip()) < 342


def test_exposure_slider_low_end(app_page: Page):
    """Narrowing exposure to low end (0–3) filters out high-exposure occupations."""
    app_page.evaluate("""() => {
        FILTER_STATE.exposure.min = 0;
        FILTER_STATE.exposure.max = 3;
        applyFilters();
    }""")
    visible, _ = app_page.locator("#filterCount").inner_text().split(" / ")
    assert int(visible.strip()) < 342


# ── Combined filters + reset ─────────────────────────────────────────────────

def test_combined_filters_are_additive(app_page: Page):
    """Two filters combined yields <= results of either alone."""
    app_page.locator("#eduFilters .filter-btn").nth(0).click()
    edu_only_count = int(app_page.locator("#filterCount").inner_text().split(" / ")[0].strip())

    app_page.locator("#outlookFilters .filter-btn").nth(0).click()
    combined_count = int(app_page.locator("#filterCount").inner_text().split(" / ")[0].strip())

    assert combined_count <= edu_only_count


def test_reset_restores_full_count(app_page: Page):
    """Reset button restores 342 / 342 after filters are applied."""
    app_page.locator("#eduFilters .filter-btn").nth(0).click()
    app_page.locator("#outlookFilters .filter-btn").nth(0).click()
    app_page.evaluate("""() => {
        FILTER_STATE.pay.min = 50000;
        FILTER_STATE.pay.max = 100000;
        applyFilters();
    }""")
    assert "342 / 342" not in app_page.locator("#filterCount").inner_text()

    app_page.locator("#resetFilters").click()
    expect(app_page.locator("#filterCount")).to_have_text("342 / 342 occupations")


def test_reset_reactivates_all_buttons(app_page: Page):
    """After reset, all toggle buttons are active again."""
    app_page.locator("#eduFilters .filter-btn").nth(0).click()
    app_page.locator("#outlookFilters .filter-btn").nth(0).click()
    app_page.locator("#resetFilters").click()

    for btn in app_page.locator("#eduFilters .filter-btn").all():
        expect(btn).not_to_have_class(INACTIVE)
    for btn in app_page.locator("#outlookFilters .filter-btn").all():
        expect(btn).not_to_have_class(INACTIVE)


# ── Color mode compatibility ──────────────────────────────────────────────────

def test_color_mode_switch_after_filter(app_page: Page):
    """Switching color mode after filtering keeps the count unchanged."""
    app_page.locator("#eduFilters .filter-btn").nth(0).click()
    filtered_count_text = app_page.locator("#filterCount").inner_text()

    for mode in ["pay", "education", "exposure", "outlook"]:
        app_page.locator(f"#colorToggle button[data-mode='{mode}']").click()
        expect(app_page.locator("#filterCount")).to_have_text(filtered_count_text)
        expect(app_page.locator("canvas#canvas")).to_be_visible()


def test_stats_total_jobs_reflects_filter(app_page: Page):
    """Total jobs stat decreases when filtered to a single education level."""
    initial_m = float(app_page.locator("#statTotalJobs").inner_text().replace("M", ""))

    # Keep only Bachelor's degree (index 5), deactivate the rest
    buttons = app_page.locator("#eduFilters .filter-btn").all()
    for i, btn in enumerate(buttons):
        if i != 5:
            btn.click()

    filtered_m = float(app_page.locator("#statTotalJobs").inner_text().replace("M", ""))
    assert filtered_m < initial_m
