# 9. Processes

**Previous:** [Indirect emissions](08-indirect-emissions.md) · **Next:** [Purchased inputs and precursors](10-purchased-inputs-and-precursors.md)

## Purpose

Define **conventional production processes** and how produced quantity is shared across CBAM products, non-CBAM use, and optional heat / waste gas / exported electricity inputs.

## Who can use it

View: **view** access. Create, edit, archive: **edit** access on a writable period.

## What must be completed first

- Product profiles and production context  
- Prefer current direct and indirect results for the read-only allocated values shown on the process  

## How to open

Period detail → tab **Processes**.

![Processes tab](assets/09-processes.png)

## Process header fields

| Label | Required | Notes |
|-------|----------|-------|
| Installation | Yes | Process site |
| Process name | Yes | Display name |
| Process identifier | Optional / as shown | External id |
| Product profile | Linked via uses | Targets for distribution |
| Produced quantity / Unit | Yes | Process output quantity |

## Product distribution

You split produced quantity into:

- Quantity marketed / assigned to a CBAM product profile  
- Quantity used in another CBAM product (internal flow)  
- Non-CBAM quantity  

Drafts can save while **unbalanced**. Readiness stays blocked until remaining quantity is exactly zero.

## Conditional inputs

| Area | When shown | Meaning |
|------|------------|---------|
| Measurable heat | Heat flags enabled | Imported / exported heat amounts and factors |
| Waste gas | Waste gas flags enabled | Imported / exported waste gas |
| Exported electricity | Enabled | Process-level exported electricity quantity, factor, and evidence (feeds product results) |

Controlled lists (factor source, documents, and similar) come from the server.

## Read-only displays

- Allocated direct emissions / electricity from current allocation results when available  
- Links back to Allocation when values are missing or out of date  

## Not supported here

- Process Emissions calculation method  
- Mass Balance calculation method  

Only **Conventional** processes are implemented in the UI.

## Where to go next

[Purchased inputs and precursors](10-purchased-inputs-and-precursors.md).

## Example

Create process “Steel finishing”, distribute 100% of tonnes across screw and nut profiles with zero remaining.

## Inventories

Field and action lists: [inventories/](inventories/).
