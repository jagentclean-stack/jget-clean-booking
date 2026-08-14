#!/usr/bin/env python3
"""Modify index.html: two-step booking flow (date -> hourly time slots -> form),
shared bookings.json backend via GitHub Actions workflow dispatch, and
double-booking prevention (re-check before commit)."""
import re

SRC = '/home/ubuntu/booking-repo/index.html'
html = open(SRC, encoding='utf-8').read()

# ---------------------------------------------------------------
# 1. Update step header labels
# ---------------------------------------------------------------
html = html.replace(
    '<span id="step-text-2" class="text-xs font-semibold mt-2 text-gray-500">選擇時間與方案</span>',
    '<span id="step-text-2" class="text-xs font-semibold mt-2 text-gray-500">選擇時間</span>'
)

# ---------------------------------------------------------------
# 2. Replace STEP 1 heading/subtitle
# ---------------------------------------------------------------
html = html.replace(
    '''<p class="text-xs text-tech-accent/80 mt-1">
              ✨ 快來挑選您的專屬特務服務日期～ (週一 ～ 週日開放預約)
            </p>''',
    '''<p class="text-xs text-tech-accent/80 mt-1">
              ✨ 快來挑選你的專屬服務時段～ (週一 ～ 週日開放預約)
            </p>'''.replace('請選擇您方便接受服務的日期', '請選擇您方便接受服務的日期')
)

# ---------------------------------------------------------------
# 3. Replace STEP 1 "next" button text
# ---------------------------------------------------------------
html = html.replace(
    '<span>前往選擇服務時間與方案</span>',
    '<span>下一步：選擇時間</span>'
)

# ---------------------------------------------------------------
# 4. Replace STEP 2 heading/subtitle/date display area
# ---------------------------------------------------------------
html = html.replace(
    '''<span>【選擇時間與方案】</span>
            </h2>
            <p class="text-xs text-tech-accent/80 mt-1">
              請選擇預計的清潔時長方案與偏好的抵達時間
            </p>''',
    '''<span>【選擇服務時間】</span>
            </h2>
            <p class="text-xs text-tech-accent/80 mt-1">
              選擇多個連續時段,更方便安排清潔服務～
            </p>'''
)

html = html.replace(
    '''已選日期：<span id="selected-date-display" class="text-tech-accent font-bold">----/--/--</span>''',
    '''已選日期：<span id="selected-date-display" class="text-tech-accent font-bold">----/--/--</span>
            <span id="selected-date-weekday" class="text-gray-400 ml-2">星期-</span>'''
)

# ---------------------------------------------------------------
# 5. Replace STEP 2 duration label + slot label + hint
# ---------------------------------------------------------------
html = html.replace(
    '<label class="block text-xs font-semibold text-gray-300 mb-2.5">1. 請選擇預約時長方案：</label>',
    '<label class="block text-xs font-semibold text-gray-300 mb-2.5">1. 請選擇預約服務方案：</label>'
)

html = html.replace(
    '''<label class="block text-xs font-semibold text-gray-300 mb-2.5">2. 請選擇人員抵達時間段：</label>''',
    '''<label class="block text-xs font-semibold text-gray-300 mb-2.5">2. 請勾選服務時段(可複選連續時段,再點擊一次可取消):</label>'''
)

# ---------------------------------------------------------------
# 6. Replace STEP 2 navigation button texts
# ---------------------------------------------------------------
html = html.replace(
    '<button id="btn-to-step3" disabled onclick="goToStep(3)" class="px-8 py-3 rounded-xl bg-gray-800 text-gray-500 font-semibold cursor-not-allowed transition-all duration-300 flex items-center space-x-2">\n            <span>進入下一步填寫資料</span>',
    '<button id="btn-to-step3" disabled onclick="goToStep(3)" class="px-8 py-3 rounded-xl bg-gray-800 text-gray-500 font-semibold cursor-not-allowed transition-all duration-300 flex items-center space-x-2">\n            <span>下一步:填寫資料</span>'
)
if '進入下一步填寫資料' in html:
    html = html.replace('<span>進入下一步填寫資料</span>', '<span>下一步:填寫資料</span>')

# ---------------------------------------------------------------
# 7. Add JS BEFORE the existing <script> block: new booking engine
# ---------------------------------------------------------------
BOOKINGS_JS = '''
    // ==========================================
    // SHARED BOOKINGS DATABASE (GitHub Actions backed)
    // ==========================================
    const GITHUB_RAW_URL = "https://raw.githubusercontent.com/jagentclean-stack/jget-clean-booking/main/bookings.json";
    const GITHUB_DISPATCH_URL = "https://api.github.com/repos/jagentclean-stack/jget-clean-booking/actions/workflows/bookings.yml/dispatches";

    let sharedBookings = null;   // {slots:[], blocked:[], records:[]}
    let bookingsFetchTime = 0;   // ms of last fetch
    const BOOKINGS_FRESH_MS = 60000; // consider data fresh for 1 minute

    async function fetchBookings(forceRefresh) {
      const now = Date.now();
      if (!forceRefresh && sharedBookings && (now - bookingsFetchTime) < BOOKINGS_FRESH_MS) {
        return sharedBookings;
      }
      try {
        const resp = await fetch(GITHUB_RAW_URL + "?nocache=" + now, { cache: "no-store" });
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        sharedBookings = await resp.json();
        bookingsFetchTime = now;
        return sharedBookings;
      } catch (err) {
        console.error("讀取預約帳本失敗:", err);
        showToast("暫時無法讀取預約資料,將以本地資料顯示");
        return null;
      }
    }

    // Return booked hour-slots for a date from the shared database
    function getBookedSlotsForDate(dateStr) {
      const booked = [];
      if (sharedBookings && sharedBookings.slots) {
        sharedBookings.slots.forEach(s => {
          if (s.date === dateStr) booked.push(...(s.times || []));
        });
      }
      if (sharedBookings && sharedBookings.records) {
        sharedBookings.records.forEach(r => {
          if (r.date === dateStr) booked.push(...(r.times || []));
        });
      }
      // Fallback: local legacy appointments
      appointments.filter(a => a.date === dateStr).forEach(a => booked.push(a.slot));
      return booked;
    }

    function getDateBlockedForDate(dateStr) {
      const blocked = [];
      if (sharedBookings && sharedBookings.blocked) {
        sharedBookings.blocked.forEach(b => {
          if (b.date === dateStr) blocked.push(...(b.times || []));
        });
      }
      // Legacy local blockedSlots fallback
      blockedSlots.filter(bs => bs.date === dateStr).forEach(bs => blocked.push(bs.slot));
      return blocked;
    }

    // Submit booking record via GitHub Actions workflow dispatch (anonymous)
    async function submitBookingToDatabase(booking) {
      try {
        const resp = await fetch(GITHUB_DISPATCH_URL, {
          method: "POST",
          headers: { "Accept": "application/vnd.github+json" },
          body: JSON.stringify({
            ref: "main",
            inputs: { "booking-json": JSON.stringify(booking) }
          })
        });
        if (!resp.ok) {
          const t = await resp.text();
          throw new Error("HTTP " + resp.status + ": " + t.slice(0, 200));
        }
        return true;
      } catch (err) {
        console.error("寫入預約帳本失敗:", err);
        return false;
      }
    }
'''

html = html.replace(
    '  <script>\n    const LINE_OFFICIAL_URL',
    BOOKINGS_JS + '\n    const LINE_OFFICIAL_URL'
)

# ---------------------------------------------------------------
# 8. Replace JS time-slot constants: hourly slots AM 09-12, PM 13-18
# ---------------------------------------------------------------
html = html.replace(
    "const AM_TIME_SLOTS = ['08:00-08:30', '08:30-09:00', '09:00-09:30', '09:30-10:00', '10:00-10:30', '10:30-11:00'];",
    "const AM_TIME_SLOTS = ['09:00-10:00', '10:00-11:00', '11:00-12:00'];"
)
html = html.replace(
    "const PM_TIME_SLOTS = ['13:00-13:30', '13:30-14:00', '14:00-14:30', '14:30-15:00', '15:00-15:30', '15:30-16:00'];",
    "const PM_TIME_SLOTS = ['13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00'];"
)

# ---------------------------------------------------------------
# 9. Replace selection state: multi-slot array
# ---------------------------------------------------------------
html = html.replace(
    '''    let selectedDateStr = '';
    let selectedDuration = ''; 
    let selectedTimeSlot = ''; 
    let calendarCurrentDate = new Date();''',
    '''    let selectedDateStr = '';
    let selectedDuration = ''; 
    let selectedTimeSlots = [];  // multi-select hourly slots
    let calendarCurrentDate = new Date();'''
)

# ---------------------------------------------------------------
# 10. Replace renderCalendar with shared-data-aware version
# ---------------------------------------------------------------
old_calendar = html[html.find('function renderCalendar()'):html.find('function selectDate(dateStr)')]
new_calendar = '''function renderCalendar() {
      const year = calendarCurrentDate.getFullYear();
      const month = calendarCurrentDate.getMonth();

      document.getElementById('calendar-month-year').innerText = `${year}年 ${month + 1}月`;

      const daysContainer = document.getElementById('calendar-days');
      daysContainer.innerHTML = '';

      const firstDayOfMonth = new Date(year, month, 1).getDay();
      const totalDaysInMonth = new Date(year, month + 1, 0).getDate();

      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

      for (let i = 0; i < firstDayOfMonth; i++) {
        const emptyCell = document.createElement('div');
        emptyCell.className = "h-16 rounded-xl border border-gray-900 bg-tech-dark/20 opacity-30 pointer-events-none";
        daysContainer.appendChild(emptyCell);
      }

      const todayStr = formatDateString(now.getFullYear(), now.getMonth() + 1, now.getDate());

      for (let day = 1; day <= totalDaysInMonth; day++) {
        const currentCellDate = new Date(year, month, day);
        currentCellDate.setHours(0,0,0,0);

        const dateStr = formatDateString(year, month + 1, day);
        const isPast = currentCellDate < today;
        const isToday = (dateStr === todayStr);

        const blockedForDate = getDateBlockedForDate(dateStr);
        const bookedForDate = getBookedSlotsForDate(dateStr);
        const blockedAllDay = blockedForDate.includes('ALL') || blockedForDate.includes('全天');
        const isFullyBooked = !blockedAllDay && (bookedForDate.length >= ALL_TIME_SLOTS.length);
        const isDisabled = isPast || blockedAllDay || isFullyBooked;
        const isSelected = (selectedDateStr === dateStr);

        const dayBtn = document.createElement('button');
        dayBtn.type = 'button';

        let cellClass = "h-16 rounded-xl border flex flex-col justify-between p-2 text-left transition-all relative overflow-hidden ";

        if (isDisabled) {
          cellClass += "bg-gray-900/40 border-gray-800 text-gray-600 cursor-not-allowed opacity-50";
        } else if (isSelected) {
          cellClass += "bg-tech-accent text-black font-bold border-tech-accent shadow-neon-cyan scale-[1.02]";
        } else {
          cellClass += "bg-tech-dark/80 border-gray-800 text-gray-200 hover:border-tech-accent hover:shadow-neon-cyan cursor-pointer";
        }

        dayBtn.className = cellClass;

        let statusBadge = '';
        if (isPast) {
          statusBadge = `<span class="text-[9px] text-gray-600">已過去</span>`;
        } else if (blockedAllDay) {
          statusBadge = `<span class="text-[9px] text-rose-500 font-semibold">已滿</span>`;
        } else if (isFullyBooked) {
          statusBadge = `<span class="text-[9px] text-rose-500 font-semibold">已滿</span>`;
        } else if (isToday) {
          statusBadge = `<span class="text-[9px] font-bold text-amber-400">今天</span>`;
        } else if (isSelected) {
          statusBadge = `<span class="text-[9px] text-black font-extrabold">已選擇</span>`;
        } else {
          statusBadge = `<span class="text-[9px] font-medium text-tech-neon">可預約</span>`;
        }

        if (isToday && !isSelected && !isDisabled) {
          // extra highlight border for today
          dayBtn.className = cellClass.replace("border-gray-800", "border-amber-400/60 border-2");
        }

        dayBtn.innerHTML = `
          <span class="text-sm font-bold">${day}</span>
          <div class="flex justify-between items-center w-full">
            ${statusBadge}
          </div>
        `;

        if (!isDisabled) {
          dayBtn.onclick = () => selectDate(dateStr);
        }

        daysContainer.appendChild(dayBtn);
      }

      const btnToStep2 = document.getElementById('btn-to-step2');
      if (selectedDateStr) {
        btnToStep2.disabled = false;
        btnToStep2.className = "w-full md:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-tech-accent to-tech-glow hover:shadow-neon-cyan text-black font-bold transition-all duration-300 flex items-center justify-center space-x-2 cursor-pointer";
      } else {
        btnToStep2.disabled = true;
        btnToStep2.className = "w-full md:w-auto px-8 py-3 rounded-xl bg-gray-800 text-gray-500 font-semibold cursor-not-allowed transition-all duration-300 flex items-center justify-center space-x-2";
      }
    }
'''
html = html.replace(old_calendar, new_calendar)

# ---------------------------------------------------------------
# 11. Replace selectDate + formatDateString; add ALL_TIME_SLOTS + weekday helper
# ---------------------------------------------------------------
old_select = html[html.find('function selectDate(dateStr)'):html.find('function formatDateString')]
new_select = '''function selectDate(dateStr) {
      selectedDateStr = dateStr;
      selectedTimeSlots = [];
      renderCalendar();
      const d = new Date(dateStr + 'T00:00:00+08:00');
      const wk = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'][d.getDay()];
      showToast(`已選擇預約日期:${dateStr}(${wk})`);
    }
'''
html = html.replace(old_select, new_select)

html = html.replace(
    '''    function formatDateString(year, month, day) {
      const m = month.toString().padStart(2, '0');
      const d = day.toString().padStart(2, '0');
      return `${year}-${m}-${d}`;
    }''',
    '''    function formatDateString(year, month, day) {
      const m = month.toString().padStart(2, '0');
      const d = day.toString().padStart(2, '0');
      return `${year}-${m}-${d}`;
    }

    const ALL_TIME_SLOTS = [].concat(AM_TIME_SLOTS, PM_TIME_SLOTS);

    function getWeekdayLabel(dateStr) {
      const d = new Date(dateStr + 'T00:00:00+08:00');
      return ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'][d.getDay()];
    }

    function isSlotInPast(dateStr, slot) {
      // slot like "09:00-10:00"; compare slot start with now
      const now = new Date();
      const [hh, mm] = slot.split('-')[0].split(':').map(Number);
      const slotTime = new Date(dateStr + 'T00:00:00+08:00');
      slotTime.setHours(hh, mm, 0, 0);
      return slotTime <= now;
    }

    function toggleTimeSlot(slot) {
      const idx = selectedTimeSlots.indexOf(slot);
      if (idx >= 0) {
        selectedTimeSlots.splice(idx, 1);
      } else {
        selectedTimeSlots.push(slot);
        // keep selected slots sorted
        selectedTimeSlots.sort();
      }
      renderTimeSlots();
    }'''
)

# ---------------------------------------------------------------
# 12. Replace goToStep & window.onload to wire data loading
# ---------------------------------------------------------------
old_go = html[html.find('function goToStep(stepNum)'):html.find('function resetToStep1')]
new_go = '''function goToStep(stepNum) {
      if (stepNum === 2 && !selectedDateStr) {
        showToast('請先選擇預約日期!');
        return;
      }
      if (stepNum === 3 && (!selectedDuration || selectedTimeSlots.length === 0)) {
        showToast('請完整選擇服務方案與至少一個時段!');
        return;
      }

      document.getElementById('step-1').classList.add('hidden');
      document.getElementById('step-2').classList.add('hidden');
      document.getElementById('step-3').classList.add('hidden');

      for (let i = 1; i <= 3; i++) {
        const dot = document.getElementById(`step-dot-${i}`);
        const text = document.getElementById(`step-text-${i}`);
        if (i < stepNum) {
          dot.className = "w-10 h-10 rounded-full bg-tech-glow text-white font-bold flex items-center justify-center transition-all duration-300";
          dot.innerHTML = `<i class="fa-solid fa-check"></i>`;
          text.className = "text-xs font-semibold mt-2 text-tech-glow";
        } else if (i === stepNum) {
          dot.className = "w-10 h-10 rounded-full bg-tech-accent text-black font-bold flex items-center justify-center shadow-neon-cyan transition-all duration-300";
          dot.innerText = i;
          text.className = "text-xs font-semibold mt-2 text-tech-accent";
        } else {
          dot.className = "w-10 h-10 rounded-full bg-gray-800 text-gray-400 font-bold border border-gray-700 flex items-center justify-center transition-all duration-300";
          dot.innerText = i;
          text.className = "text-xs font-semibold mt-2 text-gray-500";
        }
      }

      const line = document.getElementById('progress-line');
      if (stepNum === 1) line.style.width = '0%';
      if (stepNum === 2) line.style.width = '50%';
      if (stepNum === 3) line.style.width = '100%';

      document.getElementById(`step-${stepNum}`).classList.remove('hidden');

      if (stepNum === 2) {
        document.getElementById('selected-date-display').innerText = selectedDateStr;
        document.getElementById('selected-date-weekday').innerText = getWeekdayLabel(selectedDateStr);
        renderFrontendDurationOptions();
        renderTimeSlots();
      }

      if (stepNum === 3) {
        document.getElementById('summary-date').innerText = `${selectedDateStr}(${getWeekdayLabel(selectedDateStr)})`;
        document.getElementById('summary-duration').innerText = selectedDuration;
        document.getElementById('summary-slots').innerText = selectedTimeSlots.join('、');
      }
    }
'''
html = html.replace(old_go, new_go)

# ---------------------------------------------------------------
# 13. Replace window.onload to preload bookings
# ---------------------------------------------------------------
html = html.replace(
    '''    window.onload = function() {
      renderCalendar();
      renderFrontendPlansPreview();
      renderFrontendDurationOptions();
    };''',
    '''    window.onload = function() {
      renderFrontendPlansPreview();
      renderFrontendDurationOptions();
      // Preload shared bookings then render calendar
      fetchBookings(true).then(() => { renderCalendar(); });
    };'''
)

# ---------------------------------------------------------------
# 14. Replace renderTimeSlots & renderSlotButtonsGroup with multi-select hourly version
# ---------------------------------------------------------------
old_slots = html[html.find('function renderTimeSlots()'):html.find('function updateStep2ButtonState')]
new_slots = '''function renderTimeSlots() {
      const amGrid = document.getElementById('am-slots-grid');
      const pmGrid = document.getElementById('pm-slots-grid');

      amGrid.innerHTML = '';
      pmGrid.innerHTML = '';

      const bookedForDate = getBookedSlotsForDate(selectedDateStr);
      const blockedForDate = getDateBlockedForDate(selectedDateStr);

      renderSlotButtonsGroup(AM_TIME_SLOTS, amGrid, bookedForDate, blockedForDate);
      renderSlotButtonsGroup(PM_TIME_SLOTS, pmGrid, bookedForDate, blockedForDate);

      updateStep2ButtonState();
    }

    function renderSlotButtonsGroup(slotsArray, container, bookedList, blockedList) {
      slotsArray.forEach(slot => {
        const isBooked = bookedList.includes(slot);
        const isBlocked = blockedList.includes(slot) || blockedList.includes('ALL') || blockedList.includes('全天');
        const isPast = isSlotInPast(selectedDateStr, slot);
        const isDisabled = isBooked || isBlocked || isPast;
        const isSelected = selectedTimeSlots.includes(slot);

        const btn = document.createElement('button');
        btn.type = 'button';

        let btnClass = "py-3 px-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center space-y-1 transition-all duration-200 ";

        if (isDisabled) {
          btnClass += "bg-gray-900/60 border-gray-800 text-gray-600 cursor-not-allowed opacity-60";
        } else if (isSelected) {
          btnClass += "bg-tech-accent text-black border-tech-accent shadow-neon-cyan font-bold scale-[1.02]";
        } else {
          btnClass += "bg-tech-dark/80 border-gray-800 text-gray-200 hover:border-tech-accent hover:text-tech-accent cursor-pointer";
        }

        btn.className = btnClass;

        let statusText = '';
        let statusColor = '';
        if (isBooked) { statusText = '已預約'; statusColor = 'text-gray-600'; }
        else if (isBlocked) { statusText = '已封鎖'; statusColor = 'text-gray-600'; }
        else if (isPast) { statusText = '已過去'; statusColor = 'text-gray-600'; }
        else if (isSelected) { statusText = '已選擇 ✓'; statusColor = 'text-black font-extrabold'; }
        else { statusText = '可預約'; statusColor = 'text-tech-neon'; }

        btn.innerHTML = `
          <span class="text-sm font-bold tracking-wider">${slot}</span>
          <span class="text-[10px] ${statusColor}">${statusText}</span>
        `;

        if (!isDisabled) {
          btn.onclick = () => toggleTimeSlot(slot);
        }

        container.appendChild(btn);
      });
    }
'''
html = html.replace(old_slots, new_slots)

# ---------------------------------------------------------------
# 15. Replace updateStep2ButtonState for multi-select
# ---------------------------------------------------------------
old_btn_state = html[html.find('function updateStep2ButtonState()'):html.find('function updateStep2ButtonState()') + html[html.find('function updateStep2ButtonState()'):].find('}')]
new_btn_state = '''function updateStep2ButtonState() {
      const btnToStep3 = document.getElementById('btn-to-step3');
      if (selectedDuration && selectedTimeSlots.length > 0) {
        btnToStep3.disabled = false;
        btnToStep3.className = "px-8 py-3 rounded-xl bg-gradient-to-r from-tech-accent to-tech-glow hover:shadow-neon-cyan text-black font-bold transition-all duration-300 flex items-center space-x-2 cursor-pointer";
      } else {
        btnToStep3.disabled = true;
        btnToStep3.className = "px-8 py-3 rounded-xl bg-gray-800 text-gray-500 font-semibold cursor-not-allowed transition-all duration-300 flex items-center space-x-2";
      }
    }'''
html = html.replace(old_btn_state, new_btn_state)

# ---------------------------------------------------------------
# 16. Replace handleFormSubmit with conflict-recheck + workflow dispatch
# ---------------------------------------------------------------
old_submit = html[html.find('function handleFormSubmit(event)'):html.find('function copyModalContent')]
new_submit = '''async function handleFormSubmit(event) {
      event.preventDefault();

      const name = document.getElementById('cust-name').value.trim();
      const phone = document.getElementById('cust-phone').value.trim();
      const service = document.getElementById('cust-service').value;
      const address = document.getElementById('cust-address').value.trim();
      const notes = document.getElementById('cust-notes').value.trim();

      if (!name || !phone || !service || !address) {
        showToast('請完整填寫必填欄位!');
        return;
      }

      // -----------------------------------------------
      // 衝突防止機制:送出前再次取得最新帳本檢查
      // -----------------------------------------------
      const btn = event.submitter || document.querySelector('#booking-form button[type="submit"]');
      btn.disabled = true;
      const originalBtnText = btn.querySelector('span') ? btn.querySelector('span').innerText : '';
      if (btn.querySelector('span')) btn.querySelector('span').innerText = '正在確認時段...';

      try {
        const fresh = await fetchBookings(true);
        const chosen = new Set(selectedTimeSlots);
        let conflict = false;
        let conflictDetail = [];
        const sources = [];
        if (fresh && fresh.slots) sources.push(...fresh.slots);
        if (fresh && fresh.records) sources.push(...fresh.records);
        sources.forEach(s => {
          if (s.date === selectedDateStr) {
            const overlap = (s.times || []).filter(t => chosen.has(t));
            if (overlap.length > 0) { conflict = true; conflictDetail.push(`${s.date} ${overlap.join('、')}`); }
          }
        });
        if (conflict) {
          showToast(`很抱歉,您選擇的時段剛剛已被其他客戶預約(${conflictDetail.join(' / ')}),請重新選擇時間。`);
          goToStep(2);
          return;
        }

        // Send to database via GitHub Actions workflow dispatch
        submitBookingToDatabase({
          date: selectedDateStr,
          times: [...selectedTimeSlots],
          name: name,
          phone: phone,
          service: service,
          address: address,
          notes: notes
        }).then(ok => {
          if (!ok) showToast('預約資料已建立,但同步帳本失敗,客服將於 LINE 上與您確認時段。');
        }).catch(() => {});
      } catch (err) {
        console.error('衝突檢查失敗:', err);
        // 檢查失敗仍允許送出? 為安全起見提醒後讓使用者再試一次
        showToast('無法連線確認時段,請確認網路後再試一次');
        if (btn.querySelector('span')) btn.querySelector('span').innerText = originalBtnText;
        btn.disabled = false;
        return;
      }

      if (btn.querySelector('span')) btn.querySelector('span').innerText = originalBtnText;
      btn.disabled = false;

      const newBooking = {
        id: 'JT' + Date.now(),
        date: selectedDateStr,
        duration: selectedDuration,
        slots: [...selectedTimeSlots],
        name: name,
        phone: phone,
        service: service,
        address: address,
        notes: notes,
        createdAt: new Date().toLocaleString()
      };

      // Local legacy fallback record (admin panel still shows it)
      appointments.push({
        id: newBooking.id,
        date: selectedDateStr,
        duration: selectedDuration,
        slot: selectedTimeSlots.join('、'),
        name: name, phone: phone, service: service, address: address, notes: notes,
        createdAt: newBooking.createdAt
      });
      saveState();

      const slotRange = selectedTimeSlots.join('、');

      currentFormattedBookingText = 
`【潔特務清潔公司 - 線上預約單】
-----------------------------
預約日期:${selectedDateStr}(${getWeekdayLabel(selectedDateStr)})
服務方案:${selectedDuration}
服務時段:${slotRange}
客戶姓名:${name}
聯絡電話:${phone}
服務項目:${service}
服務地址:${address}
備註說明:${notes || '無'}
-----------------------------
(請將此內容貼上傳送給潔特務客服團隊,謝謝!)`;

      fallbackCopyText(currentFormattedBookingText);

      document.getElementById('modal-copy-preview').innerText = currentFormattedBookingText;
      document.getElementById('success-modal').classList.remove('hidden');
    }
'''
html = html.replace(old_submit, new_submit)

# ---------------------------------------------------------------
# 17. Fix resetToStep1 for new state + closeSuccessModal (clear stale data)
# ---------------------------------------------------------------
html = html.replace(
    '''    function resetToStep1() {
      selectedDateStr = '';
      selectedDuration = '';
      selectedTimeSlot = '';
      renderCalendar();
      goToStep(1);
    }''',
    '''    function resetToStep1() {
      selectedDateStr = '';
      selectedDuration = '';
      selectedTimeSlots = [];
      renderCalendar();
      goToStep(1);
    }'''
)

open(SRC, 'w', encoding='utf-8').write(html)
print('modify_index.py done')
