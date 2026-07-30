"""Plain-assert self-check for graph/routing.py's department/priority mapping —
the logic now feeding real ticket rows from the triage node.
Run with: python tests/test_routing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.graph.routing import (
    HIGH,
    LOW,
    MEDIUM,
    URGENT,
    compute_priority,
    route_department,
)

assert route_department("hostel_issue") == "Hostel Administration"
assert route_department("exam_policy") == "Examination Cell"
assert route_department("unknown_intent") == "Student Services"  # fallback

assert compute_priority("general_info") == LOW
assert compute_priority("hostel_issue") == MEDIUM  # no signals -> default
assert compute_priority("od_leave_request", hours_to_deadline=10) == URGENT
assert compute_priority("od_leave_request", hours_to_deadline=48) == HIGH
assert compute_priority("od_leave_request", blocks_exam_or_scholarship=True) == URGENT
assert compute_priority("hostel_issue", residence_or_safety=True) == HIGH

print("test_routing: all assertions passed")
