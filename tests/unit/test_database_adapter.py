"""Unit tests for Database Adapter."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4


class TestDatabaseAdapter:
    """Unit tests for DatabaseAdapter."""

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_claim_job(self, mock_to_thread):
        """Test async claim_job calls scheduler.claim_job in thread."""
        from schedora.worker.database_adapter import DatabaseAdapter

        # Mock scheduler and claimed job
        mock_scheduler = Mock()
        mock_job = Mock()
        mock_job.job_id = uuid4()
        mock_scheduler.claim_job.return_value = mock_job

        # Mock to_thread to return the job
        mock_to_thread.return_value = mock_job

        adapter = DatabaseAdapter(mock_scheduler)
        result = await adapter.claim_job("test-worker-1")

        # Verify to_thread was called with scheduler.claim_job
        mock_to_thread.assert_called_once()
        assert result == mock_job

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_transition_job_status(self, mock_to_thread):
        """Test async transition_job_status calls state_machine in thread."""
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.core.enums import JobStatus

        mock_scheduler = Mock()
        mock_state_machine = Mock()
        mock_job = Mock()
        mock_job.job_id = uuid4()

        # Mock transition result
        mock_state_machine.transition.return_value = mock_job
        mock_to_thread.return_value = mock_job

        adapter = DatabaseAdapter(mock_scheduler, mock_state_machine)
        result = await adapter.transition_job_status(
            mock_job.job_id, JobStatus.SUCCESS
        )

        # Verify to_thread was called
        mock_to_thread.assert_called_once()
        assert result == mock_job

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_update_job_result(self, mock_to_thread):
        """Test async update_job_result calls job_service in thread."""
        from schedora.worker.database_adapter import DatabaseAdapter

        mock_scheduler = Mock()
        mock_job_service = Mock()
        job_id = uuid4()
        result = {"success": True}

        # Mock update result
        mock_job_service.update_job_result.return_value = None
        mock_to_thread.return_value = None

        adapter = DatabaseAdapter(mock_scheduler, job_service=mock_job_service)
        await adapter.update_job_result(job_id, result)

        # Verify to_thread was called
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_update_job_error(self, mock_to_thread):
        """Test async update_job_error calls job_service in thread."""
        from schedora.worker.database_adapter import DatabaseAdapter

        mock_scheduler = Mock()
        mock_job_service = Mock()
        job_id = uuid4()
        error = "Test error"

        # Mock update error
        mock_job_service.update_job_error.return_value = None
        mock_to_thread.return_value = None

        adapter = DatabaseAdapter(mock_scheduler, job_service=mock_job_service)
        await adapter.update_job_error(job_id, error, details={"stack": "..."})

        # Verify to_thread was called
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_schedule_retry(self, mock_to_thread):
        """Test async schedule_retry calls retry_service in thread."""
        from schedora.worker.database_adapter import DatabaseAdapter

        mock_scheduler = Mock()
        mock_retry_service = Mock()
        job_id = uuid4()
        error = "Test error"

        # Mock schedule retry
        mock_retry_service.schedule_retry.return_value = None
        mock_to_thread.return_value = None

        adapter = DatabaseAdapter(mock_scheduler, retry_service=mock_retry_service)
        await adapter.schedule_retry(job_id, error)

        # Verify to_thread was called
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch('schedora.worker.database_adapter.asyncio.to_thread')
    async def test_error_handling(self, mock_to_thread):
        """Test adapter propagates errors from sync operations."""
        from schedora.worker.database_adapter import DatabaseAdapter

        mock_scheduler = Mock()

        # Mock to_thread to raise exception
        mock_to_thread.side_effect = Exception("Database error")

        adapter = DatabaseAdapter(mock_scheduler)

        with pytest.raises(Exception, match="Database error"):
            await adapter.claim_job("test-worker")

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test DatabaseAdapter can be initialized with services."""
        from schedora.worker.database_adapter import DatabaseAdapter

        mock_scheduler = Mock()
        mock_state_machine = Mock()
        mock_job_service = Mock()
        mock_retry_service = Mock()

        adapter = DatabaseAdapter(
            scheduler=mock_scheduler,
            state_machine=mock_state_machine,
            job_service=mock_job_service,
            retry_service=mock_retry_service,
        )

        assert adapter.scheduler == mock_scheduler
        assert adapter.state_machine == mock_state_machine
        assert adapter.job_service == mock_job_service
        assert adapter.retry_service == mock_retry_service
