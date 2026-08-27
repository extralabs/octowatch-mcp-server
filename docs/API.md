# API notes (from live demo probe)

Captured against Cloud demo while scaffolding this repo. Prefer the interactive UI at https://app.octowatchdlp.com/api/ for full catalog.

## Hosts

| URL | Role |
|-----|------|
| `https://app.octowatchdlp.com` | Web Console SPA |
| `https://app.octowatchdlp.com/api/` | In-app API docs (SPA route) |
| `https://cloud.octowatchdlp.com` | REST API (`spm-config.json` → `serverBase`) |
| `https://cloud.octowatchdlp.com/Help` | ASP.NET Web API Help (~340 endpoints) |

## Auth

```http
GET /api/Access/login-jwt?email=demo%40octowatchdlp.com&password=demo
```

Response includes `Token`, `RefreshToken`, `ExpiresIn`, `PublicID`.

```http
GET /api/Access/refresh-token?refresh_Token=…&PublicID=…
Authorization: Bearer <Token>   # on data calls
```

## Users / groups filter body

Used by Risks, Alerts, Activity, TimeSheet, Productivity, Analytics, Dashboard POSTs:

```json
[{ "NodeType": -666666, "UserID": -666666 }]
```

| NodeType | Meaning |
|----------|---------|
| `-666666` | Root (all) |
| `1` | Group (`UserID` = group id) |
| `2` | User — **not reliable** in probe (SQL errors); prefer group/root + client filter |

## Headers for period POSTs

```
Authorization: Bearer <Token>
Accept: application/json
Content-Type: application/json
DateFrom: 2026-08-20 00:00:00
DateTo: 2026-08-27 23:59:59
Offset: 0
NumRows: 100
HideHidden: False
```

## Endpoints used by MCP v0.1

| Tool area | Method | Path |
|-----------|--------|------|
| Risks | POST | `/api/Risks/Overall2` |
| Anomalies | POST | `/api/Alerts/Overall2` |
| Users/groups | GET | `/api/Edit/GetUsersGroups2` |
| Activity | POST | `/api/Activity/Overall2` |
| Timesheet | POST | `/api/TimeSheet/Overall2` |
| Productivity | POST | `/api/Productivity/Overall3` |
| Productivity totals | POST | `/api/Productivity/GetStats` |
| Analytics rollup | POST | `/api/Analytics/Overall` |
| Report settings | GET | `/api/Account/GetReports` |
| Background jobs | GET | `/api/Edit/GetProcessingTasks` |

## Demo tree (sample)

Groups: Managers, Accounting, Management, Production, Warehouse.  
Users include Accountant Emily Carter (`AliasID` 4), Madison Harris (1), Cooper Sullivan (2), Tyler Benson (3), Jackson T.R. (5), Hudson Blake (6).
