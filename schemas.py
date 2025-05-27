from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# JSON-RPC 2.0 base request/response models
class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field("2.0", const=True)
    method: str
    params: Optional[Any] = None
    id: Optional[Any] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = Field("2.0", const=True)
    result: Optional[Any] = None
    error: Optional[Any] = None
    id: Optional[Any] = None

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

# MCP method params/results
class InitializeParams(BaseModel):
    client_capabilities: Optional[Dict[str, Any]] = None

class InitializeResult(BaseModel):
    protocolVersion: str
    serverVendor: str
    serverVersion: str
    displayName: str
    description: str
    capabilities: Dict[str, bool]

class ToolListResult(BaseModel):
    __root__: List[Dict[str, Any]]

class ToolCallParams(BaseModel):
    toolId: str
    inputs: Dict[str, Any]

class ToolCallResult(BaseModel):
    sql_query: Optional[str] = None
    query_result: Optional[Any] = None
    error: Optional[str] = None
