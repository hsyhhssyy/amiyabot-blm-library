import os
from typing import Any, Callable, Dict, List, Optional, Union

curr_dir = os.path.dirname(__file__)

dir_path = f"{curr_dir}/../../../../resource/blm_library/cache"
dir_path = os.path.abspath(dir_path)
if not os.path.exists(dir_path):
    os.makedirs(dir_path)

class BLMFunctionCall:
    functon_name:str
    function_schema:Union[str,dict]
    function:Callable[..., Any]

class BLMAdapter:  
    def __init__(self):  
        self.cache_dir = dir_path  
  
    async def completion_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> Optional[str]:  
        ...  
  
    async def chat_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,  
        channel_id: Optional[str] = None,
        functions: Optional[List[BLMFunctionCall]] = None,  
    ) -> Optional[str]:  
        ...  
  
    async def assistant_flow(  
        self,  
        assistant: str,  
        prompt: Union[str, List[str]],  
        context_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> Optional[str]:  
        ...  
  
    async def assistant_create(  
        self,  
        name: str,  
        instructions: str,  
        model: str ,
        functions: Optional[List[BLMFunctionCall]] = None,  
        code_interpreter: bool = False,  
        retrieval: Optional[List[str]] = None,  
    ) -> str:  
        ...  
  
    async def model_list(self) -> List[dict]:  
        ...  
  
    def extract_json(self, string: str) -> List[Union[Dict[str, Any], List[Any]]]:
        ...