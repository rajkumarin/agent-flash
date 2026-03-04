"""Gemini integration for MCP Tools.

Provides function calling schema and execution for Google Gemini.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

from .base import ToolResult
from .registry import TOOL_REGISTRY
from utils.logger import log

if TYPE_CHECKING:
    from .client import FreeCADMCPTools


def get_gemini_tools_schema() -> List:
    """
    Generate Gemini-compatible function declarations for MCP tools.

    Returns:
        List of tool declarations that can be passed to Gemini's
        GenerativeModel for function calling.
    """
    import google.generativeai as genai

    tool_declarations = []

    for tool_name, tool_info in TOOL_REGISTRY.items():
        # Build parameters schema
        properties = {}
        required = []

        for param_name, param_info in tool_info.get('parameters', {}).items():
            param_type = param_info['type']

            # Map our types to Gemini/OpenAPI types
            if param_type == 'string':
                properties[param_name] = {
                    "type": "STRING",
                    "description": param_info.get('description', '')
                }
            elif param_type == 'number':
                properties[param_name] = {
                    "type": "NUMBER",
                    "description": param_info.get('description', '')
                }
            elif param_type == 'array':
                properties[param_name] = {
                    "type": "ARRAY",
                    "description": param_info.get('description', ''),
                    "items": {"type": "NUMBER"}
                }

            if param_info.get('required', False):
                required.append(param_name)

        # Create function declaration
        func_decl = genai.protos.FunctionDeclaration(
            name=tool_name,
            description=tool_info['description'],
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={k: genai.protos.Schema(**v) for k, v in properties.items()},
                required=required
            ) if properties else None
        )

        tool_declarations.append(func_decl)

    return tool_declarations


def create_gemini_tools():
    """
    Create a Gemini Tool object containing all MCP tool declarations.

    Returns:
        Gemini Tool object with function declarations
    """
    import google.generativeai as genai

    declarations = get_gemini_tools_schema()
    return genai.protos.Tool(function_declarations=declarations)


class MCPToolExecutor:
    """
    Executor that handles tool calls from Gemini and routes them to MCP tools.

    This class bridges Gemini's function calling with the FreeCADMCPTools.
    """

    def __init__(self, mcp_tools: "FreeCADMCPTools"):
        """
        Initialize the executor.

        Args:
            mcp_tools: FreeCADMCPTools instance
        """
        self.mcp_tools = mcp_tools
        self.tool_call_history: List[Dict[str, Any]] = []

    def execute_tool_call(self, function_call) -> Dict[str, Any]:
        """
        Execute a single tool call from Gemini.

        Args:
            function_call: Gemini FunctionCall object with name and args

        Returns:
            dict with tool result
        """
        tool_name = function_call.name
        args = dict(function_call.args) if function_call.args else {}

        log(f"Executing MCP tool: {tool_name} with args: {args}", "DEBUG")

        # Log the call
        self.tool_call_history.append({
            "tool": tool_name,
            "args": args
        })

        # Route to appropriate MCP tool method
        try:
            result = self._dispatch_tool(tool_name, args)
            log(f"Tool {tool_name} completed: success={result.success}", "DEBUG")
            return result.to_dict()
        except Exception as e:
            log(f"Tool {tool_name} failed: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def _dispatch_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Dispatch tool call to appropriate method."""
        if tool_name == "get_visible_parts":
            return self.mcp_tools.get_visible_parts(
                args.get('doc_name', ''),
                args.get('view_name', 'Left'),
                args.get('side_threshold', 5.0)
            )
        elif tool_name == "get_view_screenshot":
            return self.mcp_tools.get_view_screenshot(
                args.get('doc_name'),
                args.get('view_name', 'Isometric')
            )
        elif tool_name == "list_documents":
            return self.mcp_tools.list_documents()
        elif tool_name == "get_all_parts":
            return self.mcp_tools.get_all_parts(args.get('doc_name', ''))
        elif tool_name == "get_part_details":
            return self.mcp_tools.get_part_details(
                args.get('doc_name', ''),
                args.get('part_name', '')
            )
        elif tool_name == "highlight_part":
            return self.mcp_tools.highlight_part(
                args.get('doc_name', ''),
                args.get('part_name', ''),
                args.get('color')
            )
        elif tool_name == "compare_views":
            return self.mcp_tools.compare_views(
                args.get('doc_name', ''),
                args.get('view1', 'Left'),
                args.get('view2', 'Right')
            )
        else:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the history of tool calls made."""
        return self.tool_call_history

    def clear_history(self) -> None:
        """Clear the tool call history."""
        self.tool_call_history = []


def run_agentic_loop(
    model,
    mcp_tools: "FreeCADMCPTools",
    user_prompt: str,
    system_prompt: str = "",
    image=None,
    max_iterations: int = 5,
    doc_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run an agentic loop where Gemini can call MCP tools as needed.

    This function implements the ReAct pattern:
    1. Send prompt to Gemini with tool definitions
    2. If Gemini returns a function call, execute it and send result back
    3. Repeat until Gemini returns a text response or max iterations reached

    Args:
        model: Gemini GenerativeModel instance
        mcp_tools: FreeCADMCPTools instance
        user_prompt: The user's question/request
        system_prompt: Optional system context
        image: Optional PIL Image for vision tasks
        max_iterations: Maximum number of tool call rounds
        doc_name: Default document name to inject into prompts

    Returns:
        dict with:
            - response: Final text response
            - tool_calls: List of tool calls made
            - tool_results: List of tool results
            - images: List of any images generated (base64)
            - iterations: Number of iterations performed
    """
    import google.generativeai as genai

    executor = MCPToolExecutor(mcp_tools)
    tool_results = []
    generated_images = []

    # Create tools configuration
    tools = create_gemini_tools()

    # Build initial prompt with context
    full_prompt = f"""{system_prompt}

IMPORTANT: You have access to MCP tools to interact with FreeCAD. Use them when needed to:
- Get information about loaded documents and parts
- Take screenshots from different view angles
- Get visible parts from specific views
- Highlight parts for reference
- Compare what's visible between different views

Current document name (if loaded): {doc_name or 'Not specified - use list_documents to find open documents'}

User request: {user_prompt}"""

    # Build content list
    content = [full_prompt]
    if image is not None:
        content.append(image)

    # Start chat with tools
    chat = model.start_chat(enable_automatic_function_calling=False)

    # Configure generation
    generation_config = genai.GenerationConfig(
        temperature=0.7,
        top_p=0.95,
    )

    iteration = 0
    final_response = None

    log(f"Starting agentic loop: max_iterations={max_iterations}, doc={doc_name}", "INFO")

    while iteration < max_iterations:
        iteration += 1
        log(f"Agentic loop iteration {iteration}/{max_iterations}", "DEBUG")

        try:
            # Send message with tools
            response = chat.send_message(
                content,
                tools=[tools],
                generation_config=generation_config
            )

            # Check if response contains function calls
            if response.candidates[0].content.parts:
                has_function_call = False
                text_parts = []

                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call.name:
                        has_function_call = True
                        function_call = part.function_call

                        # Execute the tool
                        result = executor.execute_tool_call(function_call)
                        tool_results.append({
                            "tool": function_call.name,
                            "args": dict(function_call.args) if function_call.args else {},
                            "result": result
                        })

                        # Capture any images from results
                        if result.get("success") and result.get("data"):
                            if result["data"].get("image"):
                                generated_images.append({
                                    "image": result["data"]["image"],
                                    "caption": f"Tool: {function_call.name}",
                                    "view": result["data"].get("view", "Unknown")
                                })

                        # Send function response back to model
                        function_response = genai.protos.FunctionResponse(
                            name=function_call.name,
                            response={"result": result}
                        )

                        # Continue conversation with tool result
                        content = [genai.protos.Part(function_response=function_response)]

                    elif hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)

                # If no function calls, we have final response
                if not has_function_call and text_parts:
                    final_response = "\n".join(text_parts)
                    break

            else:
                # No parts, unexpected response
                final_response = "No response generated."
                break

        except Exception as e:
            log(f"Agentic loop error: {e}", "ERROR")
            final_response = f"Error during agentic loop: {str(e)}"
            break

    log(f"Agentic loop completed: iterations={iteration}, tool_calls={len(tool_results)}", "INFO")

    # If we exhausted iterations without final response
    if final_response is None:
        final_response = "Maximum iterations reached. Here's what I found based on the tool calls."

    return {
        "response": final_response,
        "tool_calls": executor.get_history(),
        "tool_results": tool_results,
        "images": generated_images,
        "iterations": iteration
    }
