# Domain Brief - RCM Denial Triage Assistant

## ERA (Electronic Remittance Advice)
An ERA is the electronic document that insurance companies like Aetna, Cigna, and UHC send 
back to healthcare providers after processing a claim. It explains what got paid, what got 
denied, what was adjusted, and what the patient owes. Think of it as a detailed receipt for 
a healthcare claim.

## 835 Transaction Format
The 835 is the HIPAA-standard EDI file format used to transmit ERA data electronically. 
ERA is the information, 835 is the format carrying it. CMS notes that the 835 is a wire 
transmission format — it is not meant to be used directly in application code, which is why 
this project starts with simplified CSV/JSON and adds 835 parsing in Week 4. In a raw 835 
file, segments are separated by a tilde (~) and fields within a segment are separated by 
an asterisk (*).

## Key 835 Segments

### CLP (Claim Payment Information)
The CLP segment is the claim-level summary in an 835 file. It contains the claim ID, how 
much was billed, how much was paid, how much was denied, and the claim status code 
(1 = paid, 4 = denied). Everything underneath a CLP segment belongs to that specific claim.

### CAS (Claim Adjustment Segment)
The CAS segment is where the actual denial codes live. It contains the group code (like CO 
or PR), the CARC code explaining why the claim was adjusted, and the dollar amount that was 
adjusted. One CLP can have multiple CAS segments if there are multiple adjustment reasons.

### SVC (Service Line Information)
The SVC segment represents a single service line — one specific procedure that was billed. 
It contains the procedure code (like 99213), any modifiers (like 25), the amount billed, 
and the amount paid. A single claim (CLP) can have multiple SVC segments if multiple 
procedures were performed on the same visit.

### LQ (Remittance Advice Remark Code)
The LQ segment carries the RARC code — the extra detail that supplements the CARC. For 
example, LQ*HE*MA130 means the remark code is MA130, which gives more specific information 
about why the claim was denied on top of what the CARC already said.

### DTM (Date Segment)
The DTM segment provides date information. DTM*472 indicates the service date — the date 
the medical procedure was performed.

### NM1 (Name Segment)
The NM1 segment provides name and identifier information. In a real 835, this contains 
patient name and member ID, which is PHI. In this project all NM1 data is synthetic.

## CARC (Claim Adjustment Reason Code)
CARCs explain why a claim payment was changed. If insurance reduces or denies a payment, 
the CARC gives the official reason. Common examples:
- CARC 16 = claim missing information
- CARC 50 = service not medically necessary
- CARC 97 = service bundled with another procedure
- CARC 1 = deductible amount

## RARC (Remittance Advice Remark Code)
RARCs give extra detail on top of the CARC. If the CARC says why the claim was denied, 
the RARC says specifically what needs to be fixed. Example: CARC 16 + RARC MA130 together 
mean the claim was denied because of an incomplete procedure code.

## Group Codes
Group codes tell you who is financially responsible for the adjustment:
- CO (Contractual Obligation) — the provider writes it off, cannot bill the patient
- PR (Patient Responsibility) — the patient owes it (deductible, copay, coinsurance)
- OA (Other Adjustment) — other adjustments not fitting CO or PR
- PI (Payer Initiated) — payer-initiated reduction

## Claim-Level vs Service-Line Denial
A service-line denial means insurance denies only one specific service on a claim while 
still paying the other services. For example, they could pay for an office visit (99213) 
but deny a flu shot (90686) on the same claim. A claim-level denial means the entire claim 
is rejected and none of the services get paid.

## PHI (Protected Health Information)
PHI is any data that can identify a patient — names, dates of birth, medical record numbers, 
insurance IDs. HIPAA protects all of this. Sending real PHI to an LLM API would be a HIPAA 
violation and could result in significant fines. All patient identifiers in this project are 
synthetic (MOCK001, PAT-SYN-001, etc.).

## Walking Through a Denial (Raw Input to Recommendation)
1. A provider submits a claim to insurance
2. Insurance processes it and sends back an 835 file
3. The 835 contains a CLP segment (claim summary) with CAS (denial codes) and LQ (remarks)
4. Our parser extracts the CLP, CAS, and LQ data into a normalized denial row
5. The CARC/RARC lookup maps the codes to plain English meanings
6. The policy retriever finds relevant payer policy text for that denial type
7. The rules engine provides a deterministic recommended action
8. The LLM reasoner generates a structured explanation grounded in the retrieved evidence
9. The output report shows parsed facts, code meanings, policy evidence, and recommended action