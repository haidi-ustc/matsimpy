# API Client Module Design

## Overview

A module for querying molecular and crystal databases via REST API, similar to Materials Project API (mp-api). Provides a clean interface for searching, retrieving, and converting database records to MatSimPy objects.

## Module Structure

```
matsimpy/api/
├── __init__.py           # Main exports (APIClient, QueryBuilder)
├── client.py             # HTTP client for API requests
├── query.py              # Query builder with MongoDB-style operators
├── parser.py             # Response parser (JSON -> MatSimPy objects)
├── exceptions.py         # Custom exceptions
└── endpoints.py          # API endpoint definitions
```

## Core Components

### 1. APIClient (`client.py`)

Main client class for making API requests.

**Features:**
- HTTP request handling (POST, GET)
- Authentication via API key
- Request retry logic with exponential backoff
- Response caching (optional)
- Pagination support
- Error handling

**Example:**
```python
from matsimpy.api import APIClient

# Initialize client
client = APIClient(
    host="https://api.example.com",
    api_key="your-api-key",
    timeout=30
)

# Search molecules
results = client.search_molecules(
    query={"charge": {"$eq": 1}, "weight": {"$gt": 200, "$lt": 250}},
    page=1,
    size=10
)
```

### 2. QueryBuilder (`query.py`)

MongoDB-style query builder for constructing complex queries.

**Supported Operators:**
- `$eq`: equals
- `$ne`: not equals
- `$gt`: greater than
- `$gte`: greater than or equal
- `$lt`: less than
- `$lte`: less than or equal
- `$in`: in list
- `$nin`: not in list
- `$regex`: regular expression match
- `$and`: logical AND
- `$or`: logical OR
- `$not`: logical NOT

**Example:**
```python
from matsimpy.api import QueryBuilder

# Build query
query = QueryBuilder()
query.add("charge", "$eq", 1)
query.add("weight", "$gt", 200)
query.add("weight", "$lt", 250)
query.add("formula", "$regex", "^C.*H.*O$")  # Contains C, H, O

# Or use fluent interface
query = (QueryBuilder()
    .eq("charge", 1)
    .gt("weight", 200)
    .lt("weight", 250)
    .regex("formula", "^C.*H.*O$"))

# Convert to dict
query_dict = query.to_dict()
```

### 3. ResponseParser (`parser.py`)

Converts API response JSON to MatSimPy objects.

**Features:**
- Parse molecule data to `Molecule` objects
- Parse crystal data to `Crystal` objects
- Extract metadata (formula, properties, identifiers)
- Handle missing/optional fields gracefully

**Example:**
```python
from matsimpy.api import ResponseParser

parser = ResponseParser()

# Parse API response
molecules = parser.parse_molecules(api_response["result"])

# Each molecule is a MatSimPy Molecule object
for mol in molecules:
    print(mol.formula)
    print(mol.get_center_of_mass())
```

### 4. Integration with Config System

Store API credentials and endpoints in config:

```yaml
# ~/.matsimpy/config.yaml
api:
  molecule:
    host: "https://api.example.com"
    api_key: "${MATSIMPY_API_KEY}"  # From environment variable
    timeout: 30
    retry:
      max_attempts: 3
      backoff_factor: 2.0
  crystal:
    host: "https://crystal-api.example.com"
    api_key: "${MATSIMPY_CRYSTAL_API_KEY}"
```

## API Response Format

Based on provided example:

```json
{
  "result": [
    {
      "picId": "picd-mol-129717517",
      "inchi": "1S/C9H14O6P/...",
      "inchikey": "VCURMVJWQVIOKI-ADUGMZOQSA-N",
      "categoryObject": "molucule",
      "smiles": "C1=C[P+](=C1)...",
      "formula": "C9H14O6P+",
      "extern": {
        "cid": 129717517,
        "cas": null,
        "iupac": "(3R,4S,5S,6R)-6-(hydroxymethyl)...",
        "weight": "249.1800000000",
        "charge": "1.0000000000",
        "exact_mass": 249.05280016,
        "monoisotopic_mass": 249.05280016,
        "tpsa": "110.0000000000",
        "complexity": 331.0,
        "h_bond_donor_count": 5,
        "h_bond_acceptor_count": 6,
        "rotatable_bond_count": 2,
        "heavy_atom_count": 16,
        ...
      }
    }
  ],
  "page": {
    "size": 2,
    "current": 1,
    "total": 2000000
  }
}
```

## Usage Examples

### Basic Search

```python
from matsimpy.api import APIClient, QueryBuilder

# Initialize client
client = APIClient.from_config("api.molecule")  # Loads from config

# Build query
query = (QueryBuilder()
    .eq("charge", 1)
    .gt("weight", 200)
    .lt("weight", 250))

# Search
response = client.search_molecules(
    query=query.to_dict(),
    page=1,
    size=10
)

# Parse results
molecules = client.parse_molecules(response["result"])

# Use MatSimPy objects
for mol in molecules:
    print(f"Formula: {mol.formula}")
    print(f"Mass: {mol.composition.mass}")
```

### Advanced Query

```python
from matsimpy.api import QueryBuilder

# Complex query with AND/OR
query = QueryBuilder()
query.and_([
    {"charge": {"$eq": 1}},
    {"$or": [
        {"weight": {"$gt": 200, "$lt": 250}},
        {"formula": {"$regex": "^C.*H.*O$"}}
    ]}
])

# Search
results = client.search_molecules(query=query.to_dict())
```

### Get by ID

```python
# Get specific molecule by picId
molecule = client.get_molecule("picd-mol-129717517")
print(molecule.formula)
print(molecule.site_properties)  # Contains metadata
```

### Pagination

```python
# Iterate through all results
for page in client.search_molecules_iter(
    query={"charge": {"$eq": 1}},
    page_size=100
):
    molecules = client.parse_molecules(page["result"])
    for mol in molecules:
        process_molecule(mol)
```

## Implementation Details

### 1. Request Format

```python
POST /api/v1/molecule/open/search
Headers:
  Content-Type: application/json
  OpenAuthorization: ${API_KEY}
Body:
{
  "current": 1,
  "size": 10,
  "params": {
    "charge": {"$eq": 1},
    "weight": {"$gt": 200, "$lt": 250}
  }
}
```

### 2. Error Handling

```python
from matsimpy.api.exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError
)

try:
    results = client.search_molecules(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded, retrying...")
except APIError as e:
    print(f"API error: {e}")
```

### 3. Caching

```python
# Enable caching
client = APIClient(
    host="...",
    api_key="...",
    cache=True,
    cache_dir="~/.matsimpy/cache/api"
)

# Cache is keyed by query hash
# Automatically invalidated after TTL
```

### 4. Retry Logic

```python
# Automatic retry on transient errors
client = APIClient(
    host="...",
    api_key="...",
    retry={
        "max_attempts": 3,
        "backoff_factor": 2.0,
        "retry_on": [500, 502, 503, 504]  # HTTP status codes
    }
)
```

## Integration with MatSimPy

### Molecule Creation from API Data

```python
# API response -> Molecule
def parse_molecule_from_api(api_data):
    """
    Convert API response to MatSimPy Molecule.
    
    If 3D coordinates are available (volume3d), use them.
    Otherwise, generate from SMILES/InChI using RDKit (optional).
    """
    # Extract identifiers
    pic_id = api_data["picId"]
    formula = api_data["formula"]
    smiles = api_data.get("smiles")
    inchi = api_data.get("inchi")
    
    # Extract metadata
    extern = api_data.get("extern", {})
    weight = float(extern.get("weight", 0))
    charge = int(float(extern.get("charge", 0)))
    
    # Try to get 3D coordinates
    if api_data.get("extern", {}).get("volume3d"):
        # Use provided 3D structure
        positions = extract_positions_from_3d(api_data["extern"]["volume3d"])
        species = extract_species_from_3d(api_data["extern"]["volume3d"])
    elif smiles:
        # Generate from SMILES (requires RDKit)
        mol = generate_from_smiles(smiles)
        positions = mol.positions
        species = mol.species
    else:
        # Fallback: create minimal molecule from formula
        species, positions = create_from_formula(formula)
    
    # Create Molecule
    molecule = Molecule(species, positions)
    
    # Store metadata in site_properties
    molecule.site_properties = [{
        "pic_id": pic_id,
        "inchi": inchi,
        "inchikey": api_data.get("inchikey"),
        "smiles": smiles,
        "weight": weight,
        "charge": charge,
        "iupac": extern.get("iupac"),
        "cid": extern.get("cid"),
        "exact_mass": extern.get("exact_mass"),
        "tpsa": extern.get("tpsa"),
        "complexity": extern.get("complexity"),
        ...
    }] * len(molecule)
    
    return molecule
```

## Configuration

### Default Config

```python
# matsimpy/config/defaults.py
def get_default_config():
    return {
        # ... existing config ...
        "api": {
            "molecule": {
                "host": None,  # Must be set by user
                "api_key": None,  # Must be set by user
                "timeout": 30,
                "retry": {
                    "max_attempts": 3,
                    "backoff_factor": 2.0,
                    "retry_on": [500, 502, 503, 504]
                },
                "cache": {
                    "enabled": False,
                    "ttl": 3600,  # 1 hour
                    "dir": "~/.matsimpy/cache/api"
                }
            },
            "crystal": {
                # Similar structure for crystal API
            }
        }
    }
```

### Environment Variables

```bash
export MATSIMPY_API__MOLECULE__HOST="https://api.example.com"
export MATSIMPY_API__MOLECULE__API_KEY="your-key-here"
```

## Testing

### Mock API Server

```python
# tests/fixtures/api_server.py
@pytest.fixture
def mock_api_server():
    """Mock API server for testing."""
    from unittest.mock import Mock
    
    server = Mock()
    server.search_molecules.return_value = {
        "result": [...],
        "page": {"size": 10, "current": 1, "total": 100}
    }
    return server
```

### Test Examples

```python
def test_query_builder():
    query = QueryBuilder().eq("charge", 1).gt("weight", 200)
    assert query.to_dict() == {
        "charge": {"$eq": 1},
        "weight": {"$gt": 200}
    }

def test_api_client_search(mock_api_server):
    client = APIClient(host="...", api_key="...")
    client._session = mock_api_server
    
    results = client.search_molecules(query={"charge": {"$eq": 1}})
    assert len(results["result"]) > 0

def test_parser():
    api_data = {
        "picId": "picd-mol-123",
        "formula": "H2O",
        "smiles": "O",
        "extern": {"weight": "18.015", "charge": "0"}
    }
    
    molecule = ResponseParser.parse_molecule(api_data)
    assert molecule.formula == "H2O"
    assert len(molecule) == 3
```

## Future Enhancements

1. **Async Support**: Async/await for concurrent requests
2. **Batch Operations**: Batch search/retrieve
3. **Streaming**: Stream large result sets
4. **WebSocket**: Real-time updates
5. **GraphQL**: Alternative query interface
6. **Local Cache**: SQLite database for offline access
7. **Structure Generation**: Generate 3D structures from SMILES/InChI

## Dependencies

- `requests`: HTTP client
- `urllib3`: URL handling
- `tenacity`: Retry logic (optional)
- `rdkit`: SMILES/InChI parsing (optional, for structure generation)

## File Structure Summary

```
matsimpy/api/
├── __init__.py           # Exports: APIClient, QueryBuilder, ResponseParser
├── client.py             # APIClient class (200-300 lines)
├── query.py              # QueryBuilder class (150-200 lines)
├── parser.py             # ResponseParser class (200-300 lines)
├── exceptions.py         # Custom exceptions (50-100 lines)
└── endpoints.py          # Endpoint constants (50 lines)

Total: ~700-1000 lines
```

## Implementation Priority

1. **Phase 1**: Core client, query builder, basic parser
2. **Phase 2**: Config integration, error handling, retry logic
3. **Phase 3**: Caching, pagination helpers, advanced queries
4. **Phase 4**: Structure generation from SMILES/InChI, async support

