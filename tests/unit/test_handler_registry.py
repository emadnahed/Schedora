"""Unit tests for Handler Registry."""
import pytest


class TestHandlerRegistry:
    """Unit tests for HandlerRegistry."""

    def test_register_handler_function(self):
        """Test registering a handler function."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        async def my_handler(payload):
            return {"result": "success"}

        registry.register_handler("test_job", my_handler)

        assert registry.has_handler("test_job")
        handler = registry.get_handler("test_job")
        assert handler == my_handler

    def test_get_registered_handler(self):
        """Test getting a registered handler."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        async def echo_handler(payload):
            return payload

        registry.register_handler("echo", echo_handler)

        handler = registry.get_handler("echo")
        assert handler == echo_handler

    def test_get_handler_not_found_raises_error(self):
        """Test getting non-existent handler raises KeyError."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        with pytest.raises(KeyError, match="No handler registered for job type: nonexistent"):
            registry.get_handler("nonexistent")

    def test_decorator_registration(self):
        """Test using decorator to register handler."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        @registry.register("decorated_job")
        async def decorated_handler(payload):
            return {"decorated": True}

        assert registry.has_handler("decorated_job")
        handler = registry.get_handler("decorated_job")
        assert handler == decorated_handler

    def test_duplicate_handler_raises_error(self):
        """Test registering duplicate handler raises ValueError."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        async def handler1(payload):
            return "first"

        async def handler2(payload):
            return "second"

        registry.register_handler("duplicate", handler1)

        with pytest.raises(ValueError, match="Handler for job type 'duplicate' already registered"):
            registry.register_handler("duplicate", handler2)

    def test_list_all_handlers(self):
        """Test listing all registered handlers."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        async def handler1(payload):
            return "1"

        async def handler2(payload):
            return "2"

        async def handler3(payload):
            return "3"

        registry.register_handler("job1", handler1)
        registry.register_handler("job2", handler2)
        registry.register_handler("job3", handler3)

        handlers = registry.list_handlers()

        assert len(handlers) == 3
        assert "job1" in handlers
        assert "job2" in handlers
        assert "job3" in handlers

    def test_has_handler_returns_false_for_unregistered(self):
        """Test has_handler returns False for unregistered handler."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        assert not registry.has_handler("nonexistent")

    def test_has_handler_returns_true_for_registered(self):
        """Test has_handler returns True for registered handler."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        async def handler(payload):
            return "test"

        registry.register_handler("exists", handler)

        assert registry.has_handler("exists")

    def test_empty_registry_list_handlers(self):
        """Test list_handlers on empty registry returns empty list."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        handlers = registry.list_handlers()

        assert handlers == []

    def test_register_handler_with_sync_function(self):
        """Test registering sync function (should still work)."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()

        def sync_handler(payload):
            return {"sync": True}

        registry.register_handler("sync_job", sync_handler)

        assert registry.has_handler("sync_job")
        handler = registry.get_handler("sync_job")
        assert handler == sync_handler

    def test_multiple_registries_are_independent(self):
        """Test that multiple registry instances are independent."""
        from schedora.worker.handler_registry import HandlerRegistry

        registry1 = HandlerRegistry()
        registry2 = HandlerRegistry()

        async def handler1(payload):
            return "1"

        async def handler2(payload):
            return "2"

        registry1.register_handler("job1", handler1)
        registry2.register_handler("job2", handler2)

        assert registry1.has_handler("job1")
        assert not registry1.has_handler("job2")

        assert registry2.has_handler("job2")
        assert not registry2.has_handler("job1")
