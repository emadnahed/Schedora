"""
Tests for observability metrics to achieve 100% coverage.

Tests all metric recording functions.
"""
import pytest
from unittest.mock import Mock, patch
from schedora.observability.metrics import (
    record_job_created,
    record_job_succeeded,
    record_job_failed,
    record_job_retrying,
    record_queue_enqueue,
    record_queue_dequeue,
    update_queue_metrics,
    update_worker_metrics,
)


class TestMetricsCoverage:
    """Test all metric recording functions."""

    def test_record_job_created(self):
        """
        Test record_job_created increments counter.

        Tests line 125 in metrics.py
        """
        with patch("schedora.observability.metrics.jobs_created_total") as mock_counter:
            mock_labels = Mock()
            mock_counter.labels.return_value = mock_labels

            record_job_created("echo")

            mock_counter.labels.assert_called_once_with(job_type="echo")
            mock_labels.inc.assert_called_once()

    def test_record_job_succeeded(self):
        """
        Test record_job_succeeded increments counter and records duration.

        Tests lines 130-131 in metrics.py
        """
        with patch("schedora.observability.metrics.jobs_succeeded_total") as mock_counter:
            with patch("schedora.observability.metrics.job_duration_seconds") as mock_histogram:
                mock_counter_labels = Mock()
                mock_counter.labels.return_value = mock_counter_labels

                mock_histogram_labels = Mock()
                mock_histogram.labels.return_value = mock_histogram_labels

                record_job_succeeded("echo", duration=1.5)

                mock_counter.labels.assert_called_once_with(job_type="echo")
                mock_counter_labels.inc.assert_called_once()

                mock_histogram.labels.assert_called_once_with(job_type="echo", status="success")
                mock_histogram_labels.observe.assert_called_once_with(1.5)

    def test_record_job_failed(self):
        """
        Test record_job_failed increments counter and records duration.

        Tests lines 136-137 in metrics.py
        """
        with patch("schedora.observability.metrics.jobs_failed_total") as mock_counter:
            with patch("schedora.observability.metrics.job_duration_seconds") as mock_histogram:
                mock_counter_labels = Mock()
                mock_counter.labels.return_value = mock_counter_labels

                mock_histogram_labels = Mock()
                mock_histogram.labels.return_value = mock_histogram_labels

                record_job_failed("fail_handler", duration=2.5)

                mock_counter.labels.assert_called_once_with(job_type="fail_handler")
                mock_counter_labels.inc.assert_called_once()

                mock_histogram.labels.assert_called_once_with(job_type="fail_handler", status="failed")
                mock_histogram_labels.observe.assert_called_once_with(2.5)

    def test_record_job_retrying(self):
        """
        Test record_job_retrying increments counter.

        Tests line 142 in metrics.py
        """
        with patch("schedora.observability.metrics.jobs_retrying_total") as mock_counter:
            mock_labels = Mock()
            mock_counter.labels.return_value = mock_labels

            record_job_retrying("timeout_job")

            mock_counter.labels.assert_called_once_with(job_type="timeout_job")
            mock_labels.inc.assert_called_once()

    def test_record_queue_enqueue(self):
        """
        Test record_queue_enqueue increments counter.

        Tests line 147 in metrics.py
        """
        with patch("schedora.observability.metrics.queue_enqueued_total") as mock_counter:
            mock_labels = Mock()
            mock_counter.labels.return_value = mock_labels

            record_queue_enqueue("jobs")

            mock_counter.labels.assert_called_once_with(queue_name="jobs")
            mock_labels.inc.assert_called_once()

    def test_record_queue_dequeue(self):
        """
        Test record_queue_dequeue increments counter.

        Tests line 152 in metrics.py
        """
        with patch("schedora.observability.metrics.queue_dequeued_total") as mock_counter:
            mock_labels = Mock()
            mock_counter.labels.return_value = mock_labels

            record_queue_dequeue("jobs")

            mock_counter.labels.assert_called_once_with(queue_name="jobs")
            mock_labels.inc.assert_called_once()

    def test_update_queue_metrics_with_none_queue(self):
        """
        Test update_queue_metrics returns early when queue is None.

        Tests line 117 in metrics.py
        """
        # Should not raise exception
        update_queue_metrics(queue=None)

    def test_update_queue_metrics_with_valid_queue(self):
        """
        Test update_queue_metrics updates gauges correctly.
        """
        mock_queue = Mock()
        mock_queue.get_queue_length.return_value = 10
        mock_queue.get_dlq_length.return_value = 2

        with patch("schedora.observability.metrics.queue_length") as mock_queue_gauge:
            with patch("schedora.observability.metrics.queue_dlq_length") as mock_dlq_gauge:
                mock_queue_labels = Mock()
                mock_queue_gauge.labels.return_value = mock_queue_labels

                mock_dlq_labels = Mock()
                mock_dlq_gauge.labels.return_value = mock_dlq_labels

                update_queue_metrics(queue=mock_queue)

                mock_queue_gauge.labels.assert_called_once_with(queue_name="jobs")
                mock_queue_labels.set.assert_called_once_with(10)

                mock_dlq_gauge.labels.assert_called_once_with(queue_name="jobs")
                mock_dlq_labels.set.assert_called_once_with(2)

    @pytest.mark.integration
    def test_update_worker_metrics_integration(self, db_session):
        """
        Test update_worker_metrics reads from database and updates gauges.
        """
        from schedora.models.worker import Worker
        from schedora.core.enums import WorkerStatus

        # Create test workers
        worker1 = Worker(
            worker_id="w1",
            hostname="host1",
            pid=1001,
            version="1.0.0",
            status=WorkerStatus.ACTIVE,
            max_concurrent_jobs=5
        )
        worker2 = Worker(
            worker_id="w2",
            hostname="host2",
            pid=1002,
            version="1.0.0",
            status=WorkerStatus.STALE,
            max_concurrent_jobs=5
        )
        db_session.add_all([worker1, worker2])
        db_session.commit()

        with patch("schedora.observability.metrics.workers_active") as mock_active:
            with patch("schedora.observability.metrics.workers_stale") as mock_stale:
                update_worker_metrics(db_session)

                mock_active.set.assert_called_once()
                mock_stale.set.assert_called_once()
