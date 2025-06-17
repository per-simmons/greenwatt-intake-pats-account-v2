GreenWatt Solar Intake & Document Automation Project Overview & Next Steps

Project Goal Create a simple app that helps GreenWatt manage the community solar enrollment process. Field agents will submit customer information and utility bills through a branded intake form. The app will then generate the correct signed documents, organize them in Google Drive, log everything in Google Sheets, and send notifications to internal team members.

Tech Stack

- Python app (Flask framework)
- Google Sheets
- Google Drive
- Google Cloud Vision API (OCR)
- OpenAI GPT-3.5 (for data extraction)
- Twilio (SMS notifications and customer verification flow)
- SMTP (email notifications)

Full User Flow

1. Field agent accesses the intake form via a branded URL (e.g. solar.greenwattusa.com)
2. Agent fills out the form including:
   - Agent ID
   - Legal Business Entity Name (optional)
   - Account Name (from utility bill)
   - Contact Full Name
   - Contact Title
   - Contact Phone Number
   - Contact Email
   - Utility (dropdown: ConEd, National Grid, NYSEG, RG&E)
   - Account Type (dropdown: Small Demand <25 KW, Large Demand >25 KW, Mass Market [Residential])
   - Operator or Developer (dropdown: Meadow Energy, Solar Simplified)
   - Agreement to T&C + POA (checkbox)
   - Upload Bill (JPEG or PDF)
3. Agent submits the form
4. App performs the following:
   - Parses utility bill using Google Cloud Vision OCR
   - Extracts and calculates monthly/annual kWh usage using GPT‑3.5, including interpreting graphs when needed
   - Maps Agent ID to Agent Name via Google Sheet
     - **Agent ID → Agent Name Mapping**
       1. **Agent Sheet**
          - Tab `Agents` → Column A `agent_id`, Column B `agent_name` (using the Sheet Jason supplied)
       2. \*\*Helper in \*\*\`\`
       ```
       def get_agent_name(agent_id):
           rows = sheets.values().get(
               spreadsheetId=SHEET_ID,
               range="Agents!A:B"
           ).execute().get("values", [])
           lookup = {r[0]: r[1] for r in rows[1:] if len(r) >= 2}
           return lookup.get(agent_id, "Unknown")
       ```
       3. **Form submission handler**
       ```
       agent_name = get_agent_name(form["agent_id"])
       sheet_append_row([... , form["agent_id"], agent_name, ...])
       ```
       4. **Outcome**
          - Agent enters code only → Sheet logs both code and resolved name.
          - Jason can update or add agents in the Sheet at any time without redeploying.
     - Document Reference: [https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I/edit?gid=1031875180](https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I/edit?gid=1031875180)
   - Retrieves Developer Agreement and standard POA template based on dropdown selections
     - **Template Storage**: All templates stored in Google Drive folder `GreenWatt_Templates` (ID: `1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE`)
     - **POA Template**: `GreenWattUSA_Limited_Power_of_Attorney.pdf`
     - **Agency Agreement**: `GreenWATT-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf`
     - Developer Agreement Mapping Logic:
       - Based on the selected Developer (e.g., Meadow Energy) and the selected Utility (e.g., National Grid), the app cross-references a mapping table in Google Sheets and downloads the template from Google Drive.
       - Example: If Meadow Energy is selected with National Grid, the app uses Meadow-National-Grid-Commercial-UCB-Agreement.pdf
       - If Mass Market is selected as the Account Type, the app defaults to this file: Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002
       - All agreement documents are located in: /Volumes/Pat Samsung/Client/Upwork/Fulfillment 2025/GreenWatt\_Automation\_6.11.25/GreenWatt-documents **Developer Agreement Mapping**
     1. Claude will be provided a Google Sheet tab (e.g., `Developer_Mapping`) with columns:
        - Column A: Developer Name (e.g. Meadow Energy)
        - Column B: Utility Name (e.g. National Grid)
        - Column C: Document File Name (e.g. Meadow-National-Grid-Commercial-UCB-Agreement.pdf)
     2. Claude will cross-reference the Developer dropdown selection and utility dropdown value with this Sheet.
     3. Based on the mapping, Claude will download the correct agreement template from Google Drive `GreenWatt_Templates` folder and use it in document generation.
     4. When Solar Simplified’s agreement becomes available, Jason simply adds a new row to the Sheet — no redeploy needed.
   - Fills both documents with customer info and generated signature (based on name from form)
     - **Signature Font Requirement**: When the Terms & Conditions checkbox is checked, customer signatures must be applied using a signature-style font (e.g., cursive/script font) to simulate handwritten signatures on all documents.
     - Claude should locate signature blocks in the template PDF and overlay a text-based signature (e.g., the typed customer name) on the same horizontal line as the "By:" field.
     - For each agreement, Claude must find the correct placeholder in the PDF using relative positioning or coordinate matching, then insert the typed signature aligned visually with the underscore.
     - See attached reference image (e.g., Meadow NYSEG agreement) showing how customer signature is typed in on the line labeled "By:" under "SUBSCRIBER." This will need to be done programmatically using ReportLab, PyPDF2, or a similar PDF processing tool.
     - If a signature block exists for both the Solar Producer and Subscriber, only the Subscriber section is filled by the app.

## Anchor‑Text Signature & Field Overlay System

**Goal**: Programmatically place typed signatures and customer info exactly on the underlines of each PDF template without editing the PDF in Acrobat, with pixel-perfect precision.

### Libraries (All Open Source)

| Library | Purpose | License |
|---------|---------|---------|
| `pdfplumber` | Extract words + their coordinates from a PDF page | MIT |
| `reportlab` | Create a transparent overlay PDF with text in exact (x,y) location | BSD |
| `PyPDF2 ≥ 3.0` | Merge the overlay onto the original template, producing final flattened PDF | BSD |

All three are MIT/BSD‑style licenses — no extra cost.

### Implementation Steps (Per Template)

#### 1. Anchor Dictionary
Create a small JSON for each agreement series (they all share wording):

```json
{
  "customer_signature": {
    "anchor": "Customer Signature:",
    "dx": 120, "dy": -2
  },
  "printed_name": {
    "anchor": "Printed Name:",
    "dx": 120, "dy": -2
  },
  "date": {
    "anchor": "Date:",
    "dx": 120, "dy": -2
  },
  "email": {
    "anchor": "Email Address:",
    "dx": 120, "dy": -2
  }
}
```

Same anchor set works for National Grid, NYSEG, RG&E commercial UCB PDFs.

#### 2. Find Anchor Coordinates

```python
import pdfplumber
def find_anchor(page, text):
    for w in page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=True):
        if text in w["text"]:
            return float(w["x0"]), float(w["top"])
    raise ValueError(f"Anchor '{text}' not found")
```

#### 3. Build Overlay

```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
def build_overlay(page_w, page_h, mapping, payload):
    c = canvas.Canvas("overlay.pdf", pagesize=(page_w, page_h))
    for key, cfg in mapping.items():
        x,y = cfg["coord"]  # filled after anchor search
        c.drawString(x + cfg["dx"], page_h - (y + cfg["dy"]), payload[key])
    c.save()
```

#### 4. Merge

```python
from pypdf import PdfReader, PdfWriter
base = PdfReader("template.pdf")
over = PdfReader("overlay.pdf")
writer = PdfWriter()
base_page = base.pages[0]
base_page.merge_page(over.pages[0])
writer.add_page(base_page)
with open("filled.pdf", "wb") as f:
    writer.write(f)
```

### Mass‑Market (Form Subscription Agreement)
Uses the same field names, so the above anchor JSON works. That file is used for all residential customers — keep it in Templates/.

### Unique POA ID Enhancement
Add while building payload:

```python
import uuid, datetime as dt
payload["unique_poa_id"] = f"POA-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
```

Log this ID in the Submissions sheet.

### Signature Styling Requirements
Customer signatures must look like authentic Adobe PDF signatures:
- Use signature-style font (cursive/script appearance)
- Proper formatting to match Adobe PDF signature examples
- Consistent styling across all document types
   - **Unique POA ID Generation**: Applies a unique identifier to each Power of Attorney document for auditing and tracking purposes
     - Format: POA-{YYYYMMDD}-{sequential_number} (e.g., POA-20250616-001)
     - Must be visible on the POA document and logged in the Google Sheet
     - Sequential numbering resets daily
   - Stores the signed documents in the correct folder structure in Google Drive
   - Logs submission in a master Google Sheet, including:
     - All form inputs
     - Mapped Agent Name
     - Developer name
     - Utility and Account Type
     - kWh usage (monthly and annual)
     - Unique POA ID
     - Timestamps
   - Sends SMS to customer via Twilio asking to confirm Y/N participation in the CDG program (triggered immediately on form submit)
   - Logs SMS response and timestamp into Google Sheet with columns: SMS Sent, SMS Sent Timestamp, SMS Response, SMS Response Timestamp, Phone Number, Message SID
   - Sends email alert to up to 3 internal team members using SendGrid API for reliable delivery including:
     - Agent Name
     - Customer Name
     - Utility
     - Signed Date
     - Annual Usage (kWh)
     - Professional HTML formatting with GreenWatt branding
   - Sends SMS notification to internal team with submission summary
5. Google Sheet stays connected in a way that allows Jason to:
   - Filter/sort submissions freely
   - Add backend columns and calculations (e.g., revenue) without interfering with app function
   - Easily expand Utilities, Developers, and Agreement mappings by updating connected Google Sheet tabs



Note: How the Dynamic Developer Dropdown Will Work You will have a connected Google Sheet to manage the Developer dropdown list and associated Agreement templates. When you update this Sheet (e.g., add a new Developer and link to a new template), the app will automatically reflect those changes in the intake form and generated documents. Claude will reference both Developer and Utility fields in order to select the correct document.

Note: How Agent ID to Agent Name Mapping Will Work You will manage a separate Agent Sheet with Agent IDs and Agent Names (link provided: [https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I/edit?gid=1031875180](https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I/edit?gid=1031875180)). When a field agent enters their ID in the form, the app will cross‑reference this Sheet and log both the ID and name in the Google Sheet for tracking.

Developer Agreement Mapping Table:

| Developer Name | Utility Name  | Agreement File Name                               |
| -------------- | ------------- | ------------------------------------------------- |
| Meadow Energy  | National Grid | Meadow-National-Grid-Commercial-UCB-Agreement.pdf |
| Meadow Energy  | NYSEG         | Meadow-NYSEG-Commercial-UCB-Agreement.pdf         |
| Meadow Energy  | RG&E          | Meadow-RGE-Commercial-UCB-Agreement.pdf           |
| Meadow Energy  | Mass Market   | Form Subscription Agreement - Mass Market UCB.pdf |

When Solar Simplified’s agreement becomes available in July, Jason can simply add a new row to this Sheet with the corresponding utility and document file path. No redeploy is needed.

All agreement templates are stored in Google Drive folder: `GreenWatt_Templates` (ID: `1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE`)

Tech Implementation **Dynamic Utility & Developer Dropdowns**

1. **Sheet structure**
   - Tab `Utilities` → Column A `utility_name`, Column B `active_flag` (TRUE/FALSE)
   - Tab `Developers` → Developer Name + Agreement link
2. \*\*Helper in \*\*\`\`

```python
from cachetools import TTLCache
cache = TTLCache(maxsize=32, ttl=900)  # 15‑min cache

def get_active_utilities():
    rows = sheets.values().get(
        spreadsheetId=SHEET_ID,
        range="Utilities!A:B"
    ).execute().get("values", [])
    return [r[0] for r in rows[1:] if len(r) >= 2 and r[1].strip().upper() == "TRUE"]
```

3. **Route adjustment**

```python
utilities_list = cache.get("utilities") or get_active_utilities()
cache["utilities"] = utilities_list
return render_template("form.html", utilities=utilities_list, developers=dev_list)
```

4. **Template snippet**

```html
<select name="utility" required>
  {% for u in utilities %}
     <option value="{{ u }}">{{ u }}</option>
  {% endfor %}
</select>
```

5. **Outcome**
   - Jason toggles a row to TRUE → it appears in the form after cache expiry (or immediately via an admin refresh).
   - No redeploy needed to add new markets.

## To Be Completely Clear On The Client Updating Intake Form Logic

Yes — Jason will be able to:

1. **Show / hide utilities** (e.g., add Central Hudson later) by flipping a TRUE/FALSE flag in a `Utilities` tab.
2. **Add a brand-new developer (Solar Simplified) and its agreement(s)** simply by adding rows in a `Developer_Mapping` tab — no code deploy required.

The intake form and the PDF-generation logic will re-read those tabs on every page-load (or on a short-lived cache), so the changes appear almost instantly.

---

## Why it works

| What Jason editsSheet Tab & ColumnsWhat the app does at run-time |                                                                                                |                                                                                                                                                                   |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Utilities list** *(which utilities appear in the dropdown)*    | `Utilities` • A `utility_name` • B `active_flag` (TRUE/FALSE)                                  | `get_active_utilities()` pulls only rows marked **TRUE** and renders that list into the `<select>` element.                                                       |
| **Developer ↔ Utility ↔ Agreement mapping**                      | `Developer_Mapping` • A `developer_name` • B `utility_name` (or “Mass Market”) • C `file_name` | On submit the app looks up *Developer + Utility* (or *Developer + Mass Market*) in this table → grabs the matching PDF file → injects data → saves a signed copy. |

*Everything* else (OCR, kWh math, Drive upload, sheet logging, SMS) happens after that lookup, so once the sheet says “use **Solar-Simplified-National-Grid.pdf**” the rest of the pipeline just works.

---

## Concretely for Jason

- **Want to enable Central Hudson later?**\
  Open `Utilities` → add a row `Central Hudson | TRUE`.\
  → It pops into the form, and Claude can now map agreements to that utility.
- **Solar Simplified arrives in July?**\
  Drop rows like:
  | ABC                                                                   |               |                                      |
  | --------------------------------------------------------------------- | ------------- | ------------------------------------ |
  | Solar Simplified                                                      | National Grid | SolarSimplified-NationalGrid-UCB.pdf |
  | Solar Simplified                                                      | Mass Market   | SolarSimplified-MassMarket-UCB.pdf   |
  | → The moment Jason saves the sheet, those options work in production. |               |                                      |

No redeploy, no code edit — the app is reading its “business rules” straight from the sheets.

---

### Already documented

- The **“Developer Agreement Mapping Table”** and the **Tech Implementation** section in the Canvas spell out these two tabs and the helper functions (`get_active_utilities()`, `Developer_Mapping` lookup).
- Signature-placement, POA-ID stamping, SMS verification, etc., are unaffected by these sheet edits.

If you’d like an example Google Sheet pre-filled with Solar Simplified placeholder rows (so Jason just swaps in file names later), let me know and I can mock that up.

---

## Environment & Credential Details (for Claude)

### Google Cloud Console

| Setting                   | Value                                                                    |
| ------------------------- | ------------------------------------------------------------------------ |
| **Project Name**          | **GreenWatt Intake Form**                                                |
| **Service Account Name**  | GreenWatt Intake Service                                                 |
| **Service Account ID**    | `greenwatt-intake-service`                                               |
| **Service Account Email** | `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com` |
| **JSON Key**              | *link to keyfile.json*                                                   |

> Claude: use this service‑account key for Drive, Sheets, and Vision calls.

---

### Google Sheets

| Sheet                     | Purpose                                  | Key Info                                                                                                                                                                                                                             |
| ------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Intake Log**            | Master log – one row per form submission | URL: [https://docs.google.com/spreadsheets/d/11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o](https://docs.google.com/spreadsheets/d/11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o)   ID: `11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o` |
| `Submissions` (tab)       | Raw dump of every submission             | Appends via `sheets_service.append_row()`                                                                                                                                                                                            |
| `Developer_Mapping` (tab) | Links Developer + Utility → Agreement    | **Columns**  A `developer_name`  B `utility_name` (or `Mass Market`)  C `file_name` (exact PDF name)                                                                                                                                 |
| `Utilities` (tab)         | Controls which utilities appear          | **Columns**  A `utility_name`  B `active_flag` (`TRUE`/`FALSE`)                                                                                                                                                                      |
| **Agents Sheet**          | Maps `agent_id` → `agent_name`           | URL: [https://docs.google.com/spreadsheets/d/1K\_0cm0syXRFTWyA97MDRjPvRSKk1Qzu3](https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I)  ID: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I`                                  |

**Utility toggle example**  (`Utilities` tab):

```
A              | B
----------------------
National Grid  | TRUE
NYSEG          | TRUE
RG&E           | FALSE
ConEd          | FALSE
```

Only rows marked **TRUE** render in the form.

---

### Google Drive

| Folder               | Purpose                               | ID                                       |
| -------------------- | ------------------------------------- | ---------------------------------------- |
| **Signed Docs root** | Final PDFs + template store           | `1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W`      |
| **Templates/**       | Sub‑folder holding all agreement PDFs | Path: `GreenWatt_Signed_Docs/Templates/` |

> Workflow: Jason uploads a new PDF template to *GreenWatt_Templates* Google Drive folder → adds a row to `Developer_Mapping` → app auto‑uses it on the next submission.

---

### End‑to‑End Update Flow (for Jason)

1. **Add / hide utilities** → flip `active_flag` in `Utilities` tab.
2. **Add Solar Simplified agreement (July)**
   1. Upload `SolarSimplified-NationalGrid-UCB.pdf` into *GreenWatt_Templates* Google Drive folder.
   2. Add a row in `Developer_Mapping`: `Solar Simplified | National Grid | SolarSimplified-NationalGrid-UCB.pdf`
3. No code changes, no redeploy — form & doc‑gen pick up changes instantly.

---

### Sample Reference Packets

The following PDFs are *examples only* (not used directly) — keep in `/GreenWatt_Automation_6.11.25/GreenWatt-documents/Reference/` for Claude to consult when formatting:

- `Micheal Makin.pdf`  (residential sample)
- `Ann Curry.pdf`  (residential sample)
- `Keith Martin.pdf`  (residential sample)
- `Gan Development-790 Southside Dr‑413.pdf`  (small commercial sample)

Claude: **do not** copy these files; use them purely to mirror signature placement & layout.

---



### Twilio API

**Note:** 2FA was required, currently validated with Pat’s number. This will need to be updated with Jason’s number.

- **Credentials:** Same as Google credentials above
- **Recovery Code:** `8N6AB6KR53QDFC6VDGPQWC1R`
- **Account SID:** `AC_your_twilio_account_sid_here`
- **Auth Token:** `your_twilio_auth_token_here`
- **API Key (GreenWatt-Intake):**
  - **SID:** `SK_your_twilio_api_key_sid_here`
  - **Secret:** `your_twilio_api_key_secret_here`

### SendGrid API

**Note:** 2FA was required, currently validated with Pat’s number. Will need to update with Jason’s number.

- **Credentials:** Same as Google credentials above
- **API Key Name:** `GreenWatt-Intake-SendGrid`
- **API Key:** `SG.your_sendgrid_api_key_here`
- **Dynamic Template (WIP):**
  - **Name:** GreenWatt Intake
  - **Dynamic Version Name:** ‘Untitled Version’
  - **Current Text Placeholder:**
    ```
    Hello {{contact_name}},
    Your submission for {{utility}} is now processed.
    ```

### OpenAI API

**Note:** Jason will need to update with his credit card info before deployment.

- **Credentials:** Log in with same Google account as project
- **API Key Name:** `GreenWatt_Intake_Open_AI_API`
- **API Key:** `sk-proj-your_openai_api_key_here`

---

## SSL Certificate Deployment Notes

### Development Environment
- **Issue:** Local development may encounter `SSL: CERTIFICATE_VERIFY_FAILED` errors with SendGrid API
- **Cause:** Corporate firewalls/proxies using self-signed certificates
- **Solution:** Set environment variable `DISABLE_SSL_VERIFICATION="true"` for local testing only

### Render.com Production Deployment
✅ **SSL Certificate Issues Automatically Resolved in Production**

Render.com provides:
- **Fully managed TLS certificates** for all deployments
- **Clean SSL environment** without corporate proxies/interceptors  
- **No SSL verification issues** in production (confirmed by multiple developers)
- **Automatic HTTPS** with proper certificate chains

**Security Note:** The `DISABLE_SSL_VERIFICATION` environment variable should be omitted or set to `"false"` on Render.com deployment for full SSL security. SSL bypass is only needed for development environments with certificate chain issues.


