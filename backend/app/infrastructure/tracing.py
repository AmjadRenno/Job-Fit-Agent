from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from app.models.execution_trace import ExecutionTrace, TraceEvent, TraceEventStatus, TraceStatus


T = TypeVar("T")


class ExecutionTraceRecorder:
    def __init__(self, operation: str, run_id: str | None = None) -> None:
        self._operation = operation
        self._run_id = run_id or f"run-{uuid4().hex[:12]}"
        self._operation_id = f"{operation}-{uuid4().hex[:8]}"
        self._events: list[TraceEvent] = []
        self._failed = False

    @property
    def run_id(self) -> str:
        return self._run_id

    def record(self, step: str, action: Callable[[], T]) -> T:
        started_at = perf_counter()
        status: TraceEventStatus = "success"
        detail: str | None = None

        try:
            return action()
        except Exception as error:
            status = "failed"
            self._failed = True
            detail = error.__class__.__name__
            raise
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            self._events.append(
                TraceEvent(
                    step=step,
                    status=status,
                    duration_ms=duration_ms,
                    detail=detail,
                )
            )

    def build(self, status: str | None = None) -> ExecutionTrace:
        final_status: TraceStatus = status or ("failed" if self._failed else "success")
        return ExecutionTrace(
            run_id=self._run_id,
            operation_id=self._operation_id,
            operation=self._operation,
            status=final_status,
            events=self._events,
        )
