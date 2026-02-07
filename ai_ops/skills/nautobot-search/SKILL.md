# Nautobot Search Skill

## Description
This skill provides comprehensive search capabilities across Nautobot's inventory including devices, circuits, IP addresses, VLANs, and other network objects.

## When to Use
Use this skill when you need to:
- Find specific devices, circuits, or network objects
- Search for resources by name, location, or attributes
- Query inventory data from Nautobot
- Look up configuration details
- Find relationships between network objects

## Available Tools
This skill has access to all MCP tools provided by the Nautobot MCP server, including:
- Device queries
- Circuit queries
- IP address management
- VLAN lookups
- Site and location information
- Interface details
- Cable connections

## Search Strategy
1. **Clarify the query**: Understand what the user is looking for
2. **Use specific searches**: Query by name, ID, or specific attributes when possible
3. **Filter results**: Apply filters to narrow down large result sets
4. **Follow relationships**: Use object relationships to find related resources
5. **Provide context**: Include relevant metadata and relationships in responses

## Examples

### Finding a Device
```
User: "Find device RTR-NYC-01"
Action: Use device search tool with name filter
Response: Provide device details including location, status, interfaces
```

### Searching by Location
```
User: "What devices are in the NYC datacenter?"
Action: Search devices with site/location filter
Response: List all devices with key details
```

### IP Address Lookup
```
User: "What device has IP address 10.1.1.1?"
Action: Use IP address search tool
Response: Provide device assignment and interface details
```

## Best Practices
- Always validate search results before responding
- Provide relevant context (location, status, relationships)
- If multiple results, summarize and ask for clarification
- Include links to Nautobot UI when available
- Handle "no results" gracefully with search suggestions
