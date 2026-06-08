from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, Self

import anyio
from anyio import EndOfStream, WouldBlock, to_thread

if TYPE_CHECKING:
    from types import TracebackType

    from anyio.abc import TaskGroup
    from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

    from big_brother.domain.policy import ModelSignal


class BatchModerationClient(Protocol):
    def classify_many(self, *, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]: ...


class BatcherNotStartedError(Exception):
    def __init__(self) -> None:
        super().__init__("moderation batcher must be used as an async context manager")


class BatcherClosedError(Exception):
    def __init__(self) -> None:
        super().__init__("moderation batcher closed before producing a result")


class BatchInferenceError(Exception):
    def __init__(self) -> None:
        super().__init__("batch moderation inference failed")


class BatchCardinalityError(Exception):
    def __init__(self, *, expected: int, actual: int) -> None:
        self.expected: int = expected
        self.actual: int = actual
        super().__init__("batch moderation result count did not match request count")


@dataclass(slots=True)
class PendingModerationRequest:
    """Mutable because the worker fills the result before releasing the waiter."""

    image_bytes: bytes
    ready: anyio.Event = field(default_factory=anyio.Event)
    signal: ModelSignal | None = None
    error: Exception | None = None


class AsyncModerationBatcher:
    def __init__(
        self,
        *,
        client: BatchModerationClient,
        max_batch_size: int,
        max_wait_ms: int,
        max_pending: int,
    ) -> None:
        self._client: BatchModerationClient = client
        self._max_batch_size: int = max_batch_size
        self._max_wait_seconds: float = max_wait_ms / 1000
        send_stream, receive_stream = anyio.create_memory_object_stream[PendingModerationRequest](
            max_pending
        )
        self._send: MemoryObjectSendStream[PendingModerationRequest] = send_stream
        self._receive: MemoryObjectReceiveStream[PendingModerationRequest] = receive_stream
        self._task_group: TaskGroup | None = None

    async def __aenter__(self) -> Self:
        task_group = anyio.create_task_group()
        self._task_group = await task_group.__aenter__()
        self._task_group.start_soon(self._run)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._send.aclose()
        task_group = self._task_group
        if task_group is not None:
            _ = await task_group.__aexit__(exc_type, exc_value, traceback)

    async def classify(self, *, image_bytes: bytes) -> ModelSignal:
        request = PendingModerationRequest(image_bytes=image_bytes)
        try:
            await self._send.send(request)
        except EndOfStream as error:
            raise BatcherNotStartedError from error
        await request.ready.wait()
        if request.error is not None:
            raise request.error
        if request.signal is None:
            raise BatcherClosedError
        return request.signal

    async def _run(self) -> None:
        async with self._receive:
            while True:
                try:
                    first_request = await self._receive.receive()
                except EndOfStream:
                    return
                batch = await self._collect_batch(first_request)
                await self._complete_batch(batch=batch)

    async def _collect_batch(
        self,
        first_request: PendingModerationRequest,
    ) -> tuple[PendingModerationRequest, ...]:
        batch = [first_request]
        deadline = anyio.current_time() + self._max_wait_seconds
        while len(batch) < self._max_batch_size:
            try:
                batch.append(self._receive.receive_nowait())
                continue
            except WouldBlock:
                pass
            remaining = deadline - anyio.current_time()
            if remaining <= 0:
                break
            with anyio.move_on_after(remaining):
                try:
                    batch.append(await self._receive.receive())
                except EndOfStream:
                    break
        return tuple(batch)

    async def _complete_batch(self, *, batch: tuple[PendingModerationRequest, ...]) -> None:
        try:
            signals = await to_thread.run_sync(
                self._classify_batch,
                tuple(request.image_bytes for request in batch),
            )
        except RuntimeError:
            _fail_batch(batch=batch, error=BatchInferenceError())
            return
        if len(signals) != len(batch):
            _fail_batch(
                batch=batch,
                error=BatchCardinalityError(expected=len(batch), actual=len(signals)),
            )
            return
        for request, signal in zip(batch, signals, strict=True):
            request.signal = signal
            request.ready.set()

    def _classify_batch(self, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]:
        return self._client.classify_many(image_bytes_list=image_bytes_list)


def _fail_batch(*, batch: tuple[PendingModerationRequest, ...], error: Exception) -> None:
    for request in batch:
        request.error = error
        request.ready.set()
