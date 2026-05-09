from mcp.server.fastmcp import FastMCP
from services import query_neon_db, post_to_neon_db, verify_ulpin

# Initialize the FastMCP Server
mcp = FastMCP("HarBr MCP")

@mcp.tool()
def search_properties(budget_max: int, neighborhood: str, bhk: int, pet_friendly: bool = False, dietary_pref: str = "Any", must_have_amenity: str = "Any") -> list:
    """Search for HarBr properties using strict parameters. Converts vague searches into concrete database queries."""
    return query_neon_db(budget_max, neighborhood, bhk, pet_friendly, dietary_pref, must_have_amenity)

@mcp.tool()
def list_property(ulpin: str, owner_name: str, rent: int, bhk: int, city: str, floor_info: str) -> str:
    """Ingest a new property listing into the HarBr database. Call this ONLY when all information is gathered."""
    return post_to_neon_db(ulpin, owner_name, rent, bhk, city, floor_info)

@mcp.tool()
def check_ulpin(ulpin: str) -> dict:
    """Perform a real-time legal and fairness audit on a property ULPIN. Checks against the HarBr land records."""
    return verify_ulpin(ulpin)

if __name__ == "__main__":
    mcp.run(transport='stdio')
 
