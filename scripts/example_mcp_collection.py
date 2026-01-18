"""
Example script showing how to use MCP tools to collect Prague businesses.

This script demonstrates how to use MCP tools (brave-search, puppeteer) 
through Cursor AI to collect business data.

NOTE: This script is meant to be executed through Cursor AI with MCP access,
not directly as a standalone Python script.
"""

# This is a reference implementation showing the pattern for using MCP tools
# The actual collection should be done through Cursor AI with MCP access

"""
Example workflow through Cursor AI:

1. Use brave-search MCP to search for businesses:
   Query: "hair salons Prague"
   Query: "kadeřnictví Praha"
   Query: "beauty salons Prague"
   etc.

2. For each search result:
   - Extract business name and basic info
   - Use puppeteer MCP to navigate to Google Maps page
   - Extract: address, phone, website
   - Search for social media links
   - Search for owner information

3. Create BusinessCreate objects and add to collector

4. Save progress periodically

5. Export to CSV when done

Example MCP tool calls (through Cursor AI):

# Search for businesses
brave_web_search(query="hair salons Prague", count=20)

# Navigate to business page
puppeteer_navigate(url="https://maps.google.com/...")

# Extract information
puppeteer_evaluate(function="() => { return document.querySelector('.business-info').textContent; }")

# Save to JSON
write_file(path="data/prague_businesses_progress.json", content=json.dumps(businesses))
"""

# Actual implementation would look like this (requires MCP client):

"""
import asyncio
from mcp import ClientSession
from scripts.collect_prague_businesses import BusinessCollector, BusinessCategory
from models.business import BusinessCreate

async def collect_with_mcp():
    collector = BusinessCollector()
    
    # Example: Search using brave-search MCP
    # This would be called through Cursor AI MCP tools
    search_results = await mcp_call("brave_web_search", {
        "query": "hair salons Prague",
        "count": 20
    })
    
    for result in search_results:
        # Extract business info
        name = result.get("title", "")
        url = result.get("url", "")
        
        # Use puppeteer to get details
        details = await mcp_call("puppeteer_navigate", {"url": url})
        
        # Create business
        business = BusinessCreate(
            name=name,
            category=BusinessCategory.HAIR_SALON,
            address=details.get("address", ""),
            phone=details.get("phone"),
            website=details.get("website"),
        )
        
        collector.add_business(business)
    
    collector.save_progress()

if __name__ == "__main__":
    asyncio.run(collect_with_mcp())
"""
