"""
Tests for AI service layer with seed_data_v4.
Tests context loading (integration), prompt building (unit),
AI service flow (mocked LLM), and approval handlers (integration).
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import time

from app.db.database import SessionLocal
from app.db.models.users import Users
from app.db.models.ai_inputs import AIInputs
from app.db.models.ai_outputs import AIOutputs, AIOutputStatus
from app.db.models.ai_proposals import AIProposals, ProposalStatus, ProposalType
from app.db.models.availability_rules import AvailabilityRules, AvailabilityRuleType
from app.db.models.coverage_requirements import CoverageRequirements

from app.services.ai.context_loader import (
    load_employee_context,
    load_store_context,
    load_coverage_context,
    load_store_employees_context,
)
from app.services.ai.prompts import build_system_prompt, build_user_prompt
from app.services.ai.ai_service import process_ai_input, _get_allowed_types
from app.services.ai.approval_handler import apply_proposal, ApprovalError
from app.services.ai.llm_provider import LLMResponse


# Seed data IDs
ADMIN_USER_ID = 100001
MANAGER_USER_ID = 100002
ALICE_USER_ID = 100003
BOB_USER_ID = 100004
EMMA_USER_ID = 100007

MANAGER_EMP_ID = 100001
ALICE_EMP_ID = 100002
BOB_EMP_ID = 100003
EMMA_EMP_ID = 100006

STORE_ID = 100001
TILLS_DEPT_ID = 100001
FLOOR_DEPT_ID = 100002
CS_DEPT_ID = 100003


@pytest.fixture(scope="module")
def db():
    """Read-only session for context loader / prompt tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def write_db():
    """Per-test session that rolls back after each test. No cleanup needed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==================== Context Loader Tests ====================

class TestContextLoader:
    def test_load_employee_context_alice(self, db):
        ctx = load_employee_context(db, ALICE_USER_ID)
        assert ctx is not None
        assert ctx["employee_id"] == ALICE_EMP_ID
        assert ctx["store_id"] == STORE_ID
        assert ctx["is_keyholder"] is True
        assert ctx["contracted_weekly_hours"] == 32
        assert "Alice" in ctx["name"]

    def test_load_employee_context_departments(self, db):
        ctx = load_employee_context(db, ALICE_USER_ID)
        dept_ids = [d["department_id"] for d in ctx["departments"]]
        assert TILLS_DEPT_ID in dept_ids
        assert CS_DEPT_ID in dept_ids

    def test_load_employee_context_availability(self, db):
        ctx = load_employee_context(db, ALICE_USER_ID)
        assert len(ctx["current_availability"]) > 0
        sunday_rules = [r for r in ctx["current_availability"] if r["day_of_week"] == 6]
        assert any(r["rule_type"] == "UNAVAILABLE" for r in sunday_rules)

    def test_load_employee_context_nonexistent_user(self, db):
        ctx = load_employee_context(db, 999999)
        assert ctx is None

    def test_load_employee_context_admin_no_employee(self, db):
        ctx = load_employee_context(db, ADMIN_USER_ID)
        assert ctx is None

    def test_load_store_context(self, db):
        ctx = load_store_context(db, STORE_ID)
        assert ctx is not None
        assert ctx["store_name"] == "Central London"
        assert len(ctx["departments"]) == 3
        dept_names = [d["name"] for d in ctx["departments"]]
        assert "Tills" in dept_names
        assert "Shop Floor" in dept_names
        assert "Customer Service" in dept_names

    def test_load_coverage_context(self, db):
        reqs = load_coverage_context(db, STORE_ID)
        assert len(reqs) == 12

    def test_load_coverage_context_filtered(self, db):
        reqs = load_coverage_context(db, STORE_ID, department_id=CS_DEPT_ID)
        assert len(reqs) == 5

    def test_load_store_employees_context(self, db):
        emps = load_store_employees_context(db, STORE_ID)
        assert len(emps) == 7
        names = [e["name"] for e in emps]
        assert any("Alice" in n for n in names)
        assert any("Frank" in n for n in names)


# ==================== Prompt Building Tests ====================

class TestPromptBuilding:
    def test_system_prompt_employee(self):
        prompt = build_system_prompt(["AVAILABILITY"], is_manager=False)
        assert "employee" in prompt.lower()
        assert "AVAILABILITY" in prompt
        assert "COVERAGE" not in prompt

    def test_system_prompt_manager(self):
        prompt = build_system_prompt(["AVAILABILITY", "COVERAGE", "ROLE_REQUIREMENT"], is_manager=True)
        assert "manager" in prompt.lower()
        assert "AVAILABILITY" in prompt
        assert "COVERAGE" in prompt
        assert "ROLE_REQUIREMENT" in prompt

    def test_system_prompt_includes_day_map(self):
        prompt = build_system_prompt(["AVAILABILITY"], is_manager=False)
        assert "monday" in prompt.lower()

    def test_user_prompt_includes_input(self):
        prompt = build_user_prompt("I can't work Tuesdays", {"employee": {"name": "Alice"}})
        assert "I can't work Tuesdays" in prompt
        assert "Alice" in prompt

    def test_user_prompt_includes_context_json(self):
        ctx = {"employee": {"employee_id": 100002, "store_id": 100001}}
        prompt = build_user_prompt("test", ctx)
        assert "100002" in prompt


# ==================== Permission Tests ====================

class TestPermissions:
    def test_employee_allowed_types(self):
        assert _get_allowed_types(False) == ["AVAILABILITY"]

    def test_manager_allowed_types(self):
        types = _get_allowed_types(True)
        assert "AVAILABILITY" in types
        assert "COVERAGE" in types
        assert "ROLE_REQUIREMENT" in types


# ==================== AI Service Tests (Mocked LLM) ====================

def _mock_llm_response(result_json: dict) -> LLMResponse:
    return LLMResponse(
        raw_text=json.dumps(result_json),
        parsed_json=result_json,
        model_used="test/mock",
        success=True,
    )


def _mock_failed_llm_response() -> LLMResponse:
    return LLMResponse(
        raw_text="",
        parsed_json=None,
        model_used="test/mock",
        success=False,
        error="Mock LLM failure",
    )


class TestAIServiceAvailability:
    @patch("app.services.ai.ai_service.get_llm_provider")
    def test_employee_availability_request(self, mock_provider_factory, write_db):
        """Employee says 'I can't work Tuesdays' -> creates AVAILABILITY proposal."""
        mock_provider = MagicMock()
        mock_provider.generate_json.return_value = _mock_llm_response({
            "intent_type": "AVAILABILITY",
            "employee_id": ALICE_EMP_ID,
            "changes": [
                {"action": "ADD", "day_of_week": 1, "start_time": None, "end_time": None, "rule_type": "UNAVAILABLE"}
            ],
            "summary": "Marking Tuesdays as unavailable",
        })
        mock_provider_factory.return_value = mock_provider

        user = write_db.query(Users).filter(Users.id == ALICE_USER_ID).first()
        ai_input = AIInputs(req_by_user_id=user.id, input_text="I can't work Tuesdays")
        write_db.add(ai_input)
        write_db.flush()

        output = process_ai_input(write_db, ai_input, user)

        assert output.status == AIOutputStatus.COMPLETE
        assert output.result_json["intent_type"] == "AVAILABILITY"
        assert output.affects_user_id == ALICE_USER_ID
        assert ai_input.processed is True

        proposal = write_db.query(AIProposals).filter(AIProposals.ai_output_id == output.id).first()
        assert proposal is not None
        assert proposal.type == ProposalType.AVAILABILITY
        assert proposal.status == ProposalStatus.PENDING

    @patch("app.services.ai.ai_service.get_llm_provider")
    def test_employee_cannot_request_coverage(self, mock_provider_factory, write_db):
        """Employee requesting coverage change should be rejected."""
        mock_provider = MagicMock()
        mock_provider.generate_json.return_value = _mock_llm_response({
            "intent_type": "COVERAGE",
            "store_id": STORE_ID,
            "department_id": TILLS_DEPT_ID,
            "changes": [],
            "summary": "test",
        })
        mock_provider_factory.return_value = mock_provider

        user = write_db.query(Users).filter(Users.id == ALICE_USER_ID).first()
        ai_input = AIInputs(req_by_user_id=user.id, input_text="We need more staff on tills")
        write_db.add(ai_input)
        write_db.flush()

        output = process_ai_input(write_db, ai_input, user)

        assert output.status == AIOutputStatus.INVALID
        assert "availability" in output.summary.lower()


class TestAIServiceManager:
    @patch("app.services.ai.ai_service.get_llm_provider")
    def test_manager_coverage_request(self, mock_provider_factory, write_db):
        """Manager requests coverage change -> creates COVERAGE proposal."""
        mock_provider = MagicMock()
        mock_provider.generate_json.return_value = _mock_llm_response({
            "intent_type": "COVERAGE",
            "store_id": STORE_ID,
            "department_id": TILLS_DEPT_ID,
            "changes": [
                {"action": "ADD", "day_of_week": 5, "start_time": "10:00", "end_time": "16:00",
                 "min_staff": 3, "max_staff": None, "coverage_id": None}
            ],
            "summary": "Adding 3 staff minimum for Tills on Saturday",
        })
        mock_provider_factory.return_value = mock_provider

        user = write_db.query(Users).filter(Users.id == MANAGER_USER_ID).first()
        ai_input = AIInputs(req_by_user_id=user.id, input_text="We need 3 people on tills Saturday 10-4")
        write_db.add(ai_input)
        write_db.flush()

        output = process_ai_input(write_db, ai_input, user)

        assert output.status == AIOutputStatus.COMPLETE
        assert output.result_json["intent_type"] == "COVERAGE"

        proposal = write_db.query(AIProposals).filter(AIProposals.ai_output_id == output.id).first()
        assert proposal is not None
        assert proposal.type == ProposalType.COVERAGE


class TestAIServiceErrors:
    @patch("app.services.ai.ai_service.get_llm_provider")
    def test_llm_failure_creates_invalid_output(self, mock_provider_factory, write_db):
        """LLM failure should create INVALID output."""
        mock_provider = MagicMock()
        mock_provider.generate_json.return_value = _mock_failed_llm_response()
        mock_provider_factory.return_value = mock_provider

        user = write_db.query(Users).filter(Users.id == ALICE_USER_ID).first()
        ai_input = AIInputs(req_by_user_id=user.id, input_text="gibberish input")
        write_db.add(ai_input)
        write_db.flush()

        output = process_ai_input(write_db, ai_input, user)

        assert output.status == AIOutputStatus.INVALID
        assert ai_input.processed is True

    @patch("app.services.ai.ai_service.get_llm_provider")
    def test_labour_budget_returns_error(self, mock_provider_factory, write_db):
        """Labour budget intent should return error (not yet supported)."""
        mock_provider = MagicMock()
        mock_provider.generate_json.return_value = _mock_llm_response({
            "intent_type": "LABOUR_BUDGET",
            "summary": "Change labour budget",
        })
        mock_provider_factory.return_value = mock_provider

        user = write_db.query(Users).filter(Users.id == MANAGER_USER_ID).first()
        ai_input = AIInputs(req_by_user_id=user.id, input_text="increase budget for tills")
        write_db.add(ai_input)
        write_db.flush()

        output = process_ai_input(write_db, ai_input, user)

        assert output.status == AIOutputStatus.INVALID
        assert "not yet supported" in output.summary.lower()


# ==================== Approval Handler Tests ====================

class TestApprovalHandlerAvailability:
    def test_add_availability_rule(self, write_db):
        """Approving availability ADD should create new rule."""
        ai_input = AIInputs(req_by_user_id=EMMA_USER_ID, input_text="test", processed=True)
        write_db.add(ai_input)
        write_db.flush()

        result_json = {
            "intent_type": "AVAILABILITY",
            "employee_id": EMMA_EMP_ID,
            "changes": [
                {"action": "ADD", "day_of_week": 6, "start_time": None, "end_time": None, "rule_type": "UNAVAILABLE"}
            ],
            "summary": "Emma unavailable Sundays",
        }
        output = AIOutputs(
            input_id=ai_input.id, result_json=result_json,
            summary="test", status=AIOutputStatus.COMPLETE,
        )
        write_db.add(output)
        write_db.flush()

        proposal = AIProposals(
            ai_output_id=output.id, type=ProposalType.AVAILABILITY,
            store_id=STORE_ID, status=ProposalStatus.PENDING,
        )
        write_db.add(proposal)
        write_db.flush()

        before_count = write_db.query(AvailabilityRules).filter(
            AvailabilityRules.employee_id == EMMA_EMP_ID,
            AvailabilityRules.day_of_week == 6,
        ).count()

        apply_proposal(write_db, proposal, MANAGER_USER_ID)
        write_db.flush()

        after_count = write_db.query(AvailabilityRules).filter(
            AvailabilityRules.employee_id == EMMA_EMP_ID,
            AvailabilityRules.day_of_week == 6,
        ).count()

        assert after_count == before_count + 1


class TestApprovalHandlerCoverage:
    def test_add_coverage_requirement(self, write_db):
        """Approving coverage ADD should create new requirement."""
        ai_input = AIInputs(req_by_user_id=MANAGER_USER_ID, input_text="test", processed=True)
        write_db.add(ai_input)
        write_db.flush()

        result_json = {
            "intent_type": "COVERAGE",
            "store_id": STORE_ID,
            "department_id": FLOOR_DEPT_ID,
            "changes": [
                {"action": "ADD", "day_of_week": 5, "start_time": "10:00", "end_time": "16:00",
                 "min_staff": 2, "max_staff": None, "coverage_id": None}
            ],
            "summary": "Add Shop Floor Saturday coverage",
        }
        output = AIOutputs(
            input_id=ai_input.id, result_json=result_json,
            summary="test", status=AIOutputStatus.COMPLETE,
        )
        write_db.add(output)
        write_db.flush()

        proposal = AIProposals(
            ai_output_id=output.id, type=ProposalType.COVERAGE,
            store_id=STORE_ID, department_id=FLOOR_DEPT_ID, status=ProposalStatus.PENDING,
        )
        write_db.add(proposal)
        write_db.flush()

        before_count = write_db.query(CoverageRequirements).filter(
            CoverageRequirements.store_id == STORE_ID,
            CoverageRequirements.department_id == FLOOR_DEPT_ID,
        ).count()

        apply_proposal(write_db, proposal, ADMIN_USER_ID)
        write_db.flush()

        after_count = write_db.query(CoverageRequirements).filter(
            CoverageRequirements.store_id == STORE_ID,
            CoverageRequirements.department_id == FLOOR_DEPT_ID,
        ).count()

        assert after_count == before_count + 1


class TestApprovalHandlerErrors:
    def test_missing_output_raises(self, write_db):
        """Proposal with no linked output should raise ApprovalError."""
        proposal = MagicMock()
        proposal.ai_output_id = 999999
        with pytest.raises(ApprovalError):
            apply_proposal(write_db, proposal, ADMIN_USER_ID)