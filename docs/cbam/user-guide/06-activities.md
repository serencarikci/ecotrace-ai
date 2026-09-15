# 6. Activities

**Previous:** [Production](05-production.md) · **Next:** [Direct emissions](07-direct-emissions.md)

## Purpose

Enter measured activity data such as fuel use and purchased electricity. Later calculation screens select eligible activity rows.

## Who can use it

View: **view** access. Create, archive, and properties: **edit** access on a writable period.

## How to open

Period detail → tab **Activities**.

![Activities tab](assets/06-activities.png)

## Fields

| Label | Required | Notes |
|-------|----------|-------|
| Activity Type | Yes | For example fuel use or electricity |
| Installation | As shown | Scope of the activity |
| Quantity | Yes | Measured amount |
| Unit | Yes | Must match the activity type rules |
| Date | Yes | Inside the reporting period |
| Source Reference | Optional | Link to evidence |
| Measurement Method | Optional | How it was measured |
| Notes | Optional | Free text |

## Actions

- Create activity  
- Archive activity  
- Manage **properties** (extra details used when factors are resolved)

## Tips

- Natural gas recorded as volume later needs **density** on the Direct Emissions screen.  
- Electricity activities are selected on the Indirect Emissions screen.  
- Creating activities here does **not** calculate emissions by itself.

## Common errors

| Situation | Fix |
|-----------|-----|
| Unit does not match | Choose a unit allowed for that activity type |
| Period locked | View only — ask to unlock or use another period |
| Permission | Need edit access |

## Where to go next

[Direct emissions](07-direct-emissions.md) for fuel, then [Indirect emissions](08-indirect-emissions.md) for electricity.

## Example

Add a natural gas fuel-use activity in Nm³ and an electricity activity in kWh for the same months as production.

## Inventories

Field and action lists: [inventories/](inventories/).
