# Legacy Office conversion - final status (2026-10-22)

## Final result: complete, zero failures

- Converted: **20** | already had twins: **393** | failed: **0**
- Total legacy files: 413 (.doc 266, .xls 90, .ppt 57) - every one now has a modern twin.
- Originals were never modified or deleted.

## History: first run failed 20 files, retry succeeded

The first full run (06:23-07:01) reported 20 failures:

- 18x Excel "This command is unavailable because the license to use this application has expired"
- 2x RPC_E_CALL_REJECTED (Excel busy - Value Steam Worksheet Assignment 1.xls, Value Stream VSM Template (Autosaved).xls)

A retry at 11:22-11:23 converted **all 20** (the license error did not reproduce):

- Value Steam Worksheet Assignment 1.xls
- Value Stream VSM Template (Autosaved).xls
- MasterSchedule Template.xls
- Six Sigma Calculator.xls
- fishbone diagram_template.xls
- FMEA Assignment 4.xls
- FMEA Template.xls
- Vacuum Breaker Insulation Resistance.xls
- A101 (SIGNED) Annual Service v2 0.xls
- A104 (SIGNED) Annual Service v2 0.xls
- Generator Vacuum Test insulation resistance groupings.xls
- SIPOC Template.xls
- 8_Run_DOE_Template.xls
- Financial Functions.xls
- Prob18-5-cell design for final.xls
- Automated Combat Engineer Calculator.xls

Affected files are confirmed converted by logs/convert-legacy-results.json.