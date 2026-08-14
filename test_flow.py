#!/usr/bin/env python3
"""Test the two-step booking flow on the local server."""
import json, time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8899/index.html'

# Prepare: book 10:00-11:00 on a FUTURE date (day after tomorrow) to avoid past-slot issues
target = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
prebooked = {
    'version': 1,
    'slots': [{'date': target, 'times': ['10:00-11:00']}],
    'blocked': [],
    'records': []
}
with open('/home/ubuntu/booking-repo/bookings.json', 'w') as f:
    json.dump(prebooked, f, ensure_ascii=False, indent=2)
print('target date:', target)

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(BASE)
    page.wait_for_timeout(3000)

    # 1. Calendar: find the target day cell (clickable, enabled)
    def get_day_buttons():
        return page.query_selector_all('#calendar-days button')

    btns = get_day_buttons()
    target_btn = None
    for btn in btns:
        txt = btn.inner_text()
        day_num = int(txt.split('\n')[0].strip())
        # find correct month: compare button label against target date
        if not btn.is_enabled():
            continue
        # candidate: enabled cell whose date string equals target
        # reconstruct: we'll just match by checking onclick-free approach; instead evaluate dateStr on click
        pass
    # Better: click each enabled cell, check selected-date-display after? Too slow.
    # Instead compute: calendar shows current month; target is day after tomorrow = same month likely.
    target_day = int(target.split('-')[2])
    for btn in btns:
        if btn.is_enabled() and btn.inner_text().split('\n')[0].strip() == str(target_day):
            target_btn = btn
            break
    assert target_btn, 'target day cell not found'
    target_btn.click()
    page.wait_for_timeout(800)

    page.click('#btn-to-step2')
    page.wait_for_timeout(1200)
    d = page.inner_text('#selected-date-display')
    w = page.inner_text('#selected-date-weekday')
    print('step2 date:', d, w)
    results.append(('step2_date', d == target))

    # 3. Slots: 10:00-11:00 should show 已預約 and be disabled; 09:00-10:00 available
    am = page.query_selector_all('#am-slots-grid button')
    # Check booked slot via fresh locator
    booked_el = page.query_selector('#am-slots-grid button:has-text("10:00-11:00")')
    print('10:00-11:00 ->', booked_el.inner_text().replace('\n', ' '), '| disabled =', booked_el.is_disabled())
    results.append(('booked_disabled', booked_el.is_disabled()))

    for s in am:
        t = s.inner_text()
        if '10:00-11:00' in t:
            continue
        if '09:00-10:00' in t:
            print('09:00-10:00 ->', t.replace('\n', ' '))
            # click via selector (DOM re-renders after each toggle)
            page.click('#am-slots-grid button:has-text("09:00-10:00")')
            page.wait_for_timeout(600)
            sel = page.inner_text('#am-slots-grid button:has-text("09:00-10:00")')
            print('after click 09:00-10:00 ->', sel.replace('\n', ' '))
            results.append(('select_slot', '已選擇' in sel))
            page.click('#am-slots-grid button:has-text("09:00-10:00")')
            page.wait_for_timeout(600)
            print('after toggle off ->', page.inner_text('#am-slots-grid button:has-text("09:00-10:00")').replace('\n', ' '))
            results.append(('toggle_off', '可預約' in page.inner_text('#am-slots-grid button:has-text("09:00-10:00")')))
            page.click('#am-slots-grid button:has-text("09:00-10:00")')
            page.wait_for_timeout(600)

    pm = page.query_selector_all('#pm-slots-grid button')
    for s in pm:
        if '14:00-15:00' in s.inner_text():
            page.click('#pm-slots-grid button:has-text("14:00-15:00")')
            page.wait_for_timeout(600)
            print('14:00-15:00 selected ->', page.inner_text('#pm-slots-grid button:has-text("14:00-15:00")').replace('\n', ' '))
            results.append(('multi_select', '已選擇' in page.inner_text('#pm-slots-grid button:has-text("14:00-15:00")')))
            break

    # 4. Pick plan
    plans = page.query_selector_all('#duration-options-grid button')
    plans[1].click()
    page.wait_for_timeout(500)
    print('plan selected:', plans[1].inner_text().strip()[:30])
    results.append(('plan_clicked', True))

    btn3 = page.query_selector('#btn-to-step3')
    print('btn-to-step3 disabled:', btn3.is_disabled())
    if btn3.is_disabled():
        results.append(('step2_button', False))
        print('ERROR: cannot advance; abort')
        browser.close()
        print(results)
        raise SystemExit(1)
    btn3.click()
    page.wait_for_timeout(1000)
    print('step3 summary:', page.inner_text('#summary-date'), '|', page.inner_text('#summary-slots'))
    results.append(('step3_summary', '09:00-10:00' in page.inner_text('#summary-slots') and '14:00-15:00' in page.inner_text('#summary-slots')))

    # 5. Fill form & submit
    page.fill('#cust-name', '測試客戶')
    page.fill('#cust-phone', '0912345678')
    page.select_option('#cust-service', '居家定期清潔')
    page.fill('#cust-address', '台北市測試路1號')
    page.wait_for_timeout(400)

    page.click('#booking-form button[type="submit"]')
    page.wait_for_timeout(4000)
    modal_visible = not page.is_hidden('#success-modal')
    print('success modal visible:', modal_visible)
    results.append(('success_modal', modal_visible))
    preview = page.inner_text('#modal-copy-preview')
    print('preview:', preview[:120].replace('\n', ' / '))
    results.append(('preview_has_multi_slots', '09:00-10:00' in preview and '14:00-15:00' in preview))

    browser.close()

ok = all(r[1] for r in results)
print('\nRESULTS:')
for name, passed in results:
    print(('PASS' if passed else 'FAIL'), name)
print('ALL PASSED' if ok else 'SOME FAILED')
raise SystemExit(0 if ok else 2)
