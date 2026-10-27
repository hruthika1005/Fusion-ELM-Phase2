"""Registry declaration for Employee Leave Management."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Academic",
    "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("elm.leave_request.view_self", "View own leave requests"),
    ("elm.leave_request.create", "Create a leave request"),
    ("elm.leave_request.withdraw", "Withdraw a pending leave request"),
    ("elm.leave_request.view", "View leave requests within scope"),
    ("elm.leave_request.approve", "Approve or reject leave requests"),
    ("elm.leave_request.respond_substitute", "Respond to a substitute assignment"),
    ("elm.leave_request.replace_substitute", "Replace a declined substitute"),
    ("elm.leave_request.cancel", "Request cancellation of approved leave"),
    ("elm.leave_request.extend", "Request extension of ongoing leave"),
    ("elm.leave_request.resume", "Submit resumption of duty"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "student": ["elm.leave_request.view_self", "elm.leave_request.create", "elm.leave_request.withdraw", "elm.leave_request.respond_substitute", "elm.leave_request.replace_substitute", "elm.leave_request.cancel", "elm.leave_request.extend", "elm.leave_request.resume"],
    "placement_officer": ["elm.leave_request.view", "elm.leave_request.approve"],
}
