"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.
"""

import json
import re
from datetime import datetime


# Dữ liệu mô phỏng để các tool chạy ổn định, không cần API hoặc Internet.
JOB_REQUIREMENTS = {
    "python developer": {
        "required_skills": ["python", "sql", "git"],
        "min_experience_years": 2,
    },
    "data analyst": {
        "required_skills": ["sql", "excel", "power bi"],
        "min_experience_years": 1,
    },
    "data engineer": {
        "required_skills": ["python", "sql", "docker"],
        "min_experience_years": 2,
    },
    "frontend developer": {
        "required_skills": ["javascript", "react", "git"],
        "min_experience_years": 2,
    },
}

INTERVIEW_SLOTS = [
    "2026-08-03 09:00",
    "2026-08-03 14:00",
    "2026-08-04 10:30",
]

# MÔ TẢ TOOL (TOOL SPECS)
# Agent dùng thông tin này để biết khi nào gọi tool, truyền tham số gì
# và kết quả/lỗi nào có thể được trả về.
TOOL_SPECS = {
    "parse_candidate_profile": {
        "description": (
            "Trích xuất tên, email, kỹ năng và số năm kinh nghiệm "
            "từ CV dạng văn bản."
        ),
        "input_schema": {
            "profile_text": {
                "type": "string",
                "required": True,
                "description": "Nội dung CV của ứng viên.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": [
                "status",
                "name",
                "email",
                "skills",
                "experience_years",
            ],
        },
        "error_semantics": "Trả status='error' nếu hồ sơ rỗng.",
        "side_effect": False,
    },
    "get_job_requirements": {
        "description": (
            "Tra cứu kỹ năng và số năm kinh nghiệm tối thiểu "
            "của một vị trí tuyển dụng."
        ),
        "input_schema": {
            "job_title": {
                "type": "string",
                "required": True,
                "description": "Tên vị trí cần tra cứu.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": [
                "status",
                "job_title",
                "required_skills",
                "min_experience_years",
            ],
        },
        "error_semantics": (
            "Trả status='error' nếu tên vị trí rỗng hoặc không tồn tại."
        ),
        "side_effect": False,
    },
    "evaluate_candidate": {
        "description": (
            "Đối chiếu kỹ năng, kinh nghiệm của ứng viên với yêu cầu "
            "công việc và đưa ra điểm phù hợp."
        ),
        "input_schema": {
            "candidate_skills": {
                "type": "array[string]",
                "required": True,
                "description": "Danh sách kỹ năng của ứng viên.",
            },
            "experience_years": {
                "type": "integer",
                "minimum": 0,
                "required": True,
                "description": "Số năm kinh nghiệm.",
            },
            "job_title": {
                "type": "string",
                "required": True,
                "description": "Vị trí cần đánh giá.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": [
                "status",
                "score",
                "matched_skills",
                "missing_skills",
                "experience",
                "recommendation",
            ],
        },
        "error_semantics": (
            "Trả status='error' khi sai kiểu dữ liệu, kinh nghiệm âm "
            "hoặc vị trí không tồn tại."
        ),
        "side_effect": False,
    },
    "check_interview_slots": {
        "description": "Tra cứu các khung giờ phỏng vấn còn trống.",
        "input_schema": {
            "preferred_date": {
                "type": "string",
                "format": "YYYY-MM-DD",
                "required": False,
                "description": "Ngày muốn phỏng vấn; để trống để xem tất cả.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": ["status", "available_slots", "message"],
        },
        "error_semantics": (
            "Trả status='error' nếu ngày không đúng định dạng YYYY-MM-DD."
        ),
        "side_effect": False,
    },
    "schedule_interview": {
        "description": (
            "Đặt lịch phỏng vấn vào một khung giờ còn trống. "
            "Chỉ gọi sau khi người dùng xác nhận."
        ),
        "input_schema": {
            "candidate_email": {
                "type": "string",
                "format": "email",
                "required": True,
            },
            "job_title": {
                "type": "string",
                "required": True,
            },
            "slot": {
                "type": "string",
                "format": "YYYY-MM-DD HH:MM",
                "required": True,
            },
            "confirmed": {
                "type": "boolean",
                "required": True,
                "description": "Phải là true sau xác nhận của người dùng.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": [
                "status",
                "candidate_email",
                "job_title",
                "slot",
                "message",
            ],
        },
        "error_semantics": (
            "Trả confirmation_required nếu chưa xác nhận; trả error "
            "nếu email sai hoặc lịch không còn trống."
        ),
        "side_effect": True,
    },
    "send_interview_invitation": {
        "description": (
            "Tạo và mô phỏng gửi thư mời phỏng vấn. "
            "Chỉ gọi sau khi người dùng xác nhận."
        ),
        "input_schema": {
            "candidate_email": {
                "type": "string",
                "format": "email",
                "required": True,
            },
            "job_title": {
                "type": "string",
                "required": True,
            },
            "slot": {
                "type": "string",
                "format": "YYYY-MM-DD HH:MM",
                "required": True,
            },
            "confirmed": {
                "type": "boolean",
                "required": True,
                "description": "Phải là true sau xác nhận của người dùng.",
            },
        },
        "output_schema": {
            "type": "json_string",
            "fields": [
                "status",
                "recipient",
                "subject",
                "body",
                "message",
            ],
        },
        "error_semantics": (
            "Trả confirmation_required nếu chưa xác nhận; "
            "trả error nếu email không hợp lệ."
        ),
        "side_effect": True,
    },
}


def _json_result(data: dict) -> str:
    """Chuyển kết quả tool thành JSON để Agent dễ đọc."""
    return json.dumps(data, ensure_ascii=False)


def _is_valid_email(value: object) -> bool:
    """Kiểm tra email mà không phát sinh lỗi khi đầu vào sai kiểu."""
    return (
        isinstance(value, str)
        and re.fullmatch(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value) is not None
    )


def _is_valid_datetime(value: object, date_only: bool = False) -> bool:
    """Kiểm tra ngày/giờ đúng định dạng và tồn tại trên lịch."""
    if not isinstance(value, str):
        return False
    date_format = "%Y-%m-%d" if date_only else "%Y-%m-%d %H:%M"
    try:
        datetime.strptime(value, date_format)
        return True
    except ValueError:
        return False


def parse_candidate_profile(profile_text: str) -> str:
    """
    Trích xuất tên, email, kỹ năng và kinh nghiệm từ nội dung CV.

    Args:
        profile_text (str): Nội dung CV dạng văn bản.

    Returns:
        str: JSON chứa thông tin hồ sơ hoặc thông báo lỗi.

    Side effect:
        Không có.
    """
    if not isinstance(profile_text, str) or not profile_text.strip():
        return _json_result({
            "status": "error",
            "message": "Nội dung hồ sơ không được để trống.",
        })

    text = profile_text.strip()
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    experience_match = re.search(
        r"(\d+)\s*(?:năm|years?)",
        text,
        re.IGNORECASE,
    )
    name_match = re.search(
        r"(?:họ tên|tên|name)\s*:\s*([^\n,;]+)",
        text,
        re.IGNORECASE,
    )
    known_skills = [
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
    ]
    skills = [skill for skill in known_skills if skill in text.lower()]

    return _json_result({
        "status": "success",
        "name": name_match.group(1).strip() if name_match else "Không xác định",
        "email": email_match.group(0) if email_match else None,
        "skills": skills,
        "experience_years": (
            int(experience_match.group(1)) if experience_match else 0
        ),
    })


def get_job_requirements(job_title: str) -> str:
    """
    Tra cứu yêu cầu kỹ năng và kinh nghiệm của một vị trí.

    Args:
        job_title (str): Tên vị trí tuyển dụng.

    Returns:
        str: JSON chứa yêu cầu tuyển dụng hoặc thông báo lỗi.

    Side effect:
        Không có.
    """
    if not isinstance(job_title, str) or not job_title.strip():
        return _json_result({
            "status": "error",
            "message": "Tên vị trí không được để trống.",
        })

    normalized_title = job_title.strip().lower()
    requirements = JOB_REQUIREMENTS.get(normalized_title)
    if requirements is None:
        return _json_result({
            "status": "error",
            "message": f"Không tìm thấy vị trí '{job_title}'.",
            "available_jobs": list(JOB_REQUIREMENTS),
        })

    return _json_result({
        "status": "success",
        "job_title": normalized_title.title(),
        **requirements,
    })


def evaluate_candidate(
    candidate_skills: list[str],
    experience_years: int,
    job_title: str,
) -> str:
    """
    Đối chiếu ứng viên với yêu cầu công việc và tính điểm phù hợp.

    Kỹ năng chiếm 70 điểm, kinh nghiệm chiếm 30 điểm. Kết quả chỉ
    hỗ trợ chuyên viên tuyển dụng, không tự động loại ứng viên.

    Args:
        candidate_skills (list[str]): Danh sách kỹ năng của ứng viên.
        experience_years (int): Số năm kinh nghiệm.
        job_title (str): Vị trí cần đánh giá.

    Returns:
        str: JSON gồm điểm, kỹ năng phù hợp/thiếu và đề xuất.

    Side effect:
        Không có.
    """
    if (
        not isinstance(candidate_skills, list)
        or not all(isinstance(skill, str) for skill in candidate_skills)
    ):
        return _json_result({
            "status": "error",
            "message": "candidate_skills phải là danh sách chuỗi.",
        })
    if (
        not isinstance(experience_years, int)
        or isinstance(experience_years, bool)
        or experience_years < 0
    ):
        return _json_result({
            "status": "error",
            "message": "experience_years phải là số nguyên không âm.",
        })
    if not isinstance(job_title, str):
        return _json_result({
            "status": "error",
            "message": "job_title phải là chuỗi.",
        })

    requirements = JOB_REQUIREMENTS.get(job_title.strip().lower())
    if requirements is None:
        return _json_result({
            "status": "error",
            "message": f"Không tìm thấy vị trí '{job_title}'.",
        })

    required_skills = requirements["required_skills"]
    normalized_skills = {
        skill.strip().lower() for skill in candidate_skills
    }
    matched_skills = [
        skill for skill in required_skills if skill in normalized_skills
    ]
    missing_skills = [
        skill for skill in required_skills if skill not in normalized_skills
    ]

    skill_score = round(
        70 * len(matched_skills) / len(required_skills)
    )
    minimum_years = requirements["min_experience_years"]
    experience_score = min(
        30,
        round(30 * experience_years / minimum_years),
    )
    total_score = skill_score + experience_score

    if total_score >= 80:
        recommendation = "Đề xuất phỏng vấn"
    elif total_score >= 60:
        recommendation = "Cần chuyên viên tuyển dụng xem xét"
    else:
        recommendation = "Chưa phù hợp với vị trí hiện tại"

    return _json_result({
        "status": "success",
        "score": total_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience": f"{experience_years}/{minimum_years} năm yêu cầu",
        "recommendation": recommendation,
        "note": "Quyết định cuối cùng cần được con người xem xét.",
    })


def check_interview_slots(preferred_date: str = "") -> str:
    """
    Tra cứu các khung giờ phỏng vấn còn trống.

    Args:
        preferred_date (str): Ngày YYYY-MM-DD; để trống để xem tất cả.

    Returns:
        str: JSON chứa danh sách lịch trống hoặc thông báo lỗi.

    Side effect:
        Không có.
    """
    if not isinstance(preferred_date, str):
        return _json_result({
            "status": "error",
            "message": "preferred_date phải là chuỗi.",
        })
    if preferred_date and not _is_valid_datetime(preferred_date, date_only=True):
        return _json_result({
            "status": "error",
            "message": (
                "Ngày phải có định dạng YYYY-MM-DD và tồn tại trên lịch."
            ),
        })

    slots = [
        slot
        for slot in INTERVIEW_SLOTS
        if not preferred_date or slot.startswith(preferred_date)
    ]
    return _json_result({
        "status": "success",
        "available_slots": slots,
        "message": (
            "Đã tìm thấy lịch trống."
            if slots
            else "Không còn lịch trống vào ngày đã chọn."
        ),
    })


def schedule_interview(
    candidate_email: str,
    job_title: str,
    slot: str,
    confirmed: bool = False,
) -> str:
    """
    Đặt lịch phỏng vấn sau khi người dùng xác nhận.

    Args:
        candidate_email (str): Email ứng viên.
        job_title (str): Vị trí phỏng vấn.
        slot (str): Khung giờ YYYY-MM-DD HH:MM.
        confirmed (bool): Phải là True mới cho phép đặt lịch.

    Returns:
        str: JSON chứa lịch đã đặt, yêu cầu xác nhận hoặc lỗi.

    Side effect:
        Xóa khung giờ khỏi danh sách lịch trống trong phiên hiện tại.
    """
    if not isinstance(confirmed, bool):
        return _json_result({
            "status": "error",
            "message": "confirmed phải là kiểu boolean.",
        })
    if not confirmed:
        return _json_result({
            "status": "confirmation_required",
            "message": "Cần xác nhận trước khi đặt lịch phỏng vấn.",
        })
    if not _is_valid_email(candidate_email):
        return _json_result({
            "status": "error",
            "message": "Email ứng viên không hợp lệ.",
        })
    if not isinstance(job_title, str) or not job_title.strip():
        return _json_result({
            "status": "error",
            "message": "Tên vị trí không được để trống.",
        })
    if not _is_valid_datetime(slot):
        return _json_result({
            "status": "error",
            "message": (
                "Khung giờ phải có định dạng YYYY-MM-DD HH:MM "
                "và là thời gian hợp lệ."
            ),
        })
    if slot not in INTERVIEW_SLOTS:
        return _json_result({
            "status": "error",
            "message": "Khung giờ không tồn tại hoặc đã được đặt.",
        })

    INTERVIEW_SLOTS.remove(slot)
    return _json_result({
        "status": "success",
        "candidate_email": candidate_email,
        "job_title": job_title,
        "slot": slot,
        "message": "Đã đặt lịch phỏng vấn.",
    })


def send_interview_invitation(
    candidate_email: str,
    job_title: str,
    slot: str,
    confirmed: bool = False,
) -> str:
    """
    Mô phỏng gửi thư mời phỏng vấn sau khi người dùng xác nhận.

    Args:
        candidate_email (str): Email người nhận.
        job_title (str): Vị trí tuyển dụng.
        slot (str): Thời gian phỏng vấn.
        confirmed (bool): Phải là True mới cho phép gửi.

    Returns:
        str: JSON chứa trạng thái và nội dung thư mời.

    Side effect:
        Chỉ mô phỏng, không gửi email thật.
    """
    if not isinstance(confirmed, bool):
        return _json_result({
            "status": "error",
            "message": "confirmed phải là kiểu boolean.",
        })
    if not confirmed:
        return _json_result({
            "status": "confirmation_required",
            "message": "Cần xác nhận trước khi gửi thư mời.",
        })
    if not _is_valid_email(candidate_email):
        return _json_result({
            "status": "error",
            "message": "Email ứng viên không hợp lệ.",
        })
    if not isinstance(job_title, str) or not job_title.strip():
        return _json_result({
            "status": "error",
            "message": "Tên vị trí không được để trống.",
        })
    if not _is_valid_datetime(slot):
        return _json_result({
            "status": "error",
            "message": (
                "Thời gian phải có định dạng YYYY-MM-DD HH:MM "
                "và tồn tại trên lịch."
            ),
        })

    return _json_result({
        "status": "success",
        "recipient": candidate_email,
        "subject": f"Thư mời phỏng vấn vị trí {job_title}",
        "body": (
            f"Bạn được mời tham gia phỏng vấn vị trí "
            f"{job_title} vào lúc {slot}."
        ),
        "message": "Đã mô phỏng gửi thư thành công.",
    })


def get_weather(location: str) -> str:
    """
    Tra cứu thời tiết hiện tại của một thành phố.
    
    Args:
        location (str): Tên thành phố (Ví dụ: 'Hà Nội', 'TP.HCM', 'Đà Nẵng')
        
    Returns:
        str: Thông tin thời tiết chi tiết
    """
    if not isinstance(location, str) or not location.strip():
        return "LỖI: Địa điểm phải là chuỗi không rỗng."

    loc_lower = location.lower()
    if "hà nội" in loc_lower or "ha noi" in loc_lower:
        return "Thời tiết Hà Nội: 28°C, Nắng nhẹ, Độ ẩm 65%."
    elif "hồ chí minh" in loc_lower or "tp.hcm" in loc_lower or "hcm" in loc_lower:
        return "Thời tiết TP.HCM: 33°C, Nắng nóng, Có mây."
    elif "đà nẵng" in loc_lower or "da nang" in loc_lower:
        return "Thời tiết Đà Nẵng: 30°C, Gió nhẹ, Mát mẻ."
    else:
        return f"LỖI: Không tìm thấy dữ liệu thời tiết cho địa điểm '{location}'."


def search_flights(origin: str, destination: str) -> str:
    """
    Tra cứu chuyến bay giữa hai địa điểm.
    
    Args:
        origin (str): Nơi đi (Ví dụ: 'TP.HCM')
        destination (str): Nơi đến (Ví dụ: 'Hà Nội')
        
    Returns:
        str: Danh sách chuyến bay khả dụng và giá vé
    """
    if not isinstance(origin, str) or not origin.strip():
        return "LỖI: Nơi đi phải là chuỗi không rỗng."
    if not isinstance(destination, str) or not destination.strip():
        return "LỖI: Nơi đến phải là chuỗi không rỗng."
    if origin.strip().lower() == destination.strip().lower():
        return "LỖI: Nơi đi và nơi đến phải khác nhau."

    return (
        f"Chuyến bay từ {origin} -> {destination} ngày mai:\n"
        f"1. VN123 (08:00) - Giá: 1,500,000 VNĐ (Còn vé)\n"
        f"2. VJ456 (14:30) - Giá: 1,200,000 VNĐ (Còn vé)"
    )


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "parse_candidate_profile": parse_candidate_profile,
    "get_job_requirements": get_job_requirements,
    "evaluate_candidate": evaluate_candidate,
    "check_interview_slots": check_interview_slots,
    "schedule_interview": schedule_interview,
    "send_interview_invitation": send_interview_invitation,
    "get_weather": get_weather,
    "search_flights": search_flights,
}
