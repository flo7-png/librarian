# Librarian — NEEDS_REVIEW documents (with actual errors)

Generated: 2026-10-22 11:44 | count: 23

Sources: `documents.error_message` (what the worker stored), plus a fresh
re-run of the real extractor (`app.extract.extract_text`) per file to
capture the underlying error the worker never persisted.

## Summary by cause

- lock file: 12
- extraction threw: 7
- 0 chars extracted: 2
- empty file: 2

## Files

### 1. College/East Carolina Univeristy/ITEC 6005 Lean Enterprise/Module 2/ITEC 6005 Project Annex 2.xlsx
- Full path: `D:\References\College\East Carolina Univeristy\ITEC 6005 Lean Enterprise\Module 2\ITEC 6005 Project Annex 2.xlsx`
- Size: 337375 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ITEC 6005 Project Annex 2.xlsx: error, 0 chars, quality=0.00

### 2. College/East Carolina Univeristy/ITEC 6110 Quality Planning and Analysis/Assignment 4/Inserts for Assignment 4.pptx
- Full path: `D:\References\College\East Carolina Univeristy\ITEC 6110 Quality Planning and Analysis\Assignment 4\Inserts for Assignment 4.pptx`
- Size: 178343 B | chars (worker): 0 | quality: 0.00 | parser: native | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): parser 'native' opened the file but extracted 0 characters (images-only, placeholder, or no readable text)
- Re-run detail: method=native, pages=2, chars=0, confidence=0.00
- Worker event: Extracted Inserts for Assignment 4.pptx: native, 0 chars, quality=0.00

### 3. College/East Carolina Univeristy/ITEC 6112 Design of Experiments/Power Point Lectures/3.factorial.experiments (1).pdf
- Full path: `D:\References\College\East Carolina Univeristy\ITEC 6112 Design of Experiments\Power Point Lectures\3.factorial.experiments (1).pdf`
- Size: 131072 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): (none)
- Actual error (re-run): extraction threw: Unexpected EOF
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted 3.factorial.experiments (1).pdf: error, 0 chars, quality=0.00

### 4. College/East Carolina Univeristy/ITEC 6112 Design of Experiments/Power Point Lectures/3.factorial.experiments.pdf
- Full path: `D:\References\College\East Carolina Univeristy\ITEC 6112 Design of Experiments\Power Point Lectures\3.factorial.experiments.pdf`
- Size: 131072 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Duplicate of College/East Carolina Univeristy/ITEC 6112 Design of Experiments/Power Point Lectures/3.factorial.experiments (1).pdf (same SHA-256)
- Actual error (re-run): extraction threw: Unexpected EOF
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted 3.factorial.experiments.pdf: error, 0 chars, quality=0.00

### 5. College/East Carolina Univeristy/ITEC 6407 CIM & automation/ITEC 6407 Project proposal.docx
- Full path: `D:\References\College\East Carolina Univeristy\ITEC 6407 CIM & automation\ITEC 6407 Project proposal.docx`
- Size: 14381 B | chars (worker): 0 | quality: 0.00 | parser: native | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): parser 'native' opened the file but extracted 0 characters (images-only, placeholder, or no readable text)
- Re-run detail: method=native, pages=1, chars=0, confidence=0.00
- Worker event: Extracted ITEC 6407 Project proposal.docx: native, 0 chars, quality=0.00

### 6. College/Prime Power School/Electrical Systems Engineering/AE-01/AE-01 Introduction to Electrical Engineering(3).pptx
- Full path: `D:\References\College\Prime Power School\Electrical Systems Engineering\AE-01\AE-01 Introduction to Electrical Engineering(3).pptx`
- Size: 955177 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: Bad CRC-32 for file 'ppt/slideLayouts/slideLayout12.xml'
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted AE-01 Introduction to Electrical Engineering(3).pptx: error, 0 chars, quality=0.00

### 7. College/Prime Power School/Electrical Systems Engineering/AE-02/AE-02.cs.docx
- Full path: `D:\References\College\Prime Power School\Electrical Systems Engineering\AE-02\AE-02.cs.docx`
- Size: 18319 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: Bad CRC-32 for file 'word/endnotes.xml'
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted AE-02.cs.docx: error, 0 chars, quality=0.00

### 8. College/UoP/UoP/~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx
- Full path: `D:\References\College\UoP\UoP\~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Duplicate of College/UoP/~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx (same SHA-256)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx: error, 0 chars, quality=0.00

### 9. College/UoP/UoP/~$M 595 Week 4 Compensation and Benefits Recommendations Report Jacqueline Florentino 3May21.docx
- Full path: `D:\References\College\UoP\UoP\~$M 595 Week 4 Compensation and Benefits Recommendations Report Jacqueline Florentino 3May21.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$M 595 Week 4 Compensation and Benefits Recommendations Report Jacqueline Florentino 3May21.docx: error, 0 chars, quality=0.00

### 10. College/UoP/UoP/~$R 581 Week 4 Airbnb Case Study Jacqueline Florentino 26Jul21.docx
- Full path: `D:\References\College\UoP\UoP\~$R 581 Week 4 Airbnb Case Study Jacqueline Florentino 26Jul21.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$R 581 Week 4 Airbnb Case Study Jacqueline Florentino 26Jul21.docx: error, 0 chars, quality=0.00

### 11. College/UoP/UoP/~$STR 581 Signature Assignment Week 6 Jacqueline Florentino 7Aug21.pptx
- Full path: `D:\References\College\UoP\UoP\~$STR 581 Signature Assignment Week 6 Jacqueline Florentino 7Aug21.pptx`
- Size: 165 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): (none)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$STR 581 Signature Assignment Week 6 Jacqueline Florentino 7Aug21.pptx: error, 0 chars, quality=0.00

### 12. College/UoP/UoP/~$STR 581 Week 5 Business Plan Assessment Jacqueline Florentino 2Aug21.pptx
- Full path: `D:\References\College\UoP\UoP\~$STR 581 Week 5 Business Plan Assessment Jacqueline Florentino 2Aug21.pptx`
- Size: 165 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Duplicate of College/UoP/UoP/~$STR 581 Signature Assignment Week 6 Jacqueline Florentino 7Aug21.pptx (same SHA-256)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$STR 581 Week 5 Business Plan Assessment Jacqueline Florentino 2Aug21.pptx: error, 0 chars, quality=0.00

### 13. College/UoP/~$C561 Accounting Methods Week 2 Jacqueline Florentino 20May19.docx
- Full path: `D:\References\College\UoP\~$C561 Accounting Methods Week 2 Jacqueline Florentino 20May19.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$C561 Accounting Methods Week 2 Jacqueline Florentino 20May19.docx: error, 0 chars, quality=0.00

### 14. College/UoP/~$M  546 Week 1 Advirosry Memo Employment Issues Jacqueline Florentino 20 Jul 2020.docx
- Full path: `D:\References\College\UoP\~$M  546 Week 1 Advirosry Memo Employment Issues Jacqueline Florentino 20 Jul 2020.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$M  546 Week 1 Advirosry Memo Employment Issues Jacqueline Florentino 20 Jul 2020.docx: error, 0 chars, quality=0.00

### 15. College/UoP/~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx
- Full path: `D:\References\College\UoP\~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): (none)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$M  546 Week 4 Advirosry Jacqueline Florentino 11 Aug 2020.docx: error, 0 chars, quality=0.00

### 16. College/UoP/~$M595 Week 1 Application Case Jacqueline Florentino 12April21.docx
- Full path: `D:\References\College\UoP\~$M595 Week 1 Application Case Jacqueline Florentino 12April21.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$M595 Week 1 Application Case Jacqueline Florentino 12April21.docx: error, 0 chars, quality=0.00

### 17. College/UoP/~$N571 Using the Payback Method IRR and NPV Memo Week 3 Jacqueline Florentino 11Nov19.docx
- Full path: `D:\References\College\UoP\~$N571 Using the Payback Method IRR and NPV Memo Week 3 Jacqueline Florentino 11Nov19.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$N571 Using the Payback Method IRR and NPV Memo Week 3 Jacqueline Florentino 11Nov19.docx: error, 0 chars, quality=0.00

### 18. College/UoP/~$T571 Week 6 Social, Eithical, and Legal Implications Jacqueline Florentino 10Mar20.docx
- Full path: `D:\References\College\UoP\~$T571 Week 6 Social, Eithical, and Legal Implications Jacqueline Florentino 10Mar20.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$T571 Week 6 Social, Eithical, and Legal Implications Jacqueline Florentino 10Mar20.docx: error, 0 chars, quality=0.00

### 19. College/UoP/~$m 548 Week 4 Background Check Analysis Jacqueline Florentino 2Nov2020.docx
- Full path: `D:\References\College\UoP\~$m 548 Week 4 Background Check Analysis Jacqueline Florentino 2Nov2020.docx`
- Size: 162 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ~$m 548 Week 4 Background Check Analysis Jacqueline Florentino 2Nov2020.docx: error, 0 chars, quality=0.00

### 20. Electrical/PROPONENT’S ENVIRONMENTAL ASSESSMENT.pdf
- Full path: `D:\References\Electrical\PROPONENT’S ENVIRONMENTAL ASSESSMENT.pdf`
- Size: 8388608 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: Unexpected EOF
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted PROPONENT’S ENVIRONMENTAL ASSESSMENT.pdf: error, 0 chars, quality=0.00

### 21. Military Construction Manuals/ERDC Base Camp Tools 2017.pptx
- Full path: `D:\References\Military Construction Manuals\ERDC Base Camp Tools 2017.pptx`
- Size: 3399680 B | chars (worker): 0 | quality: 0.00 | parser: error | ocr: NOT_NEEDED
- Stored error (DB): Quality score: 0.00 (threshold: 0.35)
- Actual error (re-run): extraction threw: File is not a zip file
- Re-run detail: method=error, pages=0, chars=0, confidence=0.00
- Worker event: Extracted ERDC Base Camp Tools 2017.pptx: error, 0 chars, quality=0.00

### 22. My Military Medical Information/VGLI.md
- Full path: `D:\References\My Military Medical Information\VGLI.md`
- Size: 0 B | chars (worker): 0 | quality: 0.00 | parser: native | ocr: NOT_NEEDED
- Stored error (DB): (none)
- Actual error (re-run): file is empty (0 bytes on disk) — nothing to extract
- Re-run detail: method=native, pages=1, chars=0, confidence=0.00
- Worker event: Extracted VGLI.md: native, 0 chars, quality=0.00

### 23. Old AI References (Claude, Gemini)/AI Conversion/Gemini/Untitled.md
- Full path: `D:\References\Old AI References (Claude, Gemini)\AI Conversion\Gemini\Untitled.md`
- Size: 0 B | chars (worker): 0 | quality: 0.00 | parser: native | ocr: NOT_NEEDED
- Stored error (DB): Duplicate of My Military Medical Information/VGLI.md (same SHA-256)
- Actual error (re-run): file is empty (0 bytes on disk) — nothing to extract
- Re-run detail: method=native, pages=1, chars=0, confidence=0.00
- Worker event: Extracted Untitled.md: native, 0 chars, quality=0.00
