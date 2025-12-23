"""Integration tests for Job dependencies (DAG support)."""
import pytest
from schedora.core.enums import JobStatus
from tests.factories.job_factory import create_job


class TestJobDependencies:
    """Test job dependency relationships for DAG workflows."""

    def test_job_can_have_dependencies(self, db_session):
        """Test a job can depend on other jobs."""
        # Create parent jobs
        validate_order = create_job(db_session, job_type="validate_order", idempotency_key="dep-1")
        reserve_inventory = create_job(db_session, job_type="reserve_inventory", idempotency_key="dep-2")

        # Create child job that depends on both
        charge_payment = create_job(db_session, job_type="charge_payment", idempotency_key="dep-3")

        # Add dependencies
        charge_payment.dependencies.append(validate_order)
        charge_payment.dependencies.append(reserve_inventory)
        db_session.commit()
        db_session.refresh(charge_payment)

        assert len(charge_payment.dependencies) == 2
        assert validate_order in charge_payment.dependencies
        assert reserve_inventory in charge_payment.dependencies

    def test_job_can_have_dependents(self, db_session):
        """Test a job can have jobs that depend on it."""
        # Create parent job
        validate_order = create_job(db_session, job_type="validate_order", idempotency_key="parent-1")

        # Create children that depend on it
        reserve_inventory = create_job(db_session, job_type="reserve_inventory", idempotency_key="child-1")
        charge_payment = create_job(db_session, job_type="charge_payment", idempotency_key="child-2")

        reserve_inventory.dependencies.append(validate_order)
        charge_payment.dependencies.append(validate_order)
        db_session.commit()
        db_session.refresh(validate_order)

        assert len(validate_order.dependents) == 2
        assert reserve_inventory in validate_order.dependents
        assert charge_payment in validate_order.dependents

    def test_dag_workflow_structure(self, db_session):
        """Test a complete DAG workflow structure."""
        # Build order processing DAG:
        #     validate_order
        #          |
        #    +-----------+
        #    |           |
        # reserve_inv  fraud_check
        #    |           |
        #    +-----+-----+
        #          |
        #    charge_payment
        #          |
        #    generate_invoice

        validate = create_job(db_session, job_type="validate_order", idempotency_key="dag-1")
        reserve = create_job(db_session, job_type="reserve_inventory", idempotency_key="dag-2")
        fraud = create_job(db_session, job_type="fraud_check", idempotency_key="dag-3")
        charge = create_job(db_session, job_type="charge_payment", idempotency_key="dag-4")
        invoice = create_job(db_session, job_type="generate_invoice", idempotency_key="dag-5")

        # Build dependencies
        reserve.dependencies.append(validate)
        fraud.dependencies.append(validate)
        charge.dependencies.append(reserve)
        charge.dependencies.append(fraud)
        invoice.dependencies.append(charge)

        db_session.commit()
        db_session.refresh(validate)
        db_session.refresh(charge)

        # Validate structure
        assert len(validate.dependents) == 2
        assert len(charge.dependencies) == 2
        assert len(charge.dependents) == 1
        assert invoice in charge.dependents

    def test_no_circular_dependencies_check(self, db_session):
        """Test we can detect circular dependencies (future validation)."""
        job_a = create_job(db_session, job_type="job_a", idempotency_key="circ-1")
        job_b = create_job(db_session, job_type="job_b", idempotency_key="circ-2")

        # Add dependencies
        job_a.dependencies.append(job_b)
        job_b.dependencies.append(job_a)  # Circular!

        db_session.commit()

        # For now, this is allowed at DB level
        # In Phase 2, we'll add validation logic to prevent this
        assert job_a in job_b.dependents
        assert job_b in job_a.dependents
