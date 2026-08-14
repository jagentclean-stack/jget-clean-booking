# 任務筆記(內部用)

## 背景
- 使用者 GitHub 帳號: jagentclean-stack(個人帳號,免費方案,public repo 才有 Pages)
- 儲存庫: https://github.com/jagentclean-stack/jget-clean-booking
- GitHub Pages URL: https://jagentclean-stack.github.io/jget-clean-booking/ (已啟用,legacy mode, main branch, HTTP 200 OK)
- gh CLI 可用(token ghu_ 經 Manus proxy,有 contents:read/write 權限,無 pages 權限;gh api 經 proxy 正常)
- Pages 啟用是用瀏覽器登入 GitHub 後手動在 Settings → Pages 完成

## 目前任務:改版預約系統
使用者要求(兩步驟流程):
1. Step 1 選擇預約日期:週一到週日、可切換月份、過去不可選、已無時段顯示「已滿」灰字、今天明確標示;日曆依後台預約資料自動判斷;提示「快來挑選你的專屬服務時段～」;按鈕「下一步:選擇時間」
2. Step 2 選擇服務時間:顯示已選日期;上午 09:00-12:00、下午 13:00-18:00,切成 1 小時單位(09-10,10-11,11-12,13-14,14-15,15-16,16-17,17-18);可多選連續時段、已預約不可點、過去時間不可點、顯示「已預約/可預約」、可取消;提示「選擇多個連續時段,更方便安排清潔服務～」;按鈕「下一步:填寫資料」
3. Step 3 填寫資料(既有表單保留:姓名、電話、服務項目、地址、備註;LINE 連結 https://lin.ee/TBAzd3A)
4. 衝突防止(Double Booking 防護):送出時再次檢查資料庫,若已被搶訂顯示「很抱歉,您選擇的時段剛剛已被其他客戶預約,請重新選擇時間。」

## 已確認可行的架構(重要!)
- 前端 fetch 讀取 https://raw.githubusercontent.com/jagentclean-stack/jget-clean-booking/main/bookings.json (匿名可讀,加 cache-bust 參數)
- 寫入:前端 fetch POST https://api.github.com/repos/jagentclean-stack/jget-clean-booking/actions/workflows/bookings.yml/dispatches body: {"ref":"main","inputs":{"booking-json": "...JSON string..."}} (匿名權限上允許,HTTP 403 訊息為 IP rate limit 60/hr,非 401)
- workflow: .github/workflows/bookings.yml (已測試成功:dispatch → python 合併 bookings.json → git commit push,含 workflow 內衝突再檢查,exit code 2 時印 CONFLICT)
- workflow 失敗情形:ghu token(非 repo 自有)觸發時 GITHUB_TOKEN 無 push 權限(已改 push 成功? 第二次加 permissions: contents: write 後 success)
- 衝突檢查雙層:前端送出前 fetch 最新 bookings.json + workflow 內再次檢查

## bookings.json 結構(已推至 main, 當前乾淨狀態)
```json
{"version":1,"slots":[],"blocked":[],"records":[]}
```
- slots: 每筆 {date, times[]} 已預約時段(用於日曆顯示已滿)
- blocked: {date, times:["ALL"|"09:00-10:00"...]} 管理者封鎖
- records: 完整預約單 {date, times[], name, phone, service, address, notes, createdAt}

## 原 index.html(在 /home/ubuntu/booking-repo/index.html,66880 bytes,1448 行)
- Tailwind CDN + FontAwesome,深色科技風(tech-accent #06b6d4 cyan)
- 原流程:Step1 日曆(30 分鐘單位時段 AM 08:00-11:00 PM 13:00-16:00)、Step2 選時長方案+抵達時間(單選)、Step3 表單+LINE
- 狀態:localStorage (JT_CONFIG, JT_APPOINTMENTS, JT_BLOCKED_SLOTS, JT_PLANS_V3)
- 預設管理密碼:clean123;LINE: https://lin.ee/TBAzd3A
- 原時長方案(4個):兩人半天3.5小時($4200)、兩人一天7小時($8000)、現場評估、新屋入住優惠
- 成功 modal:複製預約單 + 開啟 LINE
- 管理後台 modal:紀錄/方案 CRUD/封鎖時段/改密碼

## 改寫策略
- 保留原有風格/品牌/管理後台
- Step1 改:日曆依 bookings.json 判斷:過去灰不可選、today 明確標示、slots 全滿或 blocked ALL 顯示「已滿」、其餘可點、選擇高亮;按鈕「下一步:選擇時間」
- Step2 改:保留方案選擇(單選) + 時段格 8 個(1 小時單位),多選(可取消),連續選取支援,過去時段不可選,依 slots+blocked 標「已預約/已封鎖/可預約」;按鈕「下一步:填寫資料」
- Step3:送出時 fetch 最新 bookings.json 再檢查 → CONFLICT 提示 → 否則 fetch POST dispatch workflow → 成功 modal(複製+LINE)
- 注意:dispatch 匿名可能被 rate limit → 失敗時 fallback:複製預約單 + 前往 LINE

## 部署流程
- index.html 改完 → git add/commit/push main → GitHub Actions 自動 pages build → 驗證 URL

## 進度更新(2026-08-14)
- modify_index.py 已完成 index.html 修改(JS 語法檢查中發現問題)
- JS 語法檢查方法: node new Function(slice 578..1605)
- 目前錯誤: slice(0,11) OK、slice(0,12) FAIL "Unexpected token ')'" → 第 12 行(all idx 11,即 HTML line 590)有問題
- 原因疑似: BOOKINGS_JS 注入後 `fetchBookings` 附近某行;需查看 line 586-592

## 進度更新 2
- JS 全檔語法 OK(node new Function slice 578..1604)
- 執行時錯誤: PAGEERROR "ALL_TIME_SLOTS is not defined" 發生於 renderCalendar → 因為 ALL_TIME_SLOTS 常數定義在 formatDateString 之後,但 renderCalendar 由 window.onload 的 fetchBookings 完成後呼叫,執行順序上應 OK…實際是:renderCalendar 呼叫時 ALL_TIME_SLOTS 已在 parse 階段 hoisting? const 不 hoisting,但 script 是整體解析後執行,宣告在前(ALL_TIME_SLOTS 位於 selectDate 之後)——無妨,執行時已定義。真正原因可能是舊版 renderCalendar 未被完全替換,存在第二份。檢查:grep "function renderCalendar" 數量;另外 local server 的 bookings.json 被測試寫入過,確認內容。

## 測試發現(2026-08-14 輪次2)
日曆渲染正常(37 格、今天標示、已過去)。發現問題:1) 點擊日期後 step2 顯示的日期是 2026-08-14 而非所選的 08-15,懷疑 selectDate 用 new Date(dateStr+'T00:00:00+08:00') 在測試環境時區問題,且 renderCalendar 裡 select 高亮未保留或 selectedDateStr 設定時被重繪?實際:測試腳本點第一個可點按鈕(可能點到 08-14「今天」,但今天顯示「今天」非「已過去」,而日曆文本中「14 今天」在列。selectedDateStr 是 08-15 卻顯示 08-14 → selectDate 裡可能 formatDateString 與 todayStr 對齊問題;或點擊的按鈕是「今天」(enabled)而非 08-15。2) AM 時段顯示「已過去」,因為測試時間 12:00+ (sandbox 是 UTC+8 下午?)。sandbox 時間可能 >11:00,所以 09-12 都過去。3) 10:00-11:00 disabled=False 但預設應被 prebooked 佔用——因為 AM 時段顯示已過去,isPast 在 isBooked 之後判斷(isPast=true 時仍可點?isDisabled=isBooked||isBlocked||isPast,順序上 isBooked 先,但若 isBooked 檢查失敗則錯)。booked 檢查用 getBookedSlotsForDate 從 sharedBookings 讀——日曆有 37 格表示 fetchBookings 成功(預設檔 slots 為空)。測試檔 bookings.json 有預佔 08-15 10:00-11:00 但 local server 用本地檔,fetch 的是 local? No,fetch 是 raw.githubusercontent(main) → 線上檔是乾淨的,所以 10:00-11:00 沒被佔用,disabled=False 正確。3) plan buttons 內文空白(按鈕用 plan-btn 類別但 innerText 取第 0 行空白)無妨。4) btn-to-step3 disabled=True 因時段都被標為已過去(測試時段問題,真正常)。結論:核心邏輯正確,需用未來時段測試。

## 測試發現(2026-08-14 輪次3)
所有核心流程 PASS(step2 日期、時段選取/取消、多選、方案、step3 摘要、成功 modal、預約單內容)。唯一 FAIL:booked_disabled(10:00-11:00 在已推 prebook 後仍顯示「可預約」)。原因:前端 fetch 的 raw.githubusercontent 有快取/CDN 延遲(push 後需數秒~分鐘才更新),或 getBookedSlotsForDate 的讀取邏輯問題。需查:fetchBookings 的 resp 是否真的取到新檔。若只是 CDN 快取,等 1-2 分鐘重跑即 PASS。

## 偵錯發現(2026-08-14 輪次4)
raw.githubusercontent.com 有強 CDN 快取(nocache 參數無效,cache-bust 無法繞過),push 後前端仍抓舊檔數分鐘 → 日曆/時段顯示會與實際不符!
解決方案:改用 GitHub REST API 的 anonymous 端點 GET /repos/{owner}/{repo}/contents/bookings.json(匿名讀取,HTTP 200,無 token 也可以,回傳 base64 content),或直接改用 objects API。測試 anonymous contents API 是否可行,若可則切換 fetchBookings 目標 URL。
另一備案:改用 GitHub 的 `media.githubusercontent.com` 或 gists。
測試後:匿名 GET https://api.github.com/repos/jagentclean-stack/jget-clean-booking/contents/bookings.json → 檢查是否 200 且即時。

## 測試結果(2026-08-14 輪次5,全部 PASS)
step2 日期/已預約 disabled/選取/取消/多選/方案/step3 摘要/成功 modal/預約單內容全部 PASS。注意:contents API 為即時,本地 revert 後線上仍是預佔版,需 git push 撤除。衝突檢查邏輯在 1120-1160 行(fetch fresh → 檢查 overlap → showToast 並 return 到 step 2),submitBookingToDatabase 為 dispatch workflow。剩餘:1) 推最終版到 main 2) 確認 Pages 部署 3) 視覺抽查線上的 step1 日曆 4) 清除測試用 revert。
