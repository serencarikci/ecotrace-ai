# 7. Direct emissions (stationary combustion)

**Previous:** [Activities](06-activities.md) · **Next:** [Indirect emissions](08-indirect-emissions.md)

## Purpose

Calculate **fossil CO₂** from stationary combustion (fuel burning) for eligible fuel-use activities.

## Who can use it

View results: **view** access. Calculate: **edit** access on a writable period.

## What must be completed first

- Fuel-use activity records in Activities  
- Fuel catalog parameters available for the fuel code

## How to open

Period detail → tab **Direct Emissions**.

![Direct Emissions tab](assets/07-direct-emissions.png)

## Sections

- Activity coverage list (ready / missing / out of date)  
- Calculate form  
- Current / history results  
- Period summary totals  

## Calculate fields

| Label | Required | Notes |
|-------|----------|-------|
| Fuel use record | Yes | Eligible activity from the coverage list |
| Calculation date | Yes | Date used to pick valid parameters |
| Density | Conditional | Required for volume fuels (for example natural gas); no silent default |
| Density unit | Conditional | Together with density |

## What the system calculates (plain language)

From fuel quantity, density (if needed), net calorific value, fossil CO₂ factor, and oxidation factor, the system stores a fixed result in **tCO₂** (some screens may show tCO₂e for the same fossil CO₂ value).

Values after Calculate are a **saved snapshot**. If you change the activity later, the current result can become **out of date** until you calculate again.

## Actions

| Action | Meaning |
|--------|---------|
| Calculate | Create a new saved result |
| Calculate again / Update | New run; older results stay in history |
| Open detail | Inspect saved inputs and outputs |
| Retry | Reload after a failed request |

## Status badges

| Badge | Meaning |
|-------|---------|
| Current | Active result for this activity |
| History | Older successful result |
| Out of date | Inputs changed; calculate again |
| Failed | Run did not produce a usable result |

## Common errors

| Message / situation | Fix |
|---------------------|-----|
| Density required | Enter density for a volume fuel |
| Factor / parameter unresolved | Check fuel catalog and date |
| Permission | Need edit access |
| Unit incompatible | Fix the activity unit |

## Where to go next

[Indirect emissions](08-indirect-emissions.md), then allocate on the Allocation tab.

## Example

Select the natural gas activity, set density `0.68`, calculate, confirm Current result and period total.

## Inventories

Field and action lists: [inventories/](inventories/).
