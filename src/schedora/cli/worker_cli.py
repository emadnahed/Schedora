"""CLI entry point for running async workers."""
import asyncio
import signal
import logging
import socket
import os
import sys
from schedora.core.database import SessionLocal
from schedora.worker.async_worker import AsyncWorker
from schedora.worker.handler_registry import HandlerRegistry
from schedora.services.heartbeat_service import HeartbeatService
from schedora.core.redis import get_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_handlers(registry: HandlerRegistry) -> None:
    """
    Register example job handlers.

    Args:
        registry: Handler registry to register handlers with
    """
    from schedora.worker.handlers.echo_handler import echo_handler
    from schedora.worker.handlers.sleep_handler import sleep_handler
    from schedora.worker.handlers.fail_handler import fail_handler

    registry.register_handler("echo", echo_handler)
    registry.register_handler("sleep", sleep_handler)
    registry.register_handler("fail", fail_handler)

    logger.info("Registered handlers: echo, sleep, fail")


async def run_worker(
    worker_id: str = None,
    max_concurrent_jobs: int = 10,
    poll_interval: float = 1.0,
) -> None:
    """
    Run an async worker.

    Args:
        worker_id: Optional worker ID (auto-generated if not provided)
        max_concurrent_jobs: Maximum concurrent jobs to execute
        poll_interval: Polling interval in seconds
    """
    # Generate worker ID if not provided
    if not worker_id:
        hostname = socket.gethostname()
        pid = os.getpid()
        worker_id = f"worker-{hostname}-{pid}"

    logger.info(f"Starting worker: {worker_id}")

    # Setup database session and Redis
    db_session = SessionLocal()
    redis_client = get_redis()

    # Setup handler registry
    registry = HandlerRegistry()
    setup_handlers(registry)

    # Create worker
    worker = AsyncWorker(
        worker_id=worker_id,
        db_session=db_session,
        handler_registry=registry,
        max_concurrent_jobs=max_concurrent_jobs,
        poll_interval=poll_interval,
    )

    # Setup signal handlers for graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register worker with heartbeat service
    heartbeat_service = HeartbeatService(db_session, redis_client)
    try:
        heartbeat_service.register_worker(
            worker_id=worker_id,
            hostname=socket.gethostname(),
            pid=os.getpid(),
            max_concurrent_jobs=max_concurrent_jobs,
        )
        logger.info(f"Worker {worker_id} registered")
    except Exception as e:
        logger.error(f"Failed to register worker: {e}")
        sys.exit(1)

    # Start worker
    worker_task = asyncio.create_task(worker.start())

    # Start heartbeat sender
    async def send_heartbeats():
        """Send periodic heartbeats."""
        while not stop_event.is_set():
            try:
                heartbeat_service.send_heartbeat(worker_id)
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")

    heartbeat_task = asyncio.create_task(send_heartbeats())

    # Wait for stop signal
    await stop_event.wait()

    # Graceful shutdown
    logger.info("Stopping worker...")
    heartbeat_task.cancel()
    await worker.stop(timeout=30.0)
    await worker_task

    # Deregister worker
    try:
        heartbeat_service.deregister_worker(worker_id)
        logger.info(f"Worker {worker_id} deregistered")
    except Exception as e:
        logger.error(f"Error deregistering worker: {e}")

    # Cleanup
    db_session.close()
    logger.info("Worker stopped")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
