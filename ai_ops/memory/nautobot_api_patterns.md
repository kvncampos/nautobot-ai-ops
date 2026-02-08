# Nautobot API Query Patterns

## Standard Filter Parameters

- `name` - exact name match
- `q` - broad search across multiple fields
- `site` - filter by site name or ID
- `location` - filter by location name or ID
- `role` - filter by device/prefix role
- `status` - filter by status (active, planned, etc.)
- `tenant` - filter by tenant name or ID
- `tag` - filter by tag slug
- `manufacturer` - filter by manufacturer name
- `platform` - filter by platform name
- `device` - filter by parent device (for interfaces, IPs)
- `vrf` - filter by VRF name or ID

## Pagination

- `limit` - number of results per page (default varies)
- `offset` - skip N results for pagination
- Response includes `count` (total), `next`, `previous` URLs

## Common Endpoint Patterns

- List: `GET /api/{app}/{model}/` with query params
- Detail: `GET /api/{app}/{model}/{id}/`
- Create: `POST /api/{app}/{model}/`
- Update: `PATCH /api/{app}/{model}/{id}/`
- Delete: `DELETE /api/{app}/{model}/{id}/`

## Useful App Prefixes

- `/api/dcim/` - Devices, interfaces, cables, sites, racks
- `/api/ipam/` - IP addresses, prefixes, VLANs, VRFs
- `/api/circuits/` - Circuits, providers, circuit terminations
- `/api/tenancy/` - Tenants, tenant groups
- `/api/extras/` - Tags, custom fields, config contexts, jobs

## Common 404/400 Causes

- Path guessed from training data instead of using discovery tool
- Filter value is name but endpoint expects ID (or vice versa)
- Endpoint path changed between Nautobot versions
- Missing trailing slash on endpoint path
- Putting identifiers in path instead of query params

## Tips

- Always use the schema/discovery tool first to get the correct endpoint
- Put specific identifiers in `params`, not in the URL path
- Use `q` parameter for fuzzy/broad searches
- Chain queries: find device first, then query its interfaces
- Check `count` in response to know total results before paginating
