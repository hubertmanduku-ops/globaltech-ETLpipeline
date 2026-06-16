# The Business Problem We Are Solving

**Company:** GlobalTech Solutions
**Team:** Data Engineering
**Your role:** Junior Data Engineer — first week on the job

GlobalTech Solutions is a technology company with 1,200 employees
across 8 departments: Engineering, Sales, Marketing, Finance, HR,
Operations, Data Science, and Product.

The HR Analytics team wants to answer questions like:

- Which departments have the highest salary inequity?
- Who is at risk of leaving in the next 6 months?
- Are high performers being paid fairly compared to their peers?

The data exists in a PostgreSQL database. But there is a problem.
After running the SQL extraction (Module 03), the raw data has:

- **Null values** — some employee records are incomplete
- **Duplicate rows** — a join error in the SQL created copies
- **Wrong types** — some salary values are stored as text strings
- **Outliers** — a few salaries are entered incorrectly (negative values)

**Before anyone can analyse this data or train a model on it,
it must be cleaned, validated, and standardised.**

That is our job this module.

## What We Are Building

An ETL (Extract, Transform, Load) pipeline that takes raw, messy data
and produces a clean, reliable, analysis-ready output.

"""
raw-data.csv  (messy)
     │
     ▼
┌─────────────────────┐
│   DataValidator      │  — checks quality, reports problems
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│   DataTransformer    │  — fixes nulls, duplicates, types, adds flags
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│   ETLPipeline        │  — orchestrates everything, saves output
└─────────────────────┘
     │
     ▼
processed-data.csv  (clean, ready for analysis and ML)
"""
