# ZentroMart / VoiceOps 2026: dataset deep analysis (read-only)

Sources: I read `C:/Users/shres/Downloads/Capstone_Project_Dataset_FTTT_2026.zip` in memory with `python -I` and zipfile. I extracted nothing and wrote no files. I also read `C:\Users\shres\OneDrive\Documents\capstone_AI_ML\6ad64c83eae85_voiceops_2026_capstone_brief.pdf` (14 pages). Reference date is 2026-10-20 (Tuesday). The 2026 holidays are 08-15, 10-02, 10-19 (Mon) and 11-09.

---

## 1. Date arithmetic (all practice gold dates reproduce)

```python
H={date(2026,8,15),date(2026,10,2),date(2026,10,19),date(2026,11,9)}
isbd=lambda d: d.weekday()!=6 and d not in H          # Mon-Sat minus holidays
def addbd(d,n):                                         # day 1 = next business day after d
    while n>0:
        d+=timedelta(1)
        if isbd(d): n-=1
    return d
SLA={'upi':(1,3),'card':(5,7),'netbanking':(3,5),'cod_bank':(5,7),'wallet':(0,0),'cod_wallet':(0,0)}
```

| Case (source) | Initiated | Computed min–max | Gold | Result |
|---|---|---|---|---|
| card (PQ0008/PQ0022) | 10-17 Sat | 10-24 – **10-27** | 2026-10-27 | PASS |
| netbanking (PQ0028) | 10-14 Wed | 10-17 – **10-21** | 2026-10-21 | PASS |
| UPI (PQ0027) | 10-12 Mon | 10-13 – **10-15** | 2026-10-15 | PASS |
| card (PQ0029) | 10-12 | 10-17 – **10-21** | 2026-10-21 | PASS |
| netbanking (PQ0033/PQ0052) | 10-17 | 10-22 – **10-24** | 2026-10-24 | PASS |
| netbanking (PQ0035) | 10-12 | 10-15 – **10-17** | 2026-10-17 | PASS |
| UPI (PQ0059) | 10-17 | 10-20 – **10-22** | 2026-10-22 | PASS |
| UPI, PC010 note | 07-20 | 07-21 – **07-23** | max 2026-07-23 | PASS |

- **Convention:** the initiation day is NOT counted. Day 1 is the first business day after initiation. Sundays and holidays are skipped both as day 1 and as later days; for example, the 10-17 UPI refund skips 10-18 (Sun) and 10-19 (holiday), so day 1 is 10-20. Counting the initiation day as day 1 fails every case. The min dates in `reference_answer` (24 Oct, 17 Oct, 13 Oct, 22 Oct, 15 Oct, 20 Oct) also match `addbd(d, lo)`.
- **must_include holds only the MAX date.** The reference answer gives the range "between MIN and MAX". Say both, with the year.
- **Return deadline:** `delivered_on + N calendar days`, and the last day is included.
  - PC003: delivered 10-12, fashion 15 days, deadline 2026-10-27.
  - PC004: delivered 10-14, festive 30 days, deadline 2026-11-13.
  - The customer is eligible if `today <= deadline`. 30 delivered item-lines have their deadline exactly on 2026-10-20, so the inclusive boundary will be tested.
- **RET-8 festive rule:**
  - Applies to the `fashion` category when the `placed_at` date is between 2026-10-01 and 2026-10-15, both included.
  - The window becomes 30 days, still counted from `delivered_on`. The hour is irrelevant.
  - PC003 was placed 2026-09-30T21:42, so it is not festive and keeps 15 days.
  - Boundary orders that contain fashion items:
    - Placed 09-30: 82580117, 18599253, 66391744, 42256577.
    - Placed 10-15: 46850933, 33986432, 78670043, 28372489.
    - Placed 10-16: 46662050, 63671912, 58426045, 82902610.
  - 82 orders contain fashion items placed inside the window.
- **RET-3:** an `electronics` item with `delivered_on` < 2026-08-01 keeps 10 days (RETv3-2). Otherwise it gets 7 days.
  - 42 orders contain electronics delivered before Aug 1 (6 of them between Jul 22 and Jul 31). All of these windows have now expired.
  - Questions are phrased "what was the window" (PQ0019). PQ0057 and PQ0058 expect 7.
- **ESC-1 rule 5:**
  - Formula: `max = addbd(initiated, SLA_hi)`. Count `bd_past` = business days d with max < d <= today. Escalate if `bd_past > 3`, which is the same as `today > addbd(max, 3)`.
  - PC010: max 07-23, so the grace period ends 07-27 and it is overdue. Gold expects: escalate, `create_ticket()`, share RRN 315633825001, and never say "it will arrive tomorrow".
  - Boundary on 10-20 for 97378296 (RTO upi, init 10-12, max 10-15): 10-16, 10-17 and 10-20 are exactly 3 business days past. That is NOT "more than 3", so do not escalate. 57723321 (wallet, init 10-15) is the same case.
- **Other timers verified against the data:**
  - Express `promised_date` is the next business day if placed before 14:00, otherwise the second business day. 63/63 orders match.
  - Standard `promised_date` is within 3–6 business days (metro) or 5–9 business days (non-metro) of the placed date. 825/825 orders match.
  - RTO refunds are initiated 7, 8, 9 or 10 calendar days after `delivery_attempt_failed_3` (REF-1). 14/14 match.
  - Cancellation refunds are initiated the same day as `cancelled_by_customer`. 46/46 match.
  - Return refunds: Plus members get the refund at pickup. Non-Plus members get it within 2 business days of pickup, after QC. All match.

---

## 2. Reasoning patterns and traps the hidden test set is likely to probe

46 of the 84 section IDs never appear in practice gold. The hidden test set probably covers some of them: KB-00.2/.4, STY-2..5, ESC-2, IDV-1, FAQ-1..4, FAQH-2, FAQH-4, RVP-1..3, TRK-2, TRB-1..3, MKT-1, CAN-3, CAN-4, CPN-2, CPN-3, DWM-4, DWM-5, DEL-1, DEL-2, DEL-6, MKS-1..3, PAY-1..4, PLS-1, PLS-3, REF-4, REF-5, RETv3-6, RET-1, RET-9, WAR-3.

### A. Source precedence (KB-00.1: policy > agent guide > help > FAQ > marketing; superseded docs only cover what their successor allows)

| Trap | Losing source | Winning rule |
|---|---|---|
| Generic refund time | FAQ-1 "5 to 7 days" | REF-2 per method: UPI 1–3 bd, card 5–7 bd, netbanking 3–5 bd, wallet instant (2 h), COD-NEFT 5–7 bd after bank verification (REF-3). Cite `REF-2 ; KB-00.1`. FAQ-1 is a hard negative, and the MNI blocks "5 to 7 days"/"5-7 days" for UPI, netbanking and wallet. |
| Delivery fee | FAQ-3 "free on most orders" | DEL-2: free from ₹499 (subtotal), otherwise ₹40. Express costs ₹79, free for Plus. In the data, the ₹40 fee applies exactly when subtotal < 499 (30 orders); slot delivery is always ₹0. |
| Plus "money back faster" / "lightning-fast" | MKT-1 | PLS-2: Plus does not change windows, eligibility, or refund timelines after initiation. The only refund change is initiation at pickup. Price is ₹999 (PLS-1). |
| Free express for Plus | FAQH-4 (no qualifier) | PLS-2 and DEL-5: only where `express_available=True`. Non-metro pincodes plus Pune 411045 and Kolkata 700064 have no Express. |
| "Assured" badge | products.csv `assured=True`, WAR-2 | **MKS-3**: Assured never applies to marketplace-seller items; they get the brand warranty only. 8 SKUs are affected: ELE-0004, ELE-0009, ELE-0010, ELE-0015, ELE-0017, ELE-0018, ELE-0025, HOM-0043. |
| Electronics window | RETv3-2 10 days | RET-3 and RET-2: 7 days, unless delivered before 2026-08-01. RETv3-2 is a hard negative. |
| Free pickup for all | RETv3-6 | RET-6: ₹49 for change-of-mind fashion returns; waived for Plus members and for damaged/defective/wrong items. |
| Support logs | logs | Never authoritative (README). |

Consistent FAQs are still cited as gold for Hindi questions (`FAQH-1 ; CAN-2`, `FAQH-3 ; DWM-1`, `DEL-5 ; FAQ-5`). Retrieval must work across languages and return the FAQH chunk together with the policy chunk.

### B. Questions that need two sources (policy plus a catalog or order row)

- **Return window:** product `return_category` + RET-2 (+ RET-3/RET-8). Gold includes `products.csv:SKU` when the product is named, but not always (PQ0019, PQ0049, PQ0054, PQ0056, PQ0057 have no SKU).
- **Warranty:** WAR-1, WAR-2, products.csv (`assured`, `warranty_months`, `fulfilled_by`) and MKS-3.
  - PQ0026: ELE-0008 has 12 months Assured plus a 6-month brand warranty.
  - PQ0041: ELE-0003 has 12 months Assured plus a 12-month brand warranty.
- **Damage escalation threshold:** price > ₹10,000 (DWM-3 / ESC-1.1).
  - Above ₹10,000: ELE-0011..0014, 0020..0023, HOM-0047, HOM-0048, HOM-0049 (₹10,639).
  - Just below, so the normal DWM flow applies: ELE-0015 (₹9,629) and HOM-0050 (₹9,239).
  - It is UNVERIFIED whether a qty>1 line total counts as the item's "worth".
- **Same-name colour variants with different attributes.** Ask which colour (clarify), or cite all variants:
  - Assured status differs: Nimbus X2 Lite (0004 marketplace / 0005 ZentroMart), Voltra 20000 (0006 assured / 0007 not), Voltra 10000 (0008 / 0009 marketplace), K7 128 (0011 no / 0012 yes), K7 256 (0013 no / 0014 yes), Vista TV (0020 no / 0021 yes), USB-C cable (0024 / 0025 marketplace), Mixwell (HOM-0043 marketplace assured / HOM-0044 not assured).
  - Price threshold differs: Study Table (HOM-0049 ₹10,639 / HOM-0050 ₹9,239).
- **Gold picks one variant even when the colour is omitted.** Examples: PQ0020 tote → FSH-0038, PQ0044 bedsheet → HOM-0046, PQ0036 swimsuit → INR-0068, PQ0039 briefs → INR-0065. Hidden questions are probably made from a SKU row with the colour stripped. For recall, cite every SKU that matches the name.
- **Express or COD availability** for a pincode: pincodes.csv + DEL-5 / PAY-2 (COD up to ₹10,000, ₹25 fee).
  - Not serviceable: Leh 194101, Port Blair 744101.
  - No COD: Dehradun 248001, Shillong 793001.
- **"Why was I charged delivery?"** Check the order's `delivery_fee_inr`. Most logged customers were charged ₹0. Order 180 in the logs was an express order with ₹79, but the human agent quoted the ₹40 rule.
- **Partial refund amount (REF-4, RET-6).** The formula below reproduces 69/69 return refunds exactly:
  `refund = round_half_up(unit_price*qty − disc*price/subtotal − [disc − share if subtotal−price < coupon_min] − pickup_fee)`.
  - PC010 example: 2809 − 280.5 − 49 = 2479.5, which rounds to **2480**.
  - Cancellation refund = `total_inr` (46/46). RTO refund = `total − delivery_fee` (REF-5).

### C. Time and order-state logic

- Order status mapping for TRK-1:
  - `placed` and `packed` can still be cancelled free in My Orders (CAN-1). The agent cannot cancel; PC017 (placed) and PC018 (packed) expect decision **answer**, and the MNI is "I have cancelled / cancel kar diya".
  - `shipped` and `out_for_delivery` cannot be cancelled (CAN-2). PC019 and PC020 expect decision **refuse**: offer refuse-at-door or return, and include the "7" from REF-1 (refund starts 7–10 calendar days after the last attempt, then the payment-method SLA).
- `delivered` but customer says not received: TRK-2 (check family/neighbours, report within 48 h as missing under DWM-1). Human agents in the logs just said "delivered", which is a trap.
- Return refund status with QC pending (PC009, `return_picked_up`, pickup 10-20): must mention "quality check". Initiation within 2 business days of pickup gives **10-22**, then UPI 1–3 business days.
- Late Express delivery (DEL-4): non-Plus customers get an automatic ₹79 wallet credit within 48 h; the data has `express_late_credit_on`. Plus members get no credit. A late Standard delivery gets no compensation, and the agent must offer none.
- `delivery_attempted` (DEL-3): up to 3 attempts, then RTO and REF-1.
- RTO with refund not yet initiated: 91381064 (card; 3rd failure 10-14; refund expected to start 10-21 to 10-24, then 5–7 business days).
- RVP-2: a missed pickup moves to the next business day; after 2 misses, support can raise a priority pickup. RVP-3: item rejected at the door, customer gets an SMS with the reason.
- PAY-3: money deducted but no order means auto-reversal within 5 business days and no ticket before then.
- PAY-4: wallet balance never expires and cannot be moved to a bank (refuse).
- DEL-6: the address can only be changed before shipping.
- CAN-3: grocery slot orders can be cancelled until 2 h before the slot start. The slot time is not in the data, so ask for it (clarify).
- CAN-4: partial cancellation, with REF-4 coupon rules.
- CPN-1: one coupon only. CPN-2: a coupon that failed technically is re-issued once; an expired coupon is never re-issued.
- PLS-3: membership refund within 14 days if no benefit was used. No customer has `plus_since` within 14 days of 10-20.
- RET-9: exchanges for clothing and footwear only (not bags), subject to stock.
- RET-4: beauty items must be unopened; electronics must not be locked. RET-5: grocery, innerwear and digital are not returnable, but a damaged or wrong item goes to DWM.
- WAR-3: physical damage, liquid damage and wear are not covered.
- DWM-4: a report after 48 h becomes a normal return if within the window, otherwise warranty.
- Relative dates in speech: "parso" (day before yesterday) = 2026-10-18, "yesterday" = 10-19. "kal" can mean yesterday or tomorrow, so resolve from context.

### D. Escalation (ESC-1, with ESC-2 "create ticket first" and ESC-3 "summary fields")

1. Damaged, defective or wrong item > ₹10,000 (DWM-3). PQ0030 and PQ0046 have MNI "has been approved / I've approved / I have arranged a replacement". In PC002 the customer pushes "approve kar do": escalate with `create_ticket()`, gold `DWM-3 ; ESC-1 ; ESC-4`.
2. Order, payment or account activity the customer did not make (PQ0023).
3. Legal action, consumer court or police mentioned.
4. `contacts_last_7_days >= 2` (counts earlier contacts only). 34 orders qualify. Escalate based on the field, not on the customer's claim; PC007 and PC008 have the field at 2.
5. Refund more than 3 business days past its maximum.
6. Customer asks for a human (PC005, PC006).
7. Safety risk: swelling battery, burning smell, sparks, heat or injury (DWM-5). Tell the customer to stop using the product.

Combined trap: 48567593 is within the refund grace period but has contacts = 2, so escalate under rule 4.

### E. Refuse (ESC-4 and IDV-4)

- Another customer's data (PQ0060; MNI "+91").
- Compensation or voucher for a late Standard delivery (PC015, PC016; gold `DEL-4 ; ESC-4`; MNI "has been credited / voucher added / ₹300 has been").
- Cancelling a shipped order.
- Second failed verification (PC021, PC022).
- Policy exceptions (wallet to bank, re-issuing an expired coupon).

**Conflict:** in the brief's example the agent refuses ₹500 compensation and then creates a ticket and hands over. The practice gold for PC015/PC016 is `refuse` with no tool call. Recommendation: refuse politely and offer a human; create a ticket only if the customer asks for one. Which version the hidden scorer follows is UNVERIFIED.

### F. Clarify

- Product not named (PQ0018).
- Refund question without payment method or order (PQ0051).
- Any order-specific request without an order ID: the T1 of every conversation must introduce the assistant as an **AI** (STY-1; MI "AI / एआई") and ask for the order ID.
- Colour variant where the attribute differs.
- Grocery slot time.
- Which item, in a multi-item order (84 orders have duplicate-SKU lines, so `return_line_no` matters).

### G. Unanswerable

`answerable=False`, decision `answer`, acceptable `answer ; escalate`. MI "don't have / no information / connect / जानकारी नहीं / pata nahi / सहयोगी".

- Practice examples: midnight delivery, student discount, GST invoice on bulk orders, a store in Kochi, store pickup.
- Likely hidden examples: EMI, installation, price match, gift wrap, loyalty points, a customer-care phone number, electronics exchange.

### H. Verification flow (IDV-1..4)

- T2: when the order ID first appears, call `lookup_order(order_id=X)` (unverified) and ask for the last 4 phone digits OR the delivery pincode. Echoing the ID in groups of four is fine.
- T3: call `lookup_order(order_id=X, verification_value=V)` with exactly the digits the customer gave.
  - On success, answer the pending T1 question right away. PC011 and PC012 expect the promised date in T3.
  - On the first failure: clarify ("doesn't match, please try again"). Never reveal the expected value; MNI includes the true pincode.
  - On the second failure, even with the same value repeated: call lookup again, then **refuse**. Share no details (MNI includes the dates and the pincode) and point the customer to the registered phone (IDV-3).
- A topic switch to general policy needs no order context (CPN-1). Switching back must reuse the stored order (PC013/PC014 T5: `shipped_on`).
- Coreference: "and the refund?" means the same item (PC003 T5: wallet, so instant; PC004 T5: UPI 1–3).
- Reply in the language the customer uses (STY-4), not `preferred_language`. PC018 profile says `ta`, customer speaks hi-en. PC021 profile says `mr`, customer speaks hi. PC008 profile says `hi`, customer speaks en.

---

## 3. Data profile

- **orders.status (1,000):** delivered 660, shipped 140, cancelled 62, returned_refunded 59, packed 22, returned_to_origin 19, out_for_delivery 13, return_refund_initiated 10, return_requested 8, return_picked_up 5, placed 1, delivery_attempted 1 (41763040).
- **payment_method:** upi 480, cod 207, card 206, wallet 57, netbanking 50.
- **delivery_type:** standard 825, slot 112 (grocery only, fee always 0), express 63 (46 non-Plus paid ₹79, 17 Plus paid ₹0).
- **delivery_attempts:** 1: 702, 0: 237, 3: 34, 2: 27.
- **coupon_code:** SAVE10 60, NEW100 54, FEST200 36.
- **return_status:** 82 returns.
  - By status: refund_completed 59, refund_initiated 10, requested 8, picked_up 5.
  - By reason: changed_mind 24, size_issue 23, quality 18, not_as_described 17.
  - By category: electronics 30, fashion 28, beauty 11, home 8, books 5.
  - Refund method: upi 37, card 18, cod_bank 12, wallet 11, cod_wallet 2, netbanking 2.
  - The ₹49 fee is charged exactly when category is fashion, reason is changed_mind or size_issue, and the customer is not Plus (82/82).
- **damage_status** (32 reports): approved_replacement 17, awaiting_photos 6, priority_resolution 4, handled_as_return 3, rejected_late_report 2. Issues: defective 13, wrong_item 10, damaged 7, missing_item 2.
- **Damage on items > ₹10,000 (all `priority_resolution`):**
  - 89782837 ELE-0021 TV, 40 h, no photos (PC002).
  - 61484865 HOM-0048 sofa, 40 h.
  - 50801038 ELE-0012 K7, 30 h.
  - 95213643 HOM-0048 sofa, 6 h, wrong item.
  - Near-threshold items were approved normally: 82580117 and 81994448 (ELE-0015), 55507488 (HOM-0050).
  - Late reports (60–90 h): grocery → `rejected_late_report` (69620373, 72804612); fashion → `handled_as_return` (50917905, 90015246, 41085828).
- **contacts_last_7_days:** 0: 872, 1: 94, 2: 30, 3: 2, 4: 2. That is **34 orders ≥ 2**:
  - 39141531, 40949742, 66774364, 23135970, 17578540, 56071617(3), 98248876, 45988716, 17747810, 89037322
  - 48567593, 14782432, 82950976, 57235996, 93997658, 48606638, 48196636, 93248370, 44706505, 40876975(4)
  - 24179736, 33401384, 58376637(3), 29235737, 45011817, 74892618, 51861110, 15388730(4), 83906391, 25250869
  - 19168921, 31955109, 30887953, 15782539
- **Overdue refunds on 10-20 (strictly more than max + 3 bd):**
  - Return refunds (the only type with a completion column): **16640894** (upi, init 07-20; PC010) and **88428819** (card, init 06-22). 48567593 is still within grace.
  - Cancellation refunds: 46 initiated (upi 29, card 15, wallet 2). There is **no completion column**, so 38 look overdue by date alone; 76823002 is within grace.
  - RTO refunds: 14 initiated. 7 are past grace: 11121225, 14070367, 30885231, 56141712, 99809590, 79842056, 60505358. 57723321 and 97378296 are exactly 3 business days past.
  - Whether cancellation and RTO refunds should trigger rule 5 is UNVERIFIED (see section 7).
- **Express late:** 7 orders.
  - ₹79 credits: 58634590 (credited 09-29, PC024), 95812905 (09-24), 22354022 (09-18, PC023), 87148208 (10-02).
  - Plus members with no credit: 63173620, 69700359, 77808072.
- **Late deliveries overall:** 148 (standard 119, slot 22, express 7).
- **Open orders past their promise on 10-20:** 86035743 (shipped, 10-16), 13029488 (OFD, 10-16), 40629461 (slot OFD, 10-19), 10395095 (slot OFD, 10-16), 99465427 (shipped, 10-17), 32242098 (OFD, 10-16).
- **Cancellable now:** 23 orders (35061733 placed, plus 22 packed). Note PC017's order was placed 2026-10-20T22:41, later in the day than the "now" of the dataset.
- **Return windows today:** 278 item-lines open, 660 expired, 267 non-returnable, 30 with the deadline exactly today.
- **Customers (300):**
  - 75 are Plus members.
  - preferred_language: en 153, hi 72, hi-en 30, te 10, ta 9, kn 8, mr 6, bn 5, gu 4, ml 3.
  - Phone format is `+91 5XXXX XXXXX`. 29 phone suffixes start with 0 (PC009 0783, PC012 0654), so keep them as strings. 3 suffixes are shared across customers.
  - `delivery_pincode` equals the home pincode for 1000/1000 orders.
- **Products (70):**
  - Categories: electronics 25, fashion 14, home 12, grocery 5, innerwear 5, beauty 4, books 3, digital 2.
  - Fulfilment: ZentroMart 49; marketplace 21 (Sunrise Electronics 6, Kalpana Fashions 5, Shree Traders 4, Metro Gadget Hub 2, Deccan Home Store 2, Urban Basket Retail 2).
  - Fulfilment × assured: ZentroMart + True 15, ZentroMart + False 34, marketplace + True **8** (the MKS-3 trap), marketplace + False 13.
  - `unit_price_inr` always equals the catalog price.
- **Integrity checks that pass:** COD never exceeds ₹10,000 and never appears on non-COD pincodes; the COD fee is always 25; no order ships to an unserviceable pincode; return line SKU always matches `return_sku`; no return is outside its window.

---

## 4. `validate_dataset.py` and the support logs

**The validator (stdlib only) checks:**
- Row counts (300/1000/1783/70/36/4/244/52/96).
- Primary-key uniqueness and that keys are not blank.
- 9 foreign-key sets.
- Order-item title and category match the products table.
- `subtotal == Σ qty×unit` and `total == subtotal − coupon + delivery + cod`.
- 21 KB files with `doc_id/title/doc_type/effective_from/status`, and unique `## [ID]` sections.
- Every `gold_evidence` is a section ID or `products.csv:<valid sku>`.
- 23 conversations with consecutive turns, and no `[COMPANY]` placeholder left.
- The tool gate:
  - An unverified lookup returns no `items` or `status`.
  - An unknown order or wrong proof returns `verified` falsy.
  - The right phone suffix or pincode works, and `phone_last4` is never returned.
  - `create_ticket('short')` returns `created=False` (needs at least 20 characters).
- Every expected verification call's `verification_value` equals **all digits concatenated from that customer_message**, and the call contains `order_id=<row order_id>`.

**Support logs (244):**
- Voice 157, chat 87. Languages en 202, hi-en 42 (no Devanagari).
- Every transcript is 3 lines: greeting, one customer line, one agent line.
- Intents: where_is_my_order 76, cancel_order 33, coupon_issue 26, return_request 23, delivery_fee_question 22, talk_to_human 22, warranty_claim 19, damaged_item 18, refund_status 5.
- 78 were QA-reviewed, but only **2 have qa_findings**:
  - L200200 `agent_quoted_faq_timeline_instead_of_policy_for_upi`
  - L200219 `agent_quoted_superseded_10_day_electronics_window`

**Mistakes I found that QA did not flag (likely hidden-test traps):**
- **Superseded 10-day electronics window** for items delivered after Aug 1: L200212, L200148, L200112.
- **Festive window missed:** L200051 told a customer 15 days for a tote whose order was placed 10-04; it should be 30.
- **Compensation promised:** L200293 offered ₹500 to the wallet, which ESC-4 forbids.
- **No verification** before reading out order status, and a first name, in all 76 where-is-my-order logs.
  - "Delivered" was stated without the TRK-2 advice.
  - Statuses like `out_for_delivery` and `returned to origin` were read out raw.
- **Human handover** said "connecting you" with no ticket (ESC-2) in all 22 talk_to_human logs.
- **Warranty answers** ignore MKS-3 (all 19).
- **Fee answers** quote the ₹40 rule even for express (₹79) and for ₹0-fee orders.
- **Damage answers** say "share photos within 48 h" even for 60–90 h reports (L200033, L200211, L200029). The right answer is DWM-4 (normal return or warranty). No damage log checks the ₹10,000 threshold.
- **Cancellation:** L200008 said "already shipped" on 10-19 when `shipped_on` is 10-20.

---

## 5. Output contract for automatic scoring

Brief (p.14): one run command takes a folder of audio files and saves replies "as text and audio" with "the document chunks it used". The brief defines **no JSON schema**, so the fields below follow the practice-file columns (UNVERIFIED that the scorer reads exactly these).

- **decision:** one of `answer | clarify | escalate | refuse`. Questions accept anything in `acceptable_decisions`; conversations accept only `expected_decision`.
- **evidence:** a list of section IDs exactly as they appear in the headings (`RET-2`, `KB-00.3`, `RETv3-2`, `FAQH-3`, `KB-00.1`) plus `products.csv:<SKU>`. Join with ` ; ` if written into a CSV.
  - The practice gold has 0–3 items (2 is most common). Cite `KB-00.3` for date math, `KB-00.1` when overriding an FAQ, `IDV-2` on verification turns, `STY-1` on the greeting turn, `IDV-3` on failures, `ESC-1` (+ `ESC-3`/`DWM-3`/`ESC-4`) on escalation.
  - Whether scoring is recall or F1 is UNVERIFIED, so keep the list tight.
- **tool_calls:** canonical strings that match gold character for character, joined with ` ; `:
  - `lookup_order(order_id=89782837)` (unquoted digits only, spaces removed)
  - `lookup_order(order_id=89782837, verification_value=4533)` (comma plus one space, leading zeros kept: `0783`)
  - `create_ticket()` — gold writes it with **empty parens** even though the real call takes `summary` (≥20 chars), `order_id`, `reason` and `intent`. Log a canonical form plus a separate detailed-args field.
- **Real signatures (tools.py):**
  - `lookup_order(order_id: str, verification_value: str=None) -> dict`. Non-digits are stripped from both arguments. The proof must be 4 digits matching the phone suffix or 6 digits matching `delivery_pincode`; any other length fails. A full 10-digit phone number fails, so extract the last 4.
  - On success the result includes `found`, `verified`, all order columns, `items`, `customer_first_name` and `is_plus`. **It includes `delivery_pincode` and `customer_id`**, so strip these before the LLM sees the result.
  - `create_ticket(summary, order_id=None, reason=None, intent=None) -> {'created':True,'ticket_id':'TKT…'}`. It appends to `tools/tickets_created.csv`.
- **reply_text:**
  - Use digits and full dates with the month name and year (for example "27 October 2026" / "27 अक्टूबर 2026") so lexical `must_include` matches.
  - Match `reply_language` to the input language.
  - Never write a phrase from `must_not_include`, even negated. Substring matching is likely, so "nothing has been credited", "not within 10 days", "no ₹49 will be charged" and "FAQ says 5 to 7 days but…" all fail.
- **tts_text:** a separate spoken form: "the 27th of October 2026", order IDs in groups of four, "forty-nine rupees" (STY-3 plus the brief).

---

## 6. ASR corruption patterns (questions.csv `asr_text`) and normaliser specification

**Patterns observed:**
1. Everything lowercased (Latin script) and all punctuation removed. Apostrophes dropped: `dont`, `im`, `theres`, `wont`, `doesnt`.
2. Filler words added at the start: `uh`, `so`, `haan`, `hello`.
3. **Digits spelled out one by one:**
   - `2026` → `two zero two six` or **`to zero to six`**
   - `10000` → `one zero zero zero zero`
   - `256` → **`to five six`**
4. **SKUs:** the prefix is kept with a hyphen and the digits are spelled out, with "to" standing in for "two":
   - `ele-0012` → `ele-zero zero one to`
   - `ele-0023` → `ele-zero zero to three`
   - `ele-0002` → `ele-zero zero zero to`
5. Acronyms spelled out: `upi` → `u p i` (and `uh u p i`).
6. Words split or misspelled: `refund` → `re fund`, `kurta` → `kurtha`.
7. Words dropped, sometimes the key word: `collection`, `have`, `pe`, `लिए`, **`सामान`**, and **brand `nimbus`** (the product title is partial).
8. Hindi stays in Devanagari while Latin product names stay mixed in (code-mixing). `(Pack of 4)` → `Pack of 4`.
9. Day-of-month numbers stay as digits (`17 october`), as do `50 ml` and `3`.

**Normaliser rules:**
- Map digit words: en `zero/oh/o, one, two/to/too, three/tree, four/for, five, six, seven, eight/ate, nine`; hi `shunya, ek, do, teen, char/chaar, paanch, chhe/chah, saat, aath, nau`; Devanagari words `शून्य…नौ`; Devanagari digits `०–९`.
- Expand `double X` and `triple X`. Handle pairs like "forty five thirty three" with word2num.
- Turn `to`/`too`/`for` into a digit only inside a run of digit words, or when filling an expected slot (SKU = 4 digits, order = 8, phone suffix = 4, pincode = 6, year).
- Exclude cue words from slot values: in "last **four** digits **four five three three**", the first "four" is not part of the value. The same applies to "aakhri chaar".
- Don't merge product-name numbers into IDs: `K7`, `Book 14`, `43-inch 4K`, `65W`, `750W`, `3-Seater`, `10000 mAh`, `Pack of 3`.
- SKU regex: `(ele|fsh|hom|bty|bks|gro|inr|dgt)[- ]?\d{4}`. **`inr` clashes with the currency word INR.**
- Merge `u p i` → UPI and `re fund` → refund; drop leading fillers.
- Match products fuzzily against catalog titles because the brand may be missing.
- Order IDs come in as 4+4 groups ("8978 2837") and must be stripped to 8 digits.

**Voice language handling (from the brief):** `en-IN` accepts Hinglish and returns Latin script. Hindi practice `asr_text` is in Devanagari, which implies `hi-IN`. The batch runner needs a way to pick the language per file; whether Gnani detects the language automatically is UNVERIFIED.

---

## 7. Inconsistencies and gotchas

1. IDV-2 says "compare with `phone_last4`", but the tool never returns it; the tool does the comparison itself. The verified result does leak `delivery_pincode`.
2. Cancellation and RTO refunds have **no completion field**. Only return refunds have `return_refund_completed_on`. Applying ESC-1 rule 5 to "my cancellation refund hasn't come" is a judgement call (UNVERIFIED).
3. REF-5 says delivery fees are refunded on damaged/defective/wrong returns. Six quality or not_as_described returns that had a delivery fee (94044366, 98463156, 83066272, 57336001, 18565089, 28109608) did not get it back, although the pickup fee was waived for them.
4. Damage report 67234644: 90 h after delivery, but status is `awaiting_photos` rather than handled_as_return or rejected.
5. Gold picks one colour variant even when the question omits the colour (see 2B).
6. The README says STT runs over WebSocket; the brief uses REST `stt.transcribe(...)` (clips of 60 s or less).
7. The brief simplifies the tool signatures to `lookup_order(order_id)` and `create_ticket(summary)`.
8. Brief and dataset disagree on compensation demands: the brief says create a ticket, the gold says refuse with no tool call.
9. TRK-1 display names do not match the data's status codes (`out_for_delivery`, `returned_to_origin`, and the `return_*` statuses are absent from TRK-1). Map them to display names.
10. PC010's order has two separate lines for the same SKU (FSH-0027 ×2), and 84 orders contain duplicate SKUs. Use `return_line_no`.

**UNVERIFIED overall:**
- The scorer's matching method (substring vs semantic), retrieval metric (recall vs F1) and output file format.
- How multi-turn conversations will be delivered as audio files (filename convention for conversation and turn).
- Whether `create_ticket` is required on refusals.
- Gnani language auto-detection and Devanagari digit output.