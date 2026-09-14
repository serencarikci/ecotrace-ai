"""Exact-arithmetic Leontief solver for the CBAM SEE internal product-flow matrix.

Every operation runs on :class:`decimal.Decimal` inside a local context with a fixed,
generous precision. No float ever touches the pipeline, no epsilon pseudo-inverse is
applied and an exactly-zero pivot fails closed instead of being nudged.

Matrix orientation (workbook SEE, ``D_Processes`` process-to-process block)::

    A[consumer_i][supplier_j] = qty_of_j_consumed_in_i / TotProd(i)

so a row is a consuming process/product and a column is a supplying one. The specific
embedded emissions vector solves ``(I - A) · SEE = base``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext

ZERO = Decimal("0")
ONE = Decimal("1")

# Well above the NUMERIC(36, 18) storage scale, so elimination rounding stays far below
# anything that can survive persistence or reporting quantization.
SOLVER_PRECISION = 60

CODE_SINGULAR = "INTERNAL_PRODUCT_FLOW_SINGULAR"
CODE_INVALID = "INTERNAL_PRODUCT_FLOW_INVALID"
CODE_DENOMINATOR_ZERO = "INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO"
CODE_SELF_REFERENCE = "INTERNAL_PRODUCT_FLOW_SELF_REFERENCE"


class LeontiefError(Exception):
    """Fail-closed solver error carrying a stable blocking code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True, slots=True)
class InternalFlow:
    """One directed internal product flow (supplier output consumed by a consumer)."""

    consumer_product_profile_version_id: uuid.UUID
    supplier_product_profile_version_id: uuid.UUID
    quantity_tonnes: Decimal


@dataclass(frozen=True, slots=True)
class LeontiefSystem:
    """Deterministically ordered ``I - A`` system for one binding."""

    order: tuple[uuid.UUID, ...]
    index: dict[uuid.UUID, int]
    a_matrix: tuple[tuple[Decimal, ...], ...]
    identity_minus_a: tuple[tuple[Decimal, ...], ...]

    @property
    def size(self) -> int:
        return len(self.order)

    def is_zero_matrix(self) -> bool:
        return all(value == ZERO for row in self.a_matrix for value in row)


def order_profiles(profile_ids: Iterable[uuid.UUID]) -> tuple[uuid.UUID, ...]:
    """Deterministic row/column order: stable sort by the profile UUID string."""
    return tuple(sorted(set(profile_ids), key=str))


def build_system(
    *,
    profile_ids: Iterable[uuid.UUID],
    denominators: dict[uuid.UUID, Decimal],
    flows: Sequence[InternalFlow],
) -> LeontiefSystem:
    """Assemble ``A`` and ``I - A`` from the internal flows of one binding.

    Marketed and non-CBAM quantities never enter ``A`` (workbook L27/L41) and purchased
    precursors are outside the internal product matrix entirely.
    """
    order = order_profiles(profile_ids)
    index = {profile_id: position for position, profile_id in enumerate(order)}
    size = len(order)
    matrix: list[list[Decimal]] = [[ZERO] * size for _ in range(size)]

    with localcontext() as ctx:
        ctx.prec = SOLVER_PRECISION
        for flow in flows:
            consumer = index.get(flow.consumer_product_profile_version_id)
            supplier = index.get(flow.supplier_product_profile_version_id)
            if consumer is None or supplier is None:
                raise LeontiefError(CODE_INVALID, "Internal flow references an unknown product.")
            if consumer == supplier:
                raise LeontiefError(CODE_SELF_REFERENCE, "A process cannot consume its own output.")
            if flow.quantity_tonnes < ZERO:
                raise LeontiefError(CODE_INVALID, "Internal flow quantity cannot be negative.")
            denominator = denominators.get(flow.consumer_product_profile_version_id)
            if denominator is None or denominator <= ZERO:
                raise LeontiefError(
                    CODE_DENOMINATOR_ZERO,
                    "Consumer produced quantity must be positive.",
                )
            matrix[consumer][supplier] += flow.quantity_tonnes / denominator

        identity_minus_a = [
            [
                (ONE - matrix[row][column]) if row == column else -matrix[row][column]
                for column in range(size)
            ]
            for row in range(size)
        ]

    return LeontiefSystem(
        order=order,
        index=index,
        a_matrix=tuple(tuple(row) for row in matrix),
        identity_minus_a=tuple(tuple(row) for row in identity_minus_a),
    )


def solve(
    matrix: Sequence[Sequence[Decimal]],
    right_hand_sides: Sequence[Sequence[Decimal]],
) -> tuple[tuple[Decimal, ...], ...]:
    """Gaussian elimination with partial pivoting for one or more right-hand sides.

    ``right_hand_sides`` is a sequence of column vectors; the return value keeps the same
    order. An exactly-zero pivot raises :class:`LeontiefError` — the system is singular
    and no pseudo-inverse is attempted.
    """
    size = len(matrix)
    for row in matrix:
        if len(row) != size:
            raise LeontiefError(CODE_INVALID, "Coefficient matrix must be square.")
    for column in right_hand_sides:
        if len(column) != size:
            raise LeontiefError(CODE_INVALID, "Right-hand side length must match the matrix.")
    if size == 0:
        return tuple(() for _ in right_hand_sides)

    with localcontext() as ctx:
        ctx.prec = SOLVER_PRECISION
        working = [
            [Decimal(value) for value in row]
            + [Decimal(column[position]) for column in right_hand_sides]
            for position, row in enumerate(matrix)
        ]
        width = size + len(right_hand_sides)

        for pivot_index in range(size):
            pivot_row = max(
                range(pivot_index, size),
                key=lambda candidate: abs(working[candidate][pivot_index]),
            )
            if working[pivot_row][pivot_index] == ZERO:
                raise LeontiefError(
                    CODE_SINGULAR,
                    "The internal product-flow matrix (I - A) is singular.",
                )
            if pivot_row != pivot_index:
                working[pivot_index], working[pivot_row] = (
                    working[pivot_row],
                    working[pivot_index],
                )
            pivot = working[pivot_index][pivot_index]
            for row_index in range(pivot_index + 1, size):
                factor = working[row_index][pivot_index] / pivot
                if factor == ZERO:
                    continue
                for column_index in range(pivot_index, width):
                    working[row_index][column_index] -= factor * working[pivot_index][column_index]

        solutions: list[list[Decimal]] = [[ZERO] * size for _ in right_hand_sides]
        for rhs_index in range(len(right_hand_sides)):
            column_offset = size + rhs_index
            for row_index in range(size - 1, -1, -1):
                accumulator = working[row_index][column_offset]
                for column_index in range(row_index + 1, size):
                    accumulator -= (
                        working[row_index][column_index] * solutions[rhs_index][column_index]
                    )
                pivot = working[row_index][row_index]
                if pivot == ZERO:
                    raise LeontiefError(
                        CODE_SINGULAR,
                        "The internal product-flow matrix (I - A) is singular.",
                    )
                solutions[rhs_index][row_index] = accumulator / pivot

    return tuple(tuple(column) for column in solutions)


def solve_specific_embedded_emissions(
    *,
    system: LeontiefSystem,
    base_direct: Sequence[Decimal],
    base_indirect: Sequence[Decimal],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    """Solve ``(I - A) · SEE = base`` for the direct and indirect base vectors."""
    direct, indirect = solve(system.identity_minus_a, (base_direct, base_indirect))
    return direct, indirect


__all__ = [
    "CODE_DENOMINATOR_ZERO",
    "CODE_INVALID",
    "CODE_SELF_REFERENCE",
    "CODE_SINGULAR",
    "SOLVER_PRECISION",
    "InternalFlow",
    "LeontiefError",
    "LeontiefSystem",
    "build_system",
    "order_profiles",
    "solve",
    "solve_specific_embedded_emissions",
]
