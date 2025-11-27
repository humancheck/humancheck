"""LangChain adapters for Humancheck.

This module provides adapters and middleware for integrating Humancheck with LangChain agents.
Users can use these adapters directly instead of LangChain's built-in HITL middleware.

Example:
    ```python
    from humancheck.adapters.langchain import HumancheckLangchainAdapter
    
    agent = create_agent(
        model,
        tools,
        middleware=[
            HumancheckLangchainAdapter(
                api_url="https://api.humancheck.dev",
                api_key="your-api-key",
                tools_requiring_approval={
                    "write_file": True,
                    "execute_sql": {"allowed_decisions": ["approve", "reject"]},
                }
            )
        ],
        checkpointer=MemorySaver(),
    )
    ```
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class HumancheckLangchainAdapter:
    """Middleware for LangChain agents that uses Humancheck for human oversight.
    
    This middleware replaces LangChain's HumanInTheLoopMiddleware, providing
    human oversight through Humancheck Platform or self-hosted instance.
    
    It intercepts tool calls and sends them to Humancheck for review,
    then resumes execution based on human decisions.
    
    Example:
        ```python
        from humancheck.adapters.langchain import HumancheckLangchainAdapter
        
        agent = create_agent(
            model,
            tools,
            middleware=[
                HumancheckLangchainAdapter(
                    api_url="https://api.humancheck.dev",
                    api_key="your-api-key",
                    tools_requiring_approval={
                        "write_file": True,
                        "execute_sql": {"allowed_decisions": ["approve", "reject"]},
                    }
                )
            ],
            checkpointer=MemorySaver(),
        )
        ```
    """
    
    def __init__(
        self,
        api_url: str = "https://api.humancheck.dev",
        api_key: Optional[str] = None,
        tools_requiring_approval: Optional[Dict[str, Any]] = None,
        description_prefix: str = "Tool execution pending approval",
    ):
        """Initialize Humancheck LangChain adapter.
        
        Args:
            api_url: Humancheck API URL (Platform or self-hosted)
            api_key: API key for authentication (required for Platform)
            tools_requiring_approval: Dict mapping tool names to approval config.
                - True: All decisions allowed (approve, edit, reject)
                - False: No approval needed
                - Dict: {"allowed_decisions": ["approve", "reject"]}
            description_prefix: Prefix for review descriptions
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.description_prefix = description_prefix
        self.tools_requiring_approval = tools_requiring_approval or {}
        
        # Build headers for API requests
        self.headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def _requires_approval(self, tool_name: str) -> tuple[bool, List[str]]:
        """Check if a tool requires approval and what decisions are allowed.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tuple of (requires_approval, allowed_decisions)
        """
        config = self.tools_requiring_approval.get(tool_name, False)
        
        if config is False:
            return False, []
        
        if config is True:
            return True, ["approve", "edit", "reject"]
        
        if isinstance(config, dict):
            allowed = config.get("allowed_decisions", ["approve", "reject", "edit"])
            return True, allowed
        
        return False, []
    
    async def _create_review(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        description: str,
        allowed_decisions: List[str],
    ) -> int:
        """Create a review in Humancheck.
        
        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments
            description: Review description
            allowed_decisions: Allowed decision types
            
        Returns:
            Review ID
        """
        # Format the proposed action
        proposed_action = f"Tool: {tool_name}\nArguments:\n{json.dumps(tool_args, indent=2)}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/reviews",
                headers=self.headers,
                json={
                    "task_type": f"tool_call_{tool_name}",
                    "proposed_action": proposed_action,
                    "agent_reasoning": description,
                    "urgency": "medium",
                    "blocking": True,
                    "metadata": {
                        "tool_name": tool_name,
                        "tool_arguments": tool_args,
                        "allowed_decisions": allowed_decisions,
                        "framework": "langchain_hitl",
                    },
                },
            )
            
            if response.status_code not in (200, 201):
                raise ValueError(f"Failed to create review: {response.status_code} - {response.text}")
            
            review = response.json()
            return review["id"]
    
    async def _get_decision(self, review_id: int, timeout: float = 300.0) -> Dict[str, Any]:
        """Get decision from Humancheck.
        
        Args:
            review_id: Review ID
            timeout: Maximum time to wait in seconds
            
        Returns:
            Decision in LangChain HITL format
        """
        poll_interval = 2.0
        elapsed = 0.0
        
        async with httpx.AsyncClient() as client:
            while elapsed < timeout:
                response = await client.get(
                    f"{self.api_url}/reviews/{review_id}",
                    headers=self.headers,
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Failed to get review: {response.status_code}")
                
                review = response.json()
                
                # Check if decision has been made
                if review.get("status") != "pending" and review.get("decision"):
                    decision_data = review["decision"]
                    decision_type = decision_data.get("decision_type")
                    metadata = review.get("metadata", {})
                    tool_name = metadata.get("tool_name", "unknown_tool")
                    
                    # Convert to LangChain HITL format
                    if decision_type == "approve":
                        return {"type": "approve"}
                    
                    elif decision_type == "reject":
                        return {
                            "type": "reject",
                            "message": decision_data.get("notes") or "Rejected by human reviewer",
                        }
                    
                    elif decision_type == "modify":
                        # Parse modified action
                        modified_action = decision_data.get("modified_action", "")
                        try:
                            if modified_action.startswith("{"):
                                modified_args = json.loads(modified_action)
                            else:
                                start = modified_action.find("{")
                                if start != -1:
                                    end = modified_action.rfind("}") + 1
                                    modified_args = json.loads(modified_action[start:end])
                                else:
                                    modified_args = metadata.get("tool_arguments", {})
                        except (json.JSONDecodeError, ValueError):
                            modified_args = metadata.get("tool_arguments", {})
                        
                        return {
                            "type": "edit",
                            "edited_action": {
                                "name": tool_name,
                                "args": modified_args,
                            },
                        }
                
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
        
        raise TimeoutError(f"Review {review_id} timed out after {timeout} seconds")
    
    async def after_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Hook called after model generates response but before tool execution.
        
        This is where we intercept tool calls and send them to Humancheck.
        
        Args:
            state: Current agent state
            
        Returns:
            Modified state (may include interrupt)
        """
        from langgraph.types import interrupt
        
        # Extract tool calls from the last message
        messages = state.get("messages", [])
        if not messages:
            return state
        
        last_message = messages[-1]
        
        # Check if message has tool calls
        tool_calls = getattr(last_message, "tool_calls", None) or []
        if not tool_calls:
            return state
        
        # Filter tool calls that require approval
        action_requests = []
        review_configs = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name") or tool_call.get("id", "unknown")
            tool_args = tool_call.get("args", {})
            
            requires, allowed = self._requires_approval(tool_name)
            if not requires:
                continue  # Skip tools that don't need approval
            
            # Build description
            description = f"{self.description_prefix}\n\nTool: {tool_name}\nArgs: {json.dumps(tool_args, indent=2)}"
            
            action_requests.append({
                "name": tool_name,
                "arguments": tool_args,
                "description": description,
            })
            
            review_configs.append({
                "action_name": tool_name,
                "allowed_decisions": allowed,
            })
        
        # If no tools need approval, continue normally
        if not action_requests:
            return state
        
        # Create HITL request format (compatible with LangChain's format)
        hitl_request = {
            "action_requests": action_requests,
            "review_configs": review_configs,
        }
        
        # Raise interrupt with HITL request
        return interrupt(hitl_request)
    
    async def handle_interrupt(
        self,
        interrupt_data: List[Any],
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Handle interrupt by creating reviews and waiting for decisions.
        
        This method is called when an interrupt is raised. It creates reviews
        in Humancheck and waits for human decisions.
        
        Args:
            interrupt_data: List of interrupts from LangGraph
            config: LangGraph configuration
            
        Returns:
            List of decisions in LangChain HITL format
        """
        if not interrupt_data:
            return []
        
        # Extract HITL request from interrupt
        interrupt = interrupt_data[0]
        hitl_request = interrupt.value if hasattr(interrupt, "value") else interrupt
        
        action_requests = hitl_request.get("action_requests", [])
        if not action_requests:
            return []
        
        # Create reviews in Humancheck
        review_ids = []
        for action in action_requests:
            tool_name = action.get("name", "unknown_tool")
            tool_args = action.get("arguments", {})
            description = action.get("description", "")
            
            # Get allowed decisions
            review_configs = hitl_request.get("review_configs", [])
            config_map = {
                cfg["action_name"]: cfg.get("allowed_decisions", ["approve", "reject", "edit"])
                for cfg in review_configs
            }
            allowed = config_map.get(tool_name, ["approve", "reject", "edit"])
            
            try:
                review_id = await self._create_review(tool_name, tool_args, description, allowed)
                review_ids.append(review_id)
                print(f"  ✓ Review #{review_id} created: {tool_name}")
            except Exception as e:
                print(f"  ✗ Failed to create review for {tool_name}: {e}")
                # Default to approve on error
                review_ids.append(None)
        
        # Wait for decisions
        decisions = []
        for review_id in review_ids:
            if review_id is None:
                decisions.append({"type": "approve"})  # Default on error
                continue
            
            try:
                decision = await self._get_decision(review_id, timeout=300)
                decisions.append(decision)
                print(f"  ✓ Decision received for Review #{review_id}: {decision['type']}")
            except TimeoutError:
                print(f"  ⏱️  Timeout for Review #{review_id}, defaulting to reject")
                decisions.append({
                    "type": "reject",
                    "message": "Timeout waiting for human decision",
                })
            except Exception as e:
                print(f"  ✗ Error getting decision: {e}")
                decisions.append({"type": "approve"})  # Default on error
        
        return decisions

