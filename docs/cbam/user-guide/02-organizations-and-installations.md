# 2. Organizations and installations

**Previous:** [Getting started](01-getting-started.md) · **Next:** [Reporting periods](03-reporting-periods.md)

## Purpose

An **organization** is your company in EcoTrace. An **installation** is the plant or site used for CBAM reporting.

## Who can use it

- View list and detail: **view** access
- Create, edit, activate, archive: **edit** access

## What must be completed first

- Signed in
- Organization selected

## How to open

- Organizations: shared platform screen under Organizations
- Installations list: SKDM → **Installations**
- New installation: **New installation**
- Detail: open a row in the list

![Organizations list](assets/03-organizations.png)

![Installations list](assets/04-installations-list.png)

![Installation detail](assets/05-installation-detail.png)

## Page sections

### Installations list

- Search and status filter
- Table of installations
- **New installation** (edit access only)

### New / edit form

| Label | Required | Optional | Notes |
|-------|----------|----------|-------|
| Facility | Yes (create) | | Links the CBAM installation to a facility in the platform |
| Code | Yes | | Stable code for the installation |
| Name | Yes | | Display name |
| Timezone | Yes | | Used when reading dates |
| Operator ID | | Yes | Optional operator identifier |

### Detail actions

| Action | Who | Result |
|--------|-----|--------|
| Save | edit | Updates name, timezone, operator |
| Activate | edit | Sets status to active (when allowed) |
| Archive | edit | Archives the installation |

## Validation

- Required fields must be filled before Save.
- Do not use archived installations for new period work.

## Where to go next

Open [Reporting periods](03-reporting-periods.md) and create a draft period for this installation.

## Example

Create installation **LOCAL CBAM Review — Steel Screws & Nuts** linked to the demo facility, timezone Europe/Istanbul.

## Inventories

Field and action lists: [inventories/](inventories/).
