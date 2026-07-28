# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*
Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn
---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `4/5` | Cần suy luận từ CV của ứng viên & job description của nhà tuyển dụng. |
| 🛠️ **Tool Interaction** | `5/5` | Các tool trích xuất text từ CV - convert pdf sang text, tool gửi mail, tool đặt lịch |
| 🔀 **Dynamic Decision** | `4/5` | Multi-step suy luận nội dung CV để match với job description |
| ⏳ **Long Horizon** | `3/5` | Quy trình gồm 2-3 bước xử lý ngắn. |
| **TỔNG ĐIỂM FIT** | **16/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** |

---

## 🔍 2. SO SÁNH PHẢN HỒI (TEST CASE #3)

**Câu hỏi**: *"Ứng viên Minh có 3 năm kinh nghiệm Python, từng làm backend và đang muốn ứng tuyển vị trí Data Engineer. Hãy tóm tắt nhanh hồ sơ và cho biết mức độ phù hợp sơ bộ."*

### 🤖 Chatbot Baseline:
* **Phản hồi**: *"Ứng viên Minh có 3 năm kinh nghiệm Python, từng làm backend và đang muốn ứng tuyển vị trí Data Engineer. Hãy tóm tắt nhanh hồ sơ và cho biết mức độ phù hợp sơ bộ."*
* **Nhận xét**: AI Agent cung cấp câu trả lời rõ ràng có đầy đủ cấu trúc, dễ dàng theo dõi, có gợi ý hành động tuyển dụng.

### 🧠 ReAct Agent:

--- 🔄 Vòng lặp ReAct (Step 1/3) ---
Thought: I need to check the available interview slots first to see what options are available for next week (afternoon, avoiding Monday). I will call check_interview_slots without a specific date to see the list of available slots.
Action: {"tool": "check_interview_slots", "args": {"preferred_date": ""}}
🛠️ Action -> check_interview_slots({"preferred_date": ""})
👁️ Observation: {"status": "success", "available_slots": ["2026-08-03 09:00", "2026-08-03 14:00", "2026-08-04 10:30"], "message": "Đã tìm thấy lịch trống."}

--- 🔄 Vòng lặp ReAct (Step 2/3) ---
Thought: The first check returned slots on Monday (Aug 3) and Tuesday morning (Aug 4). I need to find more slots for next week, preferably in the afternoon and avoiding Monday (Aug 3). Let me query slots for other days of that week, starting with Tuesday, August 4, 2026, or Wednesday, August 5, 2026.
Action: {"tool": "check_interview_slots", "args": {"preferred_date": "2026-08-04"}}
🛠️ Action -> check_interview_slots({"preferred_date": "2026-08-04"})
👁️ Observation: {"status": "success", "available_slots": ["2026-08-04 10:30"], "message": "Đã tìm thấy lịch trống."}

--- 🔄 Vòng lặp ReAct (Step 3/3) ---
Thought: I need to check the available slots for other days of next week to find afternoon slots that are not on Monday (Aug 3). Let me query Wednesday, August 5, 2026.
Action: {"tool": "check_interview_slots", "args": {"preferred_date": "2026-08-05"}}
🛠️ Action -> check_interview_slots({"preferred_date": "2026-08-05"})
👁️ Observation: {"status": "success", "available_slots": [], "message": "Không còn lịch trống vào ngày đã chọn."}
🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa 3 bước. Ngắt lặp an toàn!
* **Nhận xét**: **FAILED TRACE** — Agent không crash và guardrail đã ngắt
  vòng lặp, nhưng chưa đưa ra Final Answer và chưa tìm được hai lịch buổi chiều
  ngoài thứ Hai như yêu cầu.

---

## 🧪 3. FAILED TRACE, ROOT CAUSE VÀ AGENT V2

### 3.1 Failed Trace trước khi nâng cấp

**Failure Mode:** Repeated Action / hết giới hạn vòng lặp.

```text
Step 1: check_interview_slots("")       -> có 3 lịch
Step 2: check_interview_slots("2026-08-04") -> có 1 lịch buổi sáng
Step 3: check_interview_slots("2026-08-05") -> không có lịch
GUARDRAIL TRIGGERED: đạt MAX_ITERATIONS=3
Return: None
```

**Biểu hiện:** Agent tiếp tục tra cứu từng ngày cho đến khi hết budget, không
tổng hợp được câu trả lời cuối và trả về `None`.

### 3.2 Root Cause Analysis

| Failure Mode | Nguyên nhân gốc | Ảnh hưởng | Khắc phục trong Agent V2 |
| :--- | :--- | :--- | :--- |
| Unknown Tool | Parser/executor trước đây chỉ báo tool không tồn tại, chưa cung cấp đầy đủ danh sách tool hợp lệ cho bước recovery. | Model có thể tiếp tục đoán tên tool hoặc bị kẹt. | Observation trả `code="unknown_tool"` và liệt kê toàn bộ tool hợp lệ; prompt yêu cầu sửa tool ở bước kế tiếp. |
| Malformed Args | Parser làm mất nguyên nhân lỗi và chuyển thẳng sang fallback. | Model không biết phải sửa dấu ngoặc, JSON hoặc tham số nào. | Parser V2 trả `code="malformed_action"` cùng cú pháp JSON chuẩn để model tự sửa. |
| Repeated Action | Chỉ có `MAX_ITERATIONS`, chưa so sánh Action và args giữa các bước. | Lãng phí tool call và token trước khi bị ngắt. | Tạo fingerprint từ `tool_name + args`; ngắt ngay khi fingerprint xuất hiện lần hai. |
| Max Iterations | Khi hết vòng, hàm trả `None`. | Người dùng không nhận được hướng dẫn hữu ích. | Trả safe fallback lịch sự, khẳng định không có thao tác chưa xác nhận nào được thực hiện. |

### 3.3 After — Unknown Tool tự phục hồi

Test có chủ đích: model gọi `search_product`, sau đó sửa sang
`get_job_requirements`.

```text
Step 1
Thought: Tôi sẽ thử tool tìm sản phẩm.
Action: {"tool":"search_product","args":{"query":"Python Developer"}}
Observation: {
  "status": "error",
  "code": "unknown_tool",
  "message": "Tool 'search_product' không tồn tại. Tool hợp lệ: ..."
}

Step 2
Thought: Tool trước không tồn tại; tôi sửa sang tool hợp lệ.
Action: {
  "tool": "get_job_requirements",
  "args": {"job_title": "Python Developer"}
}
Observation: {
  "status": "success",
  "required_skills": ["python", "sql", "git"],
  "min_experience_years": 2
}

Step 3
Final Answer: Python Developer yêu cầu Python, SQL, Git và tối thiểu
2 năm kinh nghiệm.
```

**Kết quả:** PASS — lỗi được biến thành Observation, Agent tự sửa đúng tool và
hoàn thành trong `MAX_ITERATIONS`.

### 3.4 After — Malformed Args tự phục hồi

```text
Step 1
Action: get_job_requirements['Python Developer'
Observation: {
  "status": "error",
  "code": "malformed_action",
  "message": "Cú pháp hợp lệ là JSON, tool_name(...) hoặc tool_name[...]."
}

Step 2
Action: {
  "tool": "get_job_requirements",
  "args": {"job_title": "Python Developer"}
}
Observation: {"status": "success", ...}

Step 3
Final Answer: Vị trí yêu cầu Python, SQL, Git và tối thiểu 2 năm kinh nghiệm.
```

**Kết quả:** PASS — parser không crash và hướng dẫn model sửa sang JSON hợp lệ.

### 3.5 After — Repeated Action bị ngắt sớm

```text
Step 1
Action: check_interview_slots({"preferred_date": "2026-08-03"})
Observation: {"status": "success", "available_slots": [...]}

Step 2
Action: check_interview_slots({"preferred_date": "2026-08-03"})
GUARDRAIL: Phát hiện Repeated Action.
Final Answer: Agent đã lặp lại cùng một hành động và tham số.
Vòng lặp được ngắt để bảo đảm an toàn.
```

**Kết quả:** PASS — Agent dừng ở bước 2, sớm hơn giới hạn 3 bước và trả thông
báo lịch sự thay vì `None`.

### 3.6 Checklist Agent V2

- [x] Có Failed Trace và phân tích nguyên nhân gốc.
- [x] Unknown Tool trả danh sách tool hợp lệ và cho phép recovery.
- [x] Malformed Args không làm parser crash.
- [x] Repeated Action bị phát hiện trước khi hết budget.
- [x] Có `MAX_ITERATIONS` và safe fallback.
- [x] Tool có side effect yêu cầu xác nhận ở application layer.

---

## ⚡ 4. TỐI ƯU CHO MODEL ÍT THAM SỐ

Agent V2 không yêu cầu model phải tự xử lý toàn bộ logic. Model chỉ cần chọn
Action gần đúng; parser, validation, recovery, guardrail và phần lớn fallback
được thực thi bằng Python.

### Các tối ưu đã áp dụng

| Tối ưu | Lợi ích với model nhỏ |
| :--- | :--- |
| `SMALL_MODEL_MODE=true` | Dùng system prompt ngắn, ít token và ít luật phải ghi nhớ cùng lúc. |
| Compact history | Chỉ gửi tối đa 2 bước gần nhất thay vì toàn bộ trace. |
| JSON không cần prefix | Chấp nhận cả `Action: {...}`, JSON trần và JSON trong code fence. |
| Tool aliases | Chuẩn hóa các tên gần đúng như `parse_cv`, `check_slots`, `evaluate_cv` sang tên tool thật. |
| Deterministic router | Nếu model không tạo được Action, Python tự chọn tool cho các intent tuyển dụng phổ biến. |
| Deterministic finalizer | Nếu model sai format sau Observation, Python tổng hợp câu trả lời trực tiếp từ JSON của tool. |
| Parser recovery | Trả lỗi cú pháp thành Observation ngắn để model sửa ở bước kế tiếp. |
| Application guardrails | Xác nhận side effect, chống lặp, timeout và kiểm tra bằng chứng không phụ thuộc năng lực model. |
| Recruitment Mock Provider | Chạy demo offline, cố ý dùng alias/JSON trần để kiểm tra đường model nhỏ. |

### Cấu hình

Trong `.env`:

```env
LLM_PROVIDER=mock
SMALL_MODEL_MODE=true
```

Để dùng prompt đầy đủ với model mạnh hơn:

```env
SMALL_MODEL_MODE=false
```

### Nguyên tắc thiết kế

```text
Model nhỏ: nhận diện intent + đề xuất Action gần đúng
Application: chuẩn hóa + kiểm tra + chạy tool + guardrail
Tool: trả dữ liệu JSON deterministic
Application/model: tạo Final Answer có bằng chứng
```

Nhờ đó, lỗi định dạng hoặc suy luận yếu của model không trực tiếp biến thành
thao tác nguy hiểm. Các hành động đặt lịch/gửi thư vẫn phải qua xác nhận độc lập
tại application layer.
