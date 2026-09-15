# 13. Factors and calculations

**Previous:** [Allocation](12-allocation.md) · **Next:** [Report and Official Excel](14-report-and-official-excel.md)

## Purpose

Resolve emission factors for generic activity, purchased-input, and allocation targets, then run the generic **activity × factor** calculation used by internal Excel workflows.

## Who can use it

View: **view** access. Resolve and execute: **edit** access on a writable period.

## How to open

Period detail → tab **Factors** or **Calculation**.

![Factors tab](assets/13-factors.png)

![Calculation tab](assets/13b-calculation.png)

## Factors tab

| Action | Meaning |
|--------|---------|
| Resolve / Resolve Again | Ask the server to pick primary or default factor values |
| Save Primary Value | Store a primary override where allowed |

### Status labels (user-facing)

| Label | Meaning |
|-------|---------|
| Primary Data Used | Primary value applied |
| Default Reference Used | Catalog default applied |
| Not Resolved / More Than One Match | Fix inputs or choose explicitly |
| Unit Does Not Match | Fix units |

## Calculation tab

| Action | Meaning |
|--------|---------|
| Create / execute calculation run | Runs the supported multiply activity × factor formula |
| Recalculate result | New saved result row |

### Result status labels

Calculated · Blocked · Invalid Input · Unit Does Not Match · Factor Not Resolved · …

## Important distinction

| Path | Used for |
|------|----------|
| Direct / Indirect / Product Results tabs | Modern CBAM fuel, electricity, product embedded emissions, Official Excel |
| Factors + Calculation tabs | Generic factor resolution + internal calculation/export path |

Do not confuse generic calculation totals with Official Excel product embedded emissions.

## Where to go next

[Report and Official Excel](14-report-and-official-excel.md).

## Inventories

Field and action lists: [inventories/](inventories/).
