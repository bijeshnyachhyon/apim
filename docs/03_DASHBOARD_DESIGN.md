# 03 Dashboard Design Specification

## 3.1 Design Principles
- **Professional Enterprise Aesthetic**: Clean, data-dense layouts optimized for IT administrators and integration developers
- **Accessibility-First**: WCAG 2.1 AA compliance, keyboard navigation, screen reader support
- **Responsive Design**: Supports 1280px+ desktop (primary) and 768px tablet (secondary)
- **Dark Mode Support**: CSS class toggle with user preference persistence

### Color Palette
| Role | Hex Code | Usage |
|---|---|---|
| Primary Navy | `#1E3A5F` | Sidebar, headers, primary buttons |
| Accent Sky Blue | `#0EA5E9` | Links, active states, focus rings |
| Success Green | `#10B981` | Connected status, success toasts |
| Warning Amber | `#F59E0B` | Rate limit warnings, degraded status |
| Danger Red | `#EF4444` | Errors, disconnected status, revoke actions |
| Gray 50 | `#F9FAFB` | Light mode background |
| Gray 900 | `#111827` | Dark mode background |
| White | `#FFFFFF` | Cards, modals in light mode |

### Typography
- **UI Font**: Inter (Google Fonts) — body text, headings, buttons
- **Monospace Font**: JetBrains Mono — API keys, code blocks, OFS messages
- **Heading Scale**: H1=24px, H2=20px, H3=16px, Body=14px, Small=12px

## 3.2 Dashboard Pages & Layout
### Sidebar Navigation
```
SIDEBAR NAVIGATION
├── 🏠 Overview (Main Dashboard)
├── 🔌 API Registry
│   ├── Endpoints
│   ├── Data Sources
│   └── OFS Message Templates
├── 🔑 API Keys & Consumers
│   ├── Keys Management
│   └── Consumer Groups
├── 📊 Analytics
│   ├── Traffic Overview
│   ├── Latency Analysis
│   └── Error Reports
├── 🗄️ Database Connections
│   ├── Connection Pool Status
│   └── Add / Edit Connections
├── 🏦 T24 / TCServer
│   ├── Connection Status
│   ├── OFS Templates
│   └── T24 Audit Log
├── 🔒 Security
│   ├── Rate Limit Rules
│   └── IP Allowlist / Blocklist
├── 📋 Audit Logs
└── ⚙️ Settings
```

### Main Layout Grid
- **Sidebar**: Fixed 260px width (collapsible to 64px icon-only)
- **Header**: 64px height with breadcrumbs, search bar, user menu, dark mode toggle
- **Content Area**: Fluid width with max-width 1600px, 24px padding
- **Cards**: Rounded-xl (12px), shadow-sm, padding-6 (24px)

## 3.3 Page-by-Page Wireframe Descriptions

### Overview Dashboard (`/dashboard/`)
**Layout**: 1-column top KPIs, 2-column middle charts, 1-column bottom tables

**Components**:
1. **KPI Cards Row** (5 cards, equal width grid)
   - Total Requests (24h): Large number, sparkline mini-chart, trend %
   - Success Rate %: Percentage with green/red indicator, vs yesterday
   - Avg Latency ms: Number with latency bar indicator
   - Active API Keys: Count with "View All" link
   - Active DB Connections: Count with status breakdown (connected/error)

2. **Line Chart**: Request volume over time
   - X-axis: Time (1h/24h/7d selector tabs)
   - Y-axis: Requests per minute
   - Series: Success (green), Client Error 4xx (amber), Server Error 5xx (red)
   - Interactive tooltip with exact values

3. **Bar Chart**: Requests by database target
   - X-axis: DB types (MSSQL, Oracle, PG, MySQL, MongoDB, T24)
   - Y-axis: Request count
   - Color-coded per DB type (see 3.5)

4. **Table**: Top 10 API consumers by request count
   - Columns: Consumer Name, API Key Prefix, Request Count, Success Rate %, Avg Latency
   - Sortable columns, click row to view consumer detail

5. **Alert Panel**: Failed connections, rate limit violations
   - Red alerts: DB connection failures, T24 timeouts
   - Amber alerts: Rate limit warnings (80% threshold), slow queries
   - Dismissible alerts with "View Details" link

---

### API Registry → Endpoints (`/dashboard/registry/endpoints`)
**Layout**: Table with filters sidebar, add button top-right

**Components**:
1. **Filters Sidebar** (collapsible)
   - Search by slug/name
   - Filter by HTTP method (GET, POST, PUT, DELETE)
   - Filter by target (DB type or T24)
   - Filter by status (active, inactive)
   - Filter by auth required (yes/no)

2. **Endpoint Table**
   - Columns: Method (badge), Path, Name, Target (with DB icon), Auth Required (toggle), Status (badge), Actions (edit/delete)
   - Method badges: GET=green, POST=blue, PUT=amber, DELETE=red
   - Paginated (25 per page), sortable

3. **Add Endpoint Modal**
   - Fields:
     - Slug (text, auto-generated from name)
     - Name (text, required)
     - Description (textarea)
     - HTTP Method (select: GET/POST/PUT/DELETE)
     - Path Pattern (text, e.g., `/customers/{id}`)
     - Target Data Source (select from registered data sources)
     - Query Template (textarea, SQL or JSON template)
     - OFS Template (select, nullable, for T24 endpoints)
     - Request Schema (JSON editor)
     - Response Schema (JSON editor)
     - Auth Required (toggle)
     - Allowed Scopes (multi-select)
     - Cache TTL Seconds (number)
     - Status (active/inactive toggle)
   - Actions: Test Endpoint, Save, Cancel
   - Test panel: input request payload, execute, view raw response

---

### API Registry → Data Sources (`/dashboard/registry/datasources`)
**Layout**: Card grid with connection status indicators

**Components**:
1. **Data Source Cards** (3-column grid)
   - Header: DB type icon + name, status badge (Connected/Error/Connecting)
   - Fields: Host:Port, Database Name, Username, Pool Size (min/max)
   - Metrics: Active Connections, Idle Connections, Avg Latency ms
   - Actions: Edit, Test Connection, View Logs, Delete
   - Status color coding: Connected=green border, Error=red border, Connecting=amber animate-pulse

2. **Add Data Source Modal** (dynamic fields per DB type)
   - Common fields: Name, DB Type (select triggers field changes)
   - MSSQL/Oracle/PG/MySQL: Host, Port, Database, Username, Password, Pool Min, Pool Max, Connection Options (JSON)
   - MongoDB: Host, Port, Database, Username, Password, Auth Source, Replica Set
   - T24: Host, Port, Username, Password, Connection Mode (HTTP/TCP), HTTP Endpoint, Timeout, Max Retries
   - Actions: Test Connection, Save, Cancel
   - Test result panel: Success with latency, or error with message

---

### API Registry → OFS Templates (`/dashboard/registry/ofs-templates`)
**Layout**: Table with OFS syntax editor modal

**Components**:
1. **OFS Template Table**
   - Columns: Name, Description, Type (Enquiry/Transaction badge), Application Name, Status, Actions (edit/test/delete)
   - Type badges: Enquiry=purple, Transaction=gold

2. **OFS Template Editor Modal**
   - Fields:
     - Name, Description
     - Type (Enquiry/Transaction select)
     - Application Name (text, e.g., CUSTOMER, FUNDS.TRANSFER)
     - OFS Message Template (textarea with monospace font, syntax highlighting for `{{variable}}` markers)
     - Variable Definitions (JSON editor: `{ "variable_name": { "type": "string", "required": true } }`)
     - T24 Version (text)
     - Status toggle
   - Preview panel: Shows raw OFS message with sample variable values
   - Test panel: Input variable values, execute OFS, view raw and parsed JSON response

---

### API Keys & Consumers → Keys Management (`/dashboard/keys`)
**Layout**: Table with key creation modal

**Components**:
1. **Key Table**
   - Columns: Key Prefix (monospace), Consumer Name, Permissions (scopes badge list), Rate Limit (hour/minute), Created Date, Last Used, Status (active/revoked badge), Actions (view/revoke)
   - Status badges: Active=green, Revoked=red, Expired=gray
   - Sortable, filterable by consumer, status

2. **Create Key Modal**
   - Fields:
     - Consumer (select from registered consumers)
     - Key Name (text)
     - Allowed Endpoints (multi-select from registered endpoints)
     - Rate Limit Override - Per Hour (number, default 1000)
     - Rate Limit Override - Per Minute (number, default 100)
     - Expiry Date (date picker, optional)
   - Actions: Generate Key, Cancel
   - **Important**: On generate, show full key ONCE in a modal with copy-to-clipboard button, warn user to save it

3. **Key Detail Panel** (slide-over from right)
   - Key info: Prefix, Consumer, Created, Expires, Status
   - Usage stats: Requests (24h), Requests (30d), Avg Latency
   - Recent Requests table: Timestamp, Endpoint, Status, Latency
   - Actions: Revoke Key (red button, confirmation dialog)

---

### API Keys & Consumers → Consumer Groups (`/dashboard/keys/consumers`)
**Layout**: Table with consumer onboarding form

**Components**:
1. **Consumer Table**
   - Columns: Name, Email, Description, API Key Count, Status, Created, Actions (edit/view keys)
   - Status badges: Active=green, Inactive=gray

2. **Onboard Consumer Modal**
   - Fields: Name, Email, Description, Initial Rate Limits (hour/minute)
   - Actions: Create Consumer, Cancel
   - Option to auto-generate first API key

---

### Analytics → Traffic Overview (`/dashboard/analytics/traffic`)
**Layout**: Time-series charts with filter controls

**Components**:
1. **Time Range Selector**: 1h, 24h, 7d, 30d, Custom Range (date picker)
2. **Request Volume Chart**: Line chart, requests per minute with success/error breakdown
3. **Response Status Chart**: Pie chart, 2xx/4xx/5xx distribution
4. **Top Endpoints Table**: Endpoint, Request Count, Avg Latency, Error Rate
5. **Traffic by Consumer Chart**: Horizontal bar chart, requests per consumer

---

### Analytics → Latency Analysis (`/dashboard/analytics/latency`)
**Layout**: Histogram and percentile charts

**Components**:
1. **Latency Percentiles Chart**: Line chart, P50/P95/P99 over time
2. **Latency Distribution Histogram**: Bar chart, latency buckets (<100ms, 100-200ms, 200-500ms, 500ms+)
3. **Slowest Endpoints Table**: Endpoint, P99 Latency, Avg Latency, Sample Size
4. **Latency by DB Type**: Grouped bar chart, per-target latency comparison

---

### Analytics → Error Reports (`/dashboard/analytics/errors`)
**Layout**: Error grouping with detailed logs

**Components**:
1. **Error Rate Chart**: Line chart, error rate % over time
2. **Error Code Breakdown**: Table, Error Code, Count, Percentage, Sample Message
3. **Recent Errors Log**: Table with Timestamp, Endpoint, Consumer, Error Code, Error Message, Request ID
4. **Error Detail Modal**: Full request context, stack trace if available, request/response payloads

---

### Database Connections (`/dashboard/databases`)
**Layout**: Connection pool metrics dashboard

**Components**:
1. **Connection Status Overview**: Cards per data source with status indicators
2. **Pool Metrics Table**: Data Source, Active Connections, Idle Connections, Max Pool Size, Utilization %
3. **Connection Health Log**: Table with Timestamp, Data Source, Status, Latency ms, Error Message
4. **Add/Edit Connection Modal**: Same as in API Registry → Data Sources

---

### T24 / TCServer (`/dashboard/t24`)
**Layout**: T24-specific monitoring and OFS testing

**Components**:
1. **Server Connection Status Card**: Host:Port, Status (connected/error), Last Ping, Latency ms, Uptime
2. **OFS Template List**: Same as API Registry → OFS Templates but filtered for T24
3. **OFS Test Console** (main feature):
   - Template Selector (dropdown)
   - Variable Input Form (dynamic fields based on template variables)
   - Raw OFS Message Preview (read-only, monospace)
   - Execute Button (blue, with loading spinner)
   - Response Panel:
     - Raw Response (textarea, scrollable)
     - Parsed JSON Response (formatted JSON viewer)
     - Status: Success/Error with `@ERROR.CODE` if applicable
4. **T24 Audit Log**: Table with Timestamp, OFS Type (Enquiry/Transaction), Template Name, Consumer, Status, Latency ms, Error Code

---

### Security (`/dashboard/security`)
**Layout**: Rate limits and IP management

**Components**:
1. **Rate Limit Rules Table**: Endpoint/Key, Limit Type (hour/minute), Limit Value, Current Usage, Status
2. **Edit Rate Limit Modal**: Target (endpoint or key), Limit Type, Value, Override Reason
3. **IP Allowlist/Blocklist**: Tables with IP Address, Description, Created, Actions (add/remove)
4. **Global Security Settings**: Toggle for require auth on all endpoints, global rate limit defaults

---

### Audit Logs (`/dashboard/audit`)
**Layout**: Filterable audit trail with export

**Components**:
1. **Filters**: Date Range, Admin User, Action Type, Resource Type, Resource ID
2. **Audit Table**: Timestamp, Admin User, Action Type, Resource Type, Resource ID, Old Value (truncated), New Value (truncated), IP Address
3. **Audit Detail Modal**: Full old/new values in JSON diff viewer
4. **Export Button**: Export filtered results as CSV or JSON

---

### Settings (`/dashboard/settings`)
**Layout**: Configuration management

**Components**:
1. **Application Settings**: App Name, Environment, Log Level, CORS Origins
2. **JWT Settings**: Algorithm (read-only RS256), Access Token Expiry, Refresh Token Expiry
3. **Encryption Settings**: Test encryption key (validate Fernet key is working)
4. **Monitoring Settings**: Prometheus Enabled toggle, Log Format (JSON/Text), Log Level
5. **Save/Reset Buttons**

## 3.4 Component Library

### StatusBadge
```
Props: status (connected, disconnected, degraded, unknown), size (sm, md, lg)
Variants:
- connected: bg-green-100 text-green-800 border-green-300
- disconnected: bg-red-100 text-red-800 border-red-300
- degraded: bg-amber-100 text-amber-800 border-amber-300
- unknown: bg-gray-100 text-gray-800 border-gray-300
```

### DatabaseIcon
SVG icons for each DB type with consistent 24x24 viewBox:
- MSSQL: Blue square with "SQL" text
- Oracle: Red square with Oracle logo stylized "O"
- PostgreSQL: Teal elephant head silhouette
- MySQL: Orange dolphin/sea creature silhouette
- MongoDB: Green leaf M stylized
- T24: Gold bank/tower icon

### MetricCard
```
Props: title (string), value (number|string), trend (optional: { value: number, direction: 'up'|'down' }), sparklineData (optional: number[]), color (navy, sky, green, amber, red)
Layout: Padding-6, rounded-xl, shadow-sm
Header: Title (text-sm text-gray-500)
Body: Value (text-3xl font-bold)
Footer: Trend indicator + "vs yesterday" text, sparkline mini-chart
```

### OFSTemplateEditor
```
Components:
- Template Name input
- Type selector (Enquiry/Transaction)
- Application Name input
- Template Textarea: monospace font, 14px, 10+ rows, border-l-4 border-gold for T24
- Variable markers `{{variable}}` highlighted in blue
- Preview panel: raw OFS with sample data substitution
- Test panel: variable inputs, execute button, response viewer
```

### RequestTable
```
Features:
- Server-side pagination (25/50/100 per page)
- Column sorting (click header)
- Global search (searches across all string columns)
- Column filters (per-column filter icon)
- Row click → detail modal/drawer
- Export selected/all to CSV
- Responsive: horizontal scroll on small screens
```

## 3.5 Color-Coded Indicators

### DB Type Color Coding
| DB Type | Color | Hex Code | Usage |
|---|---|---|---|
| MSSQL | Blue | `#3B82F6` | Icons, chart segments, status borders |
| Oracle | Red | `#EF4444` | Icons, chart segments, status borders |
| PostgreSQL | Teal | `#14B8A6` | Icons, chart segments, status borders |
| MySQL | Orange | `#F97316` | Icons, chart segments, status borders |
| MongoDB | Green | `#22C55E` | Icons, chart segments, status borders |
| T24 | Gold | `#F59E0B` | Icons, chart segments, status borders |

### Request Status Color Coding
| Status Range | Color | Hex Code | Usage |
|---|---|---|---|
| 2xx Success | Green | `#10B981` | Status badges, chart series |
| 4xx Client Error | Amber | `#F59E0B` | Status badges, chart series |
| 5xx Server Error | Red | `#EF4444` | Status badges, chart series |

### Latency Tier Color Coding
| Latency Range | Color | Hex Code | Usage |
|---|---|---|---|
| <100ms | Green | `#10B981` | Metric cards, chart thresholds |
| 100-500ms | Amber | `#F59E0B` | Metric cards, chart thresholds |
| >500ms | Red | `#EF4444` | Metric cards, chart thresholds |
