"""
Core agent app for the recruitment screening and interview scheduling lab.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from typing import Any

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from prompts import CHATBOT_BASELINE_PROMPT, MAX_ITERATIONS, REACT_SYSTEM_PROMPT
from providers import get_llm_provider
from tools import (
    AVAILABLE_TOOLS,
    JOB_REQUIREMENTS,
    check_interview_slots,
    evaluate_candidate,
    get_job_requirements,
    parse_candidate_profile,
    schedule_interview,
    send_interview_invitation,
)

load_dotenv()

ACTION_PREFIX = "Action:"
FINAL_PREFIX = "Final Answer:"


def load_test_cases():
    """Read test cases from config/test_cases.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def find_test_case(tests: list[dict[str, Any]], case_id: int) -> dict[str, Any] | None:
    """Return the test case whose ``id`` matches ``case_id``, or ``None``."""
    for case in tests:
        if case.get("id") == case_id:
            return case
    return None


def run_baseline_chatbot(user_query: str, provider):
    """Run the plain chatbot path without tools."""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")


def _tool_catalog_text() -> str:
    lines = []
    for name, spec in AVAILABLE_TOOLS.items():
        description = ""
        if name in ("parse_candidate_profile", "get_job_requirements", "evaluate_candidate",
                    "check_interview_slots", "schedule_interview", "send_interview_invitation"):
            description = ""
        lines.append(f"- {name}")
    return "\n".join(lines)


def _build_react_prompt(user_query: str, history: list[dict[str, Any]]) -> str:
    tool_help = [
        "Available tools and the main input each tool expects:",
        "- parse_candidate_profile(profile_text)",
        "- get_job_requirements(job_title)",
        "- evaluate_candidate(candidate_skills, experience_years, job_title)",
        "- check_interview_slots(preferred_date=\"\")",
        "- schedule_interview(candidate_email, job_title, slot, confirmed=False)",
        "- send_interview_invitation(candidate_email, job_title, slot, confirmed=False)",
    ]
    prompt_lines = [
        "User query:",
        user_query,
        "",
        "Tool instructions:",
        *tool_help,
        "",
        "Required output format:",
        'Thought: <short reasoning>',
        'Action: {"tool": "tool_name", "args": {...}}',
        "or",
        "Final Answer: <concise answer>",
        "",
        "Conversation state:",
    ]

    if not history:
        prompt_lines.append("(none yet)")
    else:
        for i, step in enumerate(history, start=1):
            prompt_lines.append(f"Step {i} assistant:")
            prompt_lines.append(step["assistant"].strip())
            prompt_lines.append(f"Step {i} observation:")
            prompt_lines.append(step["observation"].strip())
            prompt_lines.append("")

    return "\n".join(prompt_lines).strip()


def _extract_final_answer(text: str) -> str | None:
    match = re.search(r"Final Answer:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _parse_action_payload(payload: str) -> tuple[str | None, Any]:
    payload = payload.strip()

    if payload.startswith("{"):
        data = json.loads(payload)
        tool_name = data.get("tool") or data.get("name")
        return tool_name, data.get("args", {})

    call_match = re.fullmatch(r"([A-Za-z_][\w]*)\((.*)\)", payload)
    if call_match:
        tool_name = call_match.group(1)
        raw_args = call_match.group(2).strip()
        if not raw_args:
            return tool_name, ()
        args = ast.literal_eval(f"({raw_args},)")
        return tool_name, args

    bracket_match = re.fullmatch(r"([A-Za-z_][\w]*)\[(.*)\]", payload)
    if bracket_match:
        tool_name = bracket_match.group(1)
        raw_args = bracket_match.group(2).strip()
        if not raw_args:
            return tool_name, ()
        args = ast.literal_eval(f"({raw_args},)")
        return tool_name, args

    return None, None


def _extract_action(text: str) -> tuple[str | None, Any]:
    match = re.search(r"Action:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None, None

    payload = match.group(1).strip()
    if payload.startswith("{"):
        try:
            return _parse_action_payload(payload)
        except json.JSONDecodeError:
            return None, None

    first_line = payload.splitlines()[0].strip()
    try:
        return _parse_action_payload(first_line)
    except Exception:
        return None, None


def _format_tool_call(tool_name: str, args: Any) -> str:
    if isinstance(args, dict):
        return json.dumps(args, ensure_ascii=False)
    if isinstance(args, tuple):
        return repr(args)
    if isinstance(args, list):
        return repr(args)
    return repr(args)


def _execute_tool_call(tool_name: str, args: Any) -> str:
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool is None:
        return json.dumps(
            {"status": "error", "message": f"Tool '{tool_name}' không tồn tại."},
            ensure_ascii=False,
        )

    try:
        if isinstance(args, dict):
            return tool(**args)
        if isinstance(args, (tuple, list)):
            return tool(*args)
        if args is None:
            return tool()
        return tool(args)
    except Exception as exc:
        return json.dumps(
            {"status": "error", "message": f"{tool_name} failed: {exc}"},
            ensure_ascii=False,
        )


def _extract_known_job_title(text: str) -> str | None:
    lowered = text.lower()
    for job_title in JOB_REQUIREMENTS:
        if job_title in lowered:
            return job_title
    return None


def _extract_candidate_profile(text: str) -> dict[str, Any]:
    skills_pool = [
        "python",
        "sql",
        "git",
        "excel",
        "power bi",
        "javascript",
        "react",
        "java",
        "docker",
        "machine learning",
        "backend",
    ]
    lowered = text.lower()
    skills = [skill for skill in skills_pool if skill in lowered]
    years_match = re.search(r"(\d+)\s*(?:năm|years?)", lowered)
    return {
        "skills": skills,
        "experience_years": int(years_match.group(1)) if years_match else 0,
    }


def _fallback_action(user_query: str, history: list[dict[str, Any]]) -> tuple[str | None, Any]:
    lowered = user_query.lower()

    if any(key in lowered for key in ["phỏng vấn", "lịch hẹn", "slot", "khung giờ", "interview"]):
        if history:
            return None, None
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_query)
        return "check_interview_slots", {"preferred_date": date_match.group(0) if date_match else ""}

    if any(key in lowered for key in ["đánh giá", "phù hợp", "sàng lọc", "hồ sơ", "cv", "ứng viên"]):
        if history:
            return None, None
        job_title = _extract_known_job_title(user_query)
        profile = _extract_candidate_profile(user_query)
        if job_title and profile["skills"]:
            return "evaluate_candidate", {
                "candidate_skills": profile["skills"],
                "experience_years": profile["experience_years"],
                "job_title": job_title,
            }
        if "hồ sơ" in lowered or "cv" in lowered:
            return "parse_candidate_profile", {"profile_text": user_query}
        if job_title:
            return "get_job_requirements", {"job_title": job_title}

    if any(key in lowered for key in ["mời", "thư mời", "gửi email", "gửi thư"]):
        if history:
            return None, None
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", user_query)
        slot_match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", user_query)
        if email_match and slot_match:
            return "send_interview_invitation", {
                "candidate_email": email_match.group(0),
                "job_title": _extract_known_job_title(user_query) or "candidate",
                "slot": slot_match.group(0),
                "confirmed": False,
            }

    return None, None


def _fallback_final_answer(user_query: str, history: list[dict[str, Any]]) -> str | None:
    if not history:
        return None

    last_observation = history[-1]["observation"]
    last_assistant = history[-1]["assistant"].lower()
    lowered_query = user_query.lower()

    if "check_interview_slots" in last_assistant or "phỏng vấn" in lowered_query:
        try:
            data = json.loads(last_observation)
        except json.JSONDecodeError:
            return None
        slots = data.get("available_slots", [])
        if slots:
            recommended = slots[0]
            if len(slots) > 1:
                return (
                    f"Đã kiểm tra lịch phỏng vấn còn trống. Có thể đề xuất slot {recommended} "
                    f"và vẫn còn các lựa chọn khác như {', '.join(slots[1:])}."
                )
            return f"Đã kiểm tra lịch phỏng vấn còn trống. Slot phù hợp là {recommended}."
        return "Không còn khung giờ phù hợp để sắp xếp phỏng vấn."

    if "evaluate_candidate" in last_assistant:
        try:
            data = json.loads(last_observation)
        except json.JSONDecodeError:
            return None
        score = data.get("score")
        recommendation = data.get("recommendation")
        matched = data.get("matched_skills", [])
        missing = data.get("missing_skills", [])
        return (
            f"Đánh giá sơ bộ hoàn tất: score {score}, khuyến nghị {recommendation}. "
            f"Kỹ năng phù hợp: {matched}. Kỹ năng còn thiếu: {missing}."
        )

    if "parse_candidate_profile" in last_assistant:
        try:
            data = json.loads(last_observation)
        except json.JSONDecodeError:
            return None
        skills = data.get("skills", [])
        experience_years = data.get("experience_years", 0)
        name = data.get("name", "ứng viên")
        return (
            f"Đã trích xuất hồ sơ của {name}: {experience_years} năm kinh nghiệm, "
            f"kỹ năng chính {skills}."
        )

    return None


def iter_react_agent(user_query: str, provider):
    """Run a ReAct loop, yielding structured events for streaming UIs.

    Yields event dicts in order:
        {"type": "query", "text": user_query}
        {"type": "step", "step": N, "max": M}
        {"type": "llm_response", "text": response}
        {"type": "action", "tool": name, "args": <formatted>}
        {"type": "observation", "text": observation}
        {"type": "final_answer", "text": ...}   # terminal
        {"type": "guardrail", "message": ...}    # terminal
        {"type": "error", "message": ...}        # terminal
    """
    yield {"type": "query", "text": user_query}
    history: list[dict[str, Any]] = []

    try:
        for step in range(1, MAX_ITERATIONS + 1):
            yield {"type": "step", "step": step, "max": MAX_ITERATIONS}
            prompt = _build_react_prompt(user_query, history)
            response = provider.generate(prompt, system_prompt=REACT_SYSTEM_PROMPT)
            yield {"type": "llm_response", "text": response}

            final_answer = _extract_final_answer(response)
            if final_answer:
                yield {"type": "final_answer", "text": final_answer}
                return final_answer

            tool_name, args = _extract_action(response)
            if tool_name is None:
                tool_name, args = _fallback_action(user_query, history)

            if tool_name is None:
                fallback_answer = _fallback_final_answer(user_query, history)
                if fallback_answer:
                    yield {"type": "final_answer", "text": fallback_answer}
                    return fallback_answer

                fallback_text = response.strip()
                yield {"type": "final_answer", "text": fallback_text}
                return fallback_text

            yield {
                "type": "action",
                "tool": tool_name,
                "args": _format_tool_call(tool_name, args),
            }
            observation = _execute_tool_call(tool_name, args)
            yield {"type": "observation", "text": observation}
            history.append({"assistant": response, "observation": observation})

        guardrail_msg = (
            f"Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!"
        )
        yield {"type": "guardrail", "message": guardrail_msg}
        return None
    except Exception as exc:
        yield {"type": "error", "message": f"{exc}"}
        return None


def run_react_agent(user_query: str, provider):
    """Run a ReAct loop with tool execution and guardrails (CLI version)."""
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    result = None
    for event in iter_react_agent(user_query, provider):
        etype = event["type"]
        if etype == "query":
            continue
        if etype == "step":
            print(f"\n--- 🔄 Vòng lặp ReAct (Step {event['step']}/{event['max']}) ---")
        elif etype == "llm_response":
            print(event["text"])
        elif etype == "action":
            print(f"🛠️ Action -> {event['tool']}({event['args']})")
        elif etype == "observation":
            print(f"👁️ Observation: {event['text']}")
        elif etype == "final_answer":
            print(f"🏁 Final Answer: {event['text']}")
            result = event["text"]
        elif etype == "guardrail":
            print(f"🛡️ GUARDRAIL TRIGGERED: {event['message']}")
        elif etype == "error":
            print(f"❌ Error: {event['message']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chạy demo Chatbot Baseline vs ReAct Agent cho test case theo id."
    )
    parser.add_argument(
        "--id",
        type=int,
        default=4,
        help="Test case id cần chạy (mặc định: 4). Xem config/test_cases.json.",
    )
    args = parser.parse_args()

    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(
        f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} "
        f"(Model: {model_name})"
    )

    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")

    case = find_test_case(tests, args.id)
    if case is None:
        available_ids = [case_item.get("id") for case_item in tests]
        print(
            f"⚠️ Không tìm thấy test case id={args.id}. "
            f"Các id khả dụng: {available_ids}. Dùng test case mặc định (id=4)."
        )
        case = find_test_case(tests, 4) or (tests[3] if len(tests) > 3 else tests[-1])

    print(f"📌 Đang chạy Test Case id={case.get('id')} | {case.get('category')}")
    sample_query = case["question"]

    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)

    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
