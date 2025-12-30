\# Service Specification: billing-service



\## 1. Service Responsibility

The `billing-service` acts as the financial orchestrator for the order-to-cash lifecycle. It is responsible for the deterministic calculation of invoice totals, complex tax application (GST), promotional discount attribution, and maintaining the source of truth for all customer billing documents.



\## 2. Invoice Generation Lifecycle

Invoices are not manually created; they are triggered by the `order-service` via a `COMPLETED` state transition event.



\### 2.1 Data Components

Every generated invoice object is required to contain:

\* \*\*Header Metadata:\*\* `invoice\_id`, `correlation\_id`, `tenant\_id`, and `timestamp`.

\* \*\*Line Items:\*\* Detailed breakdown of products/services, including `unit\_price`, `quantity`, and `sku\_id`.

\* \*\*Subtotal:\*\* The sum of all line items before taxes or discounts.

\* \*\*Tax Ledger:\*\* A breakdown of CGST, SGST, and IGST components.

\* \*\*Total Payable:\*\* The final amount, rounded to two decimal places, required for payment authorization.



---



\## 3. GST \& Taxation Logic

The system implements a localized tax engine designed for compliance with regional fiscal requirements.



\### 3.1 Determination Logic

Taxation is determined at the time of invoice finalization using a three-factor lookup:

1\. \*\*Nexus Check:\*\* Comparison between the `fulfillment\_center\_location` and the `customer\_shipping\_address`.

2\. \*\*Tax Category:\*\* Product-specific codes (e.g., HSN/SAC codes) retrieved from the Product Catalog.

3\. \*\*Slab Resolution:\*\* Matching the transaction value against current legislative GST slabs.



\### 3.2 Tax Types

\* \*\*Intra-state Transactions:\*\* Applied when the origin and destination are within the same state. The system splits the tax 50/50 between \*\*CGST\*\* (Central) and \*\*SGST\*\* (State).

\* \*\*Inter-state Transactions:\*\* Applied for cross-border shipping within the country. A single \*\*IGST\*\* (Integrated) rate is applied.



\### 3.3 Performance \& Configuration

Tax rates are stored in the `tax-config` relational table. To minimize latency during the checkout flow, these rates are cached in a \*\*Redis\*\* cluster with a 24-hour Time-To-Live (TTL). A manual cache-clear is triggered via the Admin Portal whenever tax laws are updated.



---



\## 4. Discount Hierarchy

Discounts are applied strictly \*\*before\*\* tax calculation to ensure the taxable base is legally accurate. The service supports a hierarchical application of discounts:



| Discount Type | Application Logic | Priority |

| :--- | :--- | :--- |

| \*\*Flat Discount\*\* | A fixed currency amount (e.g., -$10.00) subtracted from the subtotal. | 1 |

| \*\*Percentage\*\* | A percentage of the gross line-item value (e.g., -15%). | 2 |

| \*\*Promotional Coupon\*\* | Validated against the `promo-service` for expiration and usage limits. | 3 |



---



\## 5. State Machine \& Transitions

The `billing-service` manages the internal status of an invoice to ensure data integrity.



\* \*\*DRAFT:\*\* Initial state where line items are gathered but taxes are not yet locked.

\* \*\*FINALIZED:\*\* Tax and discounts are calculated; the invoice is now immutable.

\* \*\*PENDING\_PAYMENT:\*\* The invoice is awaiting a `PaymentConfirmed` event from the `payments-service`.

\* \*\*PAID:\*\* The transaction is settled; ledger entries are generated.

\* \*\*CANCELLED:\*\* Reversal state used if the order is returned or the payment fails the maximum retry threshold.



---



\## 6. Audit \& Compliance

All state changes in the `billing-service` are logged to an `audit\_log` table, capturing the `user\_id` or `system\_process` that initiated the change, along with a "Before" and "After" snapshot of the invoice JSON.

